"""
Borgt dat alle 6 AFAS Profit HRM GetConnectors herkend worden door
_detect_template — zowel op de officiële GetConnector_Profit_*-bestandsnamen
als op de korte Nederlandse namen. Voorkomt 'Bestandstype niet herkend'.
"""
from app.services.algemeen_validator import _detect_template

# (bestandsnaam, headers) -> verwachte template-key
CASES = [
    ("GetConnector_Profit_Employers_Werkgevers.json",
     ["EmployerId", "Name", "OrganisationId", "AddressLine1", "UnitId"], "employers"),
    ("GetConnector_Profit_Functions_Functies.json",
     ["Employer", "FunctionId", "FunctionDesc", "Blocked", "FunctionType"], "functions"),
    ("GetConnector_Profit_OrganizationChart_Organigram.json",
     ["Unitd", "UnitDesc", "Level", "Manager", "UpperUnit", "Level1"], "organisation"),
    ("GetConnector_Profit_Employees_Medeewerkergegevens.json",
     ["EmployeeId", "BSN", "Mail"], "employees"),
    ("GetConnector_Profit_Timetable_Medewerker_roosters.json",
     ["EmployeeId", "StartDate", "HoursPerWeek"], "timetable"),
    ("GetConnector_Profit_Illness_Medewerker_verzuimverloop.json",
     ["EmployeeId", "StartDate", "AbsenceTypeId"], "illness"),
]


def test_alle_afas_connectors_herkend_op_getconnector_naam():
    for filename, headers, expected in CASES:
        assert _detect_template(filename, headers) == expected, f"{filename} -> verwacht {expected}"


def test_korte_nl_namen_blijven_werken():
    assert _detect_template("Werkgevers.json", ["EmployerId", "OrganisationId", "AddressLine1"]) == "employers"
    assert _detect_template("Functies.json", ["FunctionId", "FunctionDesc", "FunctionType"]) == "functions"
    assert _detect_template("Organigram.json", ["UnitDesc", "UpperUnit", "Level1"]) == "organisation"


def test_organigram_op_headers_zonder_naam():
    # Header-signature alleen (bestandsnaam geeft geen hint)
    assert _detect_template("export_123.json", ["Unitd", "UnitDesc", "UpperUnit", "Level1"]) == "organisation"
