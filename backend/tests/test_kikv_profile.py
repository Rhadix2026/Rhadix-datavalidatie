"""
Tests voor Stap 2 slice 2.4: KIK-V veld-niveau naar profiel. KIK-V heeft bespoke
regels (dubbele identifiers, cross-field, berekeningen) die in run_file_checks
blijven; hier tonen we VERDICT-pariteit voor de veld-niveau checks (datum,
contracttype-codelijst) tegen KIK-V's eigen logica. Puur functioneel.
"""
from app.services.dataquality import is_date
from app.services.rules import CONTRACTTYPE_VALUES
from app.services.controls import check_value
from app.services.control_profiles import profile_from_kikv, run_profile
from app.services.ingest.pipeline import to_canonical


def test_profile_from_kikv_werkovereenkomst():
    p = profile_from_kikv("werkovereenkomst")
    assert p is not None
    assert p.required.get("startdatum") == "date"
    assert p.required.get("overeenkomsttype") == "codelist"
    assert p.codelists.get("overeenkomsttype") == CONTRACTTYPE_VALUES
    assert p.required.get("personeelsnummer") == "text"
    assert profile_from_kikv("bestaat-niet") is None


def test_date_verdict_parity_with_is_date():
    for v in ["2026-01-01", "2026-02-30", "20260101", "notadate", "22-04-1990"]:
        assert check_value("date", v) == is_date(v)


def test_contracttype_verdict_parity_with_kikv():
    valid = CONTRACTTYPE_VALUES[0]
    for v in [valid, valid.upper(), "geencontract", ""]:
        # KIK-V keurt alleen NIET-lege waarden en checkt v.lower().strip() in allowed
        kikv_valid = (not v.strip()) or (v.lower().strip() in CONTRACTTYPE_VALUES)
        assert check_value("codelist", v, allowed=CONTRACTTYPE_VALUES) == kikv_valid


def test_run_profile_kikv_flags_invalid_contracttype_and_date():
    p = profile_from_kikv("werkovereenkomst")
    headers = ["personeelsnummer", "dienstverbandnummer", "overeenkomsttype", "startdatum"]
    rows = [
        {"personeelsnummer": "1", "dienstverbandnummer": "A", "overeenkomsttype": CONTRACTTYPE_VALUES[0], "startdatum": "2026-01-01"},
        {"personeelsnummer": "2", "dienstverbandnummer": "B", "overeenkomsttype": "geencontract", "startdatum": "2026-02-30"},
    ]
    cf = to_canonical("werkovereenkomsten.csv", headers, rows, total=2, standard="kikv")
    assert cf.record_type == "werkovereenkomst"
    findings = run_profile(cf, p)
    ct = next((f for f in findings if f.concept == "overeenkomsttype"), None)
    dt = next((f for f in findings if f.concept == "startdatum"), None)
    assert ct is not None and ct.check == "codelist" and ct.count == 1
    assert dt is not None and dt.check == "date" and dt.count == 1
