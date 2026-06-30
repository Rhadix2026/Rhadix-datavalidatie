"""Stap 0: gedeelde datum-primitieven — borgt de Noorderboog-bevindingen (TB-007)."""
from app.services.dataquality import is_date, parse_date
from app.services import validator, algemeen_validator


def test_is_date_accepts_afas_formats():
    # AFAS levert jaar-eerst/ISO, kort yyyymmdd en NL dag-eerst
    for v in ["1980-05-12", "1980/05/12", "19800512", "12-05-1980", "12/05/1980", "1980-05-12T00:00:00Z"]:
        assert is_date(v), f"zou geldig moeten zijn: {v}"


def test_is_date_rejects_invalid_calendar():
    for v in ["2026-02-30", "1980-13-01", "", "abc", None]:
        assert not is_date(v), f"zou ongeldig moeten zijn: {v!r}"


def test_kikv_is_date_uses_shared_module():
    # TB-007b: KIK-V keurde alle AFAS (jaar-eerst) datums af -> nu niet meer
    assert validator.is_date("1980-05-12")
    assert validator.is_date("19800512")
    assert not validator.is_date("2026-02-30")


def test_algemeen_valid_date_calendar_and_iso():
    # TB-007a: Algemeen miste niet-bestaande datum (alleen formaat-regex)
    assert algemeen_validator._valid_date("1980-05-12")
    assert not algemeen_validator._valid_date("2026-02-30")        # niet-bestaande datum
    assert algemeen_validator._valid_date("1980-05-12T00:00:00Z")  # AFAS met tijdstempel


def test_parse_date_preserves_intervals():
    # parse_date blijft bruikbaar voor duur/overlap-checks
    assert parse_date("2026-01-10") < parse_date("2026-02-01")
    assert parse_date("10-01-2026") == parse_date("2026-01-10")
