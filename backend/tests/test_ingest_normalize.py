"""
Tests voor Slice 4 (Stap 1): waarde-normalisatie aan de bron. Kern: datum- en
codelijstkolommen krijgen een genormaliseerde `value`, terwijl `raw` en
`to_legacy_rows()` ONGEWIJZIGD blijven (validators draaien identiek door).
Puur functioneel; geen DB of HTTP.
"""
from app.services.rules import normalize_verzuimtype
from app.services.ingest.normalize import normalize_date, normalize_verzuim, date_columns
from app.services.ingest.pipeline import to_canonical


def test_normalize_date_formats():
    assert normalize_date("20260419") == "2026-04-19"      # yyyymmdd
    assert normalize_date("22-04-1990") == "1990-04-22"    # NL dag-eerst
    assert normalize_date("2026-04-19T00:00:00Z") == "2026-04-19"
    assert normalize_date("2026-02-30") == "2026-02-30"    # ongeldig -> ongewijzigd
    assert normalize_date("") == ""                        # leeg blijft leeg
    assert normalize_date("geen datum") == "geen datum"    # niet-datum blijft staan


def test_date_columns_by_name():
    cols = date_columns(["StartDate", "Naam", "Geboortedatum", "BSN"])
    assert "StartDate" in cols and "Geboortedatum" in cols
    assert "BSN" not in cols and "Naam" not in cols


def test_pipeline_normalizes_value_but_keeps_raw():
    headers = ["EmployeeId", "StartDate", "AbsenceTypeId"]
    rows = [{"EmployeeId": "1", "StartDate": "20260101", "AbsenceTypeId": "Ziek"}]
    cf = to_canonical("Profit_Illness.xml", headers, rows, total=1, standard="algemeen")
    assert cf.record_type is not None
    cell_date = cf.rows[0].cells["StartDate"]
    cell_verz = cf.rows[0].cells["AbsenceTypeId"]
    # value genormaliseerd
    assert cell_date.value == "2026-01-01"
    assert cell_verz.value == normalize_verzuimtype("Ziek")
    # raw ongewijzigd
    assert cell_date.raw == "20260101"
    assert cell_verz.raw == "Ziek"
    # legacy-rijen ongewijzigd (validators zien nog steeds de ruwe waarden)
    assert cf.to_legacy_rows()[0]["StartDate"] == "20260101"
    assert cf.to_legacy_rows()[0]["AbsenceTypeId"] == "Ziek"


def test_no_standard_leaves_value_as_raw():
    cf = to_canonical("x.csv", ["StartDate"], [{"StartDate": "20260101"}])
    # zonder standard: geen normalisatie, value == raw
    assert cf.rows[0].cells["StartDate"].value == "20260101"


def test_empty_date_cell_untouched():
    cf = to_canonical("Profit_Illness.xml", ["EmployeeId", "StartDate"],
                      [{"EmployeeId": "1", "StartDate": ""}], total=1, standard="algemeen")
    assert cf.rows[0].cells["StartDate"].value == ""
