"""B1 — bron-gestuurde fase-1 flow: fallback-fix, run-cache."""
from app.services.algemeen_validator import _detect_template
from app.services import run_cache


def test_kikv_csv_niet_misdetect_als_afas():
    # medewerker.csv (KIK-V, NL-kolommen): heeft BSN maar geen EmployeeId
    headers = ["MedewerkerID", "Voornaam", "Achternaam", "Geboortedatum", "BSN", "Geslacht", "Email"]
    assert _detect_template("medewerker.csv", headers) != "employees"


def test_echte_afas_employees_wel_herkend():
    headers = ["EmployeeId", "BSN", "DateOfBirth", "FirstName", "BirthName", "Gender", "Mail"]
    assert _detect_template("profit_employees.xml", headers) == "employees"


def test_run_cache_overschrijft_en_clear():
    run_cache.clear("u1")
    run_cache.set_current("u1", "afas", [{"filename": "a.csv", "headers": ["X"], "rows": [{"X": "1"}]}])
    cur = run_cache.get_current("u1")
    assert cur and cur["source"] == "afas" and len(cur["files"]) == 1
    # nieuwe scan overschrijft de vorige (= cache wissen bij nieuwe scan)
    run_cache.set_current("u1", "ons", [{"filename": "b.csv", "headers": ["Y"], "rows": []}])
    assert run_cache.get_current("u1")["source"] == "ons"
    run_cache.clear("u1")
    assert run_cache.get_current("u1") is None


def test_route_vangnet_zib_csv_niet_door_algemeen():
    # ZIB-CSV: algemeen herkent niets, ZIB wel -> vangnet zou naar 'zib' schakelen
    from app.services.zib_rules import detect_zib_schema
    from app.services.algemeen_validator import _detect_template
    headers = ["BSN", "Voornaam", "Achternaam", "Geboortedatum", "Geslacht"]
    assert _detect_template("patient.csv", headers) is None
    assert detect_zib_schema("patient.csv") == "patient"
