"""
Tests voor Slice 3 (Stap 1): de concept-mapping façade `map_concepts`. Kern: de
façade levert EXACT dezelfde bronkolom->concept-koppeling als de bestaande
mapping-mechanismen (pariteit), en de pipeline vult daarmee CanonicalFile.
field_concepts. Puur functioneel; geen DB of HTTP.
"""
from app.services.validator import auto_map, KIKV_REFERENCE
from app.services.zib_validator import _auto_map as zib_auto_map
from app.services.zib_rules import get_zib_rules
from app.services.algemeen_validator import ALL_TEMPLATES
from app.services.ingest.concepts import map_concepts
from app.services.ingest.pipeline import to_canonical


def _inv(d):
    return {c: f for f, c in d.items() if c}


def test_kikv_parity_with_auto_map():
    rt = "medewerker"
    headers = ["EmployeeId", "dateOfBirth", "OnbekendeKolom"]
    expected = _inv(auto_map(headers, KIKV_REFERENCE[rt]["col_aliases"]))
    assert map_concepts("kikv", rt, headers) == expected
    # een herkende kolom krijgt een concept, onbekende niet
    got = map_concepts("kikv", rt, headers)
    assert got.get("EmployeeId") == "personeelsnummer"
    assert "OnbekendeKolom" not in got


def test_zib_parity_with_auto_map():
    rt = "patient"
    headers = ["BSN", "Naam", "Geboortedatum", "Xyz"]
    expected = _inv(zib_auto_map(headers, get_zib_rules(rt)))
    assert map_concepts("zib", rt, headers) == expected


def test_algemeen_identity_on_template_fields():
    rt = "employees"
    fields = {**ALL_TEMPLATES[rt].get("required", {}), **ALL_TEMPLATES[rt].get("optional", {})}
    some_field = next(iter(fields))
    headers = [some_field, "GeheelOnbekend"]
    got = map_concepts("algemeen", rt, headers)
    assert got.get(some_field) == some_field
    assert "GeheelOnbekend" not in got


def test_unknown_record_type_empty():
    assert map_concepts("kikv", None, ["A"]) == {}
    assert map_concepts("kikv", "bestaat-niet", ["A"]) == {}
    assert map_concepts("kikv", "medewerker", []) == {}


def test_pipeline_populates_field_concepts():
    headers = ["EmployeeId", "dateOfBirth"]
    cf = to_canonical("Medewerkers.csv", headers, [{"EmployeeId": "1", "dateOfBirth": "1980-01-01"}],
                      total=1, standard="kikv")
    assert cf.record_type == "medewerker"
    assert cf.field_concepts.get("EmployeeId") == "personeelsnummer"
    assert cf.concept_for("dateOfBirth") == "geboortedatum"


def test_pipeline_no_concepts_without_standard():
    cf = to_canonical("Medewerkers.csv", ["EmployeeId"], [{"EmployeeId": "1"}])
    assert cf.field_concepts == {}
    assert cf.concept_for("EmployeeId") is None
