"""
Stap 2 slice 2.6: generieke cross-field datumvolgorde-regel.
`run_profile` signaleert 'eindmoment vóór startmoment' met dezelfde telling als
KIK-V's bespoke `end_before_start` in run_file_checks (verdict-pariteit).
"""
from app.services.validator import run_file_checks, auto_map, KIKV_REFERENCE
from app.services.controls import run_date_order
from app.services.control_profiles import profile_from_kikv, run_profile
from app.services.ingest.pipeline import to_canonical

HEADERS = ["personeelsnummer", "startmoment", "eindmoment"]
ROWS = [
    {"personeelsnummer": "1", "startmoment": "2024-01-10", "eindmoment": "2024-01-20"},  # ok
    {"personeelsnummer": "2", "startmoment": "2024-02-10", "eindmoment": "2024-02-05"},  # eind < start
    {"personeelsnummer": "3", "startmoment": "2024-03-01", "eindmoment": ""},            # geen eind
    {"personeelsnummer": "4", "startmoment": "2024-04-15", "eindmoment": "2024-04-01"},  # eind < start
]


def _legacy_end_before_start():
    mapping = auto_map(HEADERS, KIKV_REFERENCE["verzuim"]["col_aliases"])
    issues = run_file_checks("verzuim", ROWS, mapping)
    it = next((i for i in issues if i.get("id") == "end_before_start"), None)
    return it["count"] if it else 0


def test_run_date_order_basic():
    starts = ["2024-01-10", "2024-02-10", "2024-03-01", "2024-04-15"]
    ends   = ["2024-01-20", "2024-02-05", "",          "2024-04-01"]
    f = run_date_order(starts, ends, "eindmoment")
    assert f is not None and f.check == "date_order"
    assert f.count == 2
    assert run_date_order(["2024-01-01"], ["2024-02-01"], "x") is None


def test_profile_has_date_order():
    p = profile_from_kikv("verzuim")
    assert ("startmoment", "eindmoment") in p.date_orders


def test_run_profile_date_order_parity():
    legacy = _legacy_end_before_start()
    assert legacy == 2
    p = profile_from_kikv("verzuim")
    cf = to_canonical("Verzuim.csv", HEADERS, ROWS, total=len(ROWS), standard="kikv")
    assert cf.record_type == "verzuim"
    findings = run_profile(cf, p)
    df = next((f for f in findings if f.check == "date_order"), None)
    assert df is not None and df.severity == "error"
    assert df.count == legacy   # verdict-pariteit met KIK-V end_before_start
