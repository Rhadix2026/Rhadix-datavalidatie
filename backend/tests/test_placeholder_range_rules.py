"""
Stap 2 slice 2.8: generieke placeholder- en bereik-regels.
Verdict-pariteit met KIK-V's bespoke `placeholder` (personeelsnummer '99999') en
`invalid_pct` (verzuimpercentage 0-100).
"""
from app.services.validator import run_file_checks, auto_map, KIKV_REFERENCE
from app.services.controls import run_forbidden_value, run_range
from app.services.control_profiles import profile_from_kikv, run_profile
from app.services.ingest.pipeline import to_canonical


def _legacy(schema, headers, rows, issue_id):
    mapping = auto_map(headers, KIKV_REFERENCE[schema]["col_aliases"])
    issues = run_file_checks(schema, rows, mapping)
    it = next((i for i in issues if i.get("id") == issue_id), None)
    return it["count"] if it else 0


# ── placeholder (medewerker) ──
MW_HEADERS = ["personeelsnummer", "geboortedatum"]
MW_ROWS = [
    {"personeelsnummer": "1",     "geboortedatum": "1980-01-01"},
    {"personeelsnummer": "99999", "geboortedatum": "1981-01-01"},   # placeholder
    {"personeelsnummer": "99999", "geboortedatum": "1982-01-01"},   # placeholder
    {"personeelsnummer": "3",     "geboortedatum": "1983-01-01"},
]


def test_run_forbidden_basic():
    f = run_forbidden_value(["1", "99999", "99999", "3"], "personeelsnummer", ["99999"])
    assert f is not None and f.check == "forbidden" and f.count == 2


def test_profile_placeholder_parity():
    legacy = _legacy("medewerker", MW_HEADERS, MW_ROWS, "placeholder")
    assert legacy == 2
    p = profile_from_kikv("medewerker")
    assert "personeelsnummer" in p.forbidden
    cf = to_canonical("Medewerkers.csv", MW_HEADERS, MW_ROWS, total=len(MW_ROWS), standard="kikv")
    findings = run_profile(cf, p)
    ff = next((f for f in findings if f.check == "forbidden"), None)
    assert ff is not None and ff.count == legacy


# ── verzuimpercentage bereik ──
VZ_HEADERS = ["personeelsnummer", "startmoment", "verzuimpercentage"]
VZ_ROWS = [
    {"personeelsnummer": "1", "startmoment": "2024-01-01", "verzuimpercentage": "50"},   # ok
    {"personeelsnummer": "2", "startmoment": "2024-01-01", "verzuimpercentage": "150"},  # > 100
    {"personeelsnummer": "3", "startmoment": "2024-01-01", "verzuimpercentage": "-5"},   # < 0
    {"personeelsnummer": "4", "startmoment": "2024-01-01", "verzuimpercentage": "abc"},  # niet-numeriek
    {"personeelsnummer": "5", "startmoment": "2024-01-01", "verzuimpercentage": ""},     # leeg -> telt niet
]


def test_run_range_basic():
    f = run_range(["50", "150", "-5", "abc", ""], "verzuimpercentage", 0.0, 100.0)
    assert f is not None and f.check == "range" and f.count == 3


def test_profile_range_parity():
    legacy = _legacy("verzuim", VZ_HEADERS, VZ_ROWS, "invalid_pct")
    assert legacy == 3
    p = profile_from_kikv("verzuim")
    assert "verzuimpercentage" in p.ranges
    cf = to_canonical("Verzuim.csv", VZ_HEADERS, VZ_ROWS, total=len(VZ_ROWS), standard="kikv")
    findings = run_profile(cf, p)
    rf = next((f for f in findings if f.check == "range"), None)
    assert rf is not None and rf.count == legacy
