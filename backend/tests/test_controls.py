"""
Tests voor Stap 2 slice 2.1: het generieke controle-fundament. Kern: de checks
hergebruiken de bestaande formaatvalidators (pariteit) en draaien op het
canonieke model. Puur functioneel; geen DB of HTTP.
"""
from app.services.algemeen_validator import VALIDATORS
from app.services.controls import (Finding, is_present, check_value,
                                    run_column, column_values)
from app.services.ingest.pipeline import to_canonical


def test_check_value_parity_with_format_validators():
    samples = {
        "date": ["2026-04-19", "2026-02-30", "geen datum"],
        "bsn":  ["123456782", "111111111", "abc"],
        "email": ["a@b.nl", "geenmail"],
        "postcode": ["8448 SJ", "12"],
        "number": ["36,0", "x"],
    }
    for check, vals in samples.items():
        for v in vals:
            assert check_value(check, v) == bool(VALIDATORS[check](v)), f"{check}:{v}"


def test_required_and_empty_semantics():
    assert check_value("required", "") is False
    assert check_value("required", "x") is True
    # lege waarde is 'niet van toepassing' voor een formaatcheck
    assert check_value("date", "") is True
    assert is_present("  ") is False and is_present("a") is True


def test_run_column_reports_failures():
    vals = ["2026-01-01", "2026-02-30", "", "notadate"]
    f = run_column(vals, "geboortedatum", "date", severity="error")
    assert isinstance(f, Finding)
    assert f.count == 2 and f.severity == "error"          # 2 ongeldig, lege overgeslagen
    assert f.examples and f.examples[0]["value"] in ("2026-02-30", "notadate")


def test_run_column_all_pass_returns_none():
    assert run_column(["2026-01-01", "1990-04-22"], "d", "date") is None


def test_column_values_reads_normalized_from_canonical():
    cf = to_canonical("Profit_Illness.xml", ["EmployeeId", "StartDate"],
                      [{"EmployeeId": "1", "StartDate": "20260101"},
                       {"EmployeeId": "2", "StartDate": "20260230"}],
                      total=2, standard="algemeen")
    vals = column_values(cf, "StartDate")
    # eerste is genormaliseerd naar ISO, tweede (ongeldige kalenderdatum) blijft raw
    assert vals[0] == "2026-01-01"
    f = run_column(vals, "startdatum", "date")
    assert f is not None and f.count == 1
