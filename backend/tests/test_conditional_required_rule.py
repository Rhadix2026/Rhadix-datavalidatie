"""
Stap 2 slice 2.7: generieke conditioneel-verplicht-regel.
`run_profile` signaleert 'einddatum ontbreekt bij tijdelijk contract' met dezelfde
telling als KIK-V's bespoke `missing_einddatum_temp` (verdict-pariteit).
"""
from app.services.validator import run_file_checks, auto_map, KIKV_REFERENCE
from app.services.controls import run_conditional_required
from app.services.control_profiles import profile_from_kikv, run_profile
from app.services.ingest.pipeline import to_canonical

HEADERS = ["dienstverbandnummer", "personeelsnummer", "overeenkomsttype", "startdatum", "einddatum"]
ROWS = [
    {"dienstverbandnummer": "1", "personeelsnummer": "1", "overeenkomsttype": "bepaalde tijd",  "startdatum": "2024-01-01", "einddatum": ""},           # tijdelijk zonder eind -> fail
    {"dienstverbandnummer": "2", "personeelsnummer": "2", "overeenkomsttype": "jaarcontract",   "startdatum": "2024-01-01", "einddatum": ""},           # tijdelijk zonder eind -> fail
    {"dienstverbandnummer": "3", "personeelsnummer": "3", "overeenkomsttype": "onbepaalde tijd","startdatum": "2024-01-01", "einddatum": ""},           # vast, open -> geen fail
    {"dienstverbandnummer": "4", "personeelsnummer": "4", "overeenkomsttype": "bepaalde tijd",  "startdatum": "2024-01-01", "einddatum": "2024-12-31"}, # tijdelijk met eind -> ok
]


def _legacy_missing_temp():
    mapping = auto_map(HEADERS, KIKV_REFERENCE["werkovereenkomst"]["col_aliases"])
    issues = run_file_checks("werkovereenkomst", ROWS, mapping)
    it = next((i for i in issues if i.get("id") == "missing_einddatum_temp"), None)
    return it["count"] if it else 0


def test_run_conditional_required_basic():
    f = run_conditional_required(["bepaalde tijd", "onbepaalde tijd", "jaarcontract"],
                                 ["", "", ""], {"bepaalde tijd", "jaarcontract"}, "einddatum")
    assert f is not None and f.check == "conditional_required"
    assert f.count == 2


def test_profile_has_conditional_required():
    p = profile_from_kikv("werkovereenkomst")
    assert any(c["trigger"] == "overeenkomsttype" and c["target"] == "einddatum"
               for c in p.conditional_required)


def test_run_profile_conditional_parity():
    legacy = _legacy_missing_temp()
    assert legacy == 2
    p = profile_from_kikv("werkovereenkomst")
    cf = to_canonical("Werkovereenkomst.csv", HEADERS, ROWS, total=len(ROWS), standard="kikv")
    assert cf.record_type == "werkovereenkomst"
    findings = run_profile(cf, p)
    cf2 = next((f for f in findings if f.check == "conditional_required"), None)
    assert cf2 is not None and cf2.severity == "error"
    assert cf2.count == legacy
