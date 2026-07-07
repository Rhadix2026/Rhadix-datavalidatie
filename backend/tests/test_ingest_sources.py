"""
Tests voor Slice 2 (Stap 1): de bronherkenning-façade `detect_source`. Kern:
de façade moet EXACT hetzelfde record-/schema-type teruggeven als de bestaande
detectoren (pariteit), en de pipeline moet daarmee het canonieke model vullen.
Puur functioneel; geen DB of HTTP.
"""
from app.services.validator import detect_schema as legacy_kikv
from app.services.zib_rules import detect_zib_schema as legacy_zib
from app.services.algemeen_validator import _detect_template as legacy_algemeen
from app.services.ingest.sources import detect_source, SourceMatch, STANDARDS
from app.services.ingest.pipeline import to_canonical, ingest

AFAS_EMP_HEADERS = ["BSN", "EmployeeId", "Mail", "FirstName"]

# (filename, headers, standard) -> vergeleken met de bijbehorende legacy-detector
CASES = [
    ("Medewerkers.csv",        [],                "kikv"),
    ("werkovereenkomsten.csv", [],                "kikv"),
    ("verzuim_2026.csv",       [],                "kikv"),
    ("willekeurig.csv",        [],                "kikv"),   # onbekend -> None
    ("patienten.csv",          [],                "zib"),
    ("medicatie_overzicht.xlsx", [],              "zib"),
    ("allergie.csv",           [],                "zib"),
    ("Profit_Employees.xml",   AFAS_EMP_HEADERS,  "algemeen"),
    ("ons_absence.csv",        [],                "algemeen"),
    ("onbekend.xlsx",          [],                "algemeen"),
]


def _legacy(standard, filename, headers):
    if standard == "kikv":
        return legacy_kikv(filename, list(headers))
    if standard == "zib":
        return legacy_zib(filename)
    return legacy_algemeen(filename, list(headers))


def test_facade_matches_legacy_detectors():
    for filename, headers, standard in CASES:
        expected = _legacy(standard, filename, headers)
        got = detect_source(filename, headers, standard)
        assert got.record_type == expected, f"{filename} ({standard}): {got.record_type} != {expected}"
        assert got.standard == standard
        assert got.recognized == (expected is not None)


def test_known_records_resolve():
    assert detect_source("Medewerkers.csv", [], "kikv").record_type == "medewerker"
    assert detect_source("patienten.csv", [], "zib").record_type == "patient"
    assert detect_source("Profit_Employees.xml", AFAS_EMP_HEADERS, "algemeen").record_type == "employees"


def test_unknown_not_recognized():
    m = detect_source("willekeurig.csv", [], "kikv")
    assert m.record_type is None and m.recognized is False


def test_standards_constant():
    assert set(STANDARDS) == {"kikv", "zib", "algemeen"}


def test_pipeline_populates_source_on_canonical():
    cf = to_canonical("patienten.csv", ["Patient", "BSN"], [{"BSN": "x"}], total=1, standard="zib")
    assert cf.source_type == "zib"
    assert cf.record_type == "patient"


def test_pipeline_leaves_source_none_without_standard():
    # slice-1 gedrag blijft: zonder standard geen bronherkenning
    cf = to_canonical("patienten.csv", ["BSN"], [{"BSN": "x"}])
    assert cf.source_type is None and cf.record_type is None


def test_ingest_passes_standard_through():
    files = ingest([{"filename": "Medewerkers.csv", "headers": [], "rows": [{"a": "1"}], "total": 1}],
                   standard="kikv")
    assert files[0].record_type == "medewerker" and files[0].source_type == "kikv"
