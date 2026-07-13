"""
Tests voor Stap 2 slice 2.5: de generieke uniciteits-regel (relationele check).
Kern: `run_profile` signaleert dubbele identifiers met dezelfde telling als
KIK-V's bespoke `dup_id` in run_file_checks (verdict-pariteit). Puur functioneel.
"""
from app.services.validator import run_file_checks, auto_map, KIKV_REFERENCE
from app.services.controls import run_unique
from app.services.control_profiles import profile_from_kikv, run_profile
from app.services.ingest.pipeline import to_canonical

HEADERS = ["EmployeeId", "dateOfBirth"]
ROWS = [
    {"EmployeeId": "1", "dateOfBirth": "1980-01-01"},
    {"EmployeeId": "1", "dateOfBirth": "1981-01-01"},   # duplicaat
    {"EmployeeId": "2", "dateOfBirth": "1982-01-01"},
    {"EmployeeId": "3", "dateOfBirth": "1983-01-01"},
    {"EmployeeId": "3", "dateOfBirth": "1984-01-01"},   # duplicaat
]


def _legacy_dup_count():
    mapping = auto_map(HEADERS, KIKV_REFERENCE["medewerker"]["col_aliases"])
    issues = run_file_checks("medewerker", ROWS, mapping)
    dup = next((i for i in issues if i.get("id") == "dup_id"), None)
    return dup["count"] if dup else 0


def test_run_unique_basic():
    f = run_unique(["1", "1", "2", "3", "3"], "personeelsnummer")
    assert f is not None and f.check == "unique"
    assert f.count == 4          # 4 rijen betrokken bij een duplicaat
    assert run_unique(["1", "2", "3"], "x") is None
    # lege waarden tellen niet mee
    assert run_unique(["", "", "1"], "x") is None


def test_profile_has_unique_identifier():
    p = profile_from_kikv("medewerker")
    assert "personeelsnummer" in p.unique


def test_run_profile_unique_parity_with_kikv_dup_id():
    legacy = _legacy_dup_count()
    assert legacy == 4
    p = profile_from_kikv("medewerker")
    cf = to_canonical("Medewerkers.csv", HEADERS, ROWS, total=len(ROWS), standard="kikv")
    assert cf.record_type == "medewerker"
    findings = run_profile(cf, p)
    uf = next((f for f in findings if f.check == "unique"), None)
    assert uf is not None and uf.severity == "error"
    assert uf.count == legacy      # verdict-pariteit met KIK-V dup_id
