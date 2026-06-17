"""
Tests voor de benchmark tegen het AFAS-referentieontwerp (algemeen_benchmark.py).
Puur functioneel — geen database of HTTP nodig.
"""
from app.services.algemeen_benchmark import benchmark_against_reference
from app.services.reference_design_afas import COVERED, MISSING, OUT_OF_SCOPE


def _concept_status(result, element_key, concept_substr):
    el = next(e for e in result["elementen"] if e["key"] == element_key)
    c  = next(c for c in el["concepts"] if concept_substr.lower() in c["concept"].lower())
    return c["status"]


def test_volledige_afas_employees_export():
    files = [{
        "filename": "profit_employees.xml",
        "headers": ["EmployeeId", "BSN", "DateOfBirth", "FirstName", "BirthName",
                    "Gender", "EmploymentStart", "EmploymentEnd", "Mail",
                    "EmploymentType", "FunctionId", "OrgUnit", "HourPerWeek"],
        "rows": [{"EmployeeId": "1", "EmploymentStart": "2020-01-01"}],
    }]
    r = benchmark_against_reference(files)
    assert r["applicable"] is True
    assert "profit_employees.xml" in r["afas_files"]
    # Mens-identificatie en geboortedatum gedekt (DateOfBirth = alias van DateBirth)
    assert _concept_status(r, "mens", "identificatie") == COVERED
    assert _concept_status(r, "mens", "Geboortedatum") == COVERED
    # WerkOvereenkomst-velden gedekt
    assert _concept_status(r, "werkovereenkomst", "Functie") == COVERED
    assert _concept_status(r, "werkovereenkomst", "Vestiging") == COVERED
    # Concept zonder bronveld blijft out_of_scope
    assert _concept_status(r, "werkovereenkomst", "Werkgever") == OUT_OF_SCOPE
    # Gewerkte periode is volledig out_of_scope -> coverage None
    gp = next(e for e in r["elementen"] if e["key"] == "gewerkte_periode")
    assert gp["coverage"] is None
    assert gp["covered"] == 0


def test_partiele_export_mist_velden():
    files = [{
        "filename": "profit_employees.xml",
        # FunctionId, OrgUnit, HourPerWeek, EmploymentType ontbreken
        "headers": ["EmployeeId", "DateOfBirth", "EmploymentStart"],
        "rows": [{"EmployeeId": "1"}],
    }]
    r = benchmark_against_reference(files)
    assert _concept_status(r, "werkovereenkomst", "Functie") == MISSING
    assert _concept_status(r, "werkovereenkomst", "Vestiging") == MISSING
    assert _concept_status(r, "werkovereenkomst", "bepaalde tijd") == MISSING
    assert r["summary"]["concepts_missing"] > 0


def test_illness_velden_gemapt():
    files = [{
        "filename": "profit_illness.xml",
        "headers": ["EmployeeId", "StartDate", "EndDate", "AbsenceTypeId", "Presence"],
        "rows": [{"EmployeeId": "1", "StartDate": "2024-01-01", "AbsenceTypeId": "Z"}],
    }]
    r = benchmark_against_reference(files)
    assert _concept_status(r, "verzuimperiode", "startDatum") == COVERED   # Illness.startdate -> StartDate
    assert _concept_status(r, "verzuimperiode", "eindDatum") == COVERED    # Illness.enddate -> EndDate
    assert _concept_status(r, "verzuimperiode", "VerzuimTijdKwaliteit") == COVERED  # Presence


def test_alleen_ons_bestand_niet_van_toepassing():
    files = [{
        "filename": "ons_employees.csv",
        "headers": ["uuid", "firstName", "name", "identificationNo", "dateOfBirth", "gender"],
        "rows": [{"uuid": "x"}],
    }]
    r = benchmark_against_reference(files)
    assert r["applicable"] is False
    assert r["afas_files"] == []


def test_summary_telt_op():
    files = [{
        "filename": "profit_employees.xml",
        "headers": ["EmployeeId", "EmploymentStart"],
        "rows": [{}],
    }]
    r = benchmark_against_reference(files)
    s = r["summary"]
    assert s["concepts_total"] == s["concepts_covered"] + s["concepts_missing"] + s["concepts_out_of_scope"]
    assert 0 <= s["coverage"] <= 100
