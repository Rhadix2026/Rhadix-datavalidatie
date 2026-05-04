"""
Tests voor einddatum-validatie bij werkovereenkomsten.

Scenario's:
  1. Tijdelijk contract MET einddatum    → geen error
  2. Tijdelijk contract ZONDER einddatum → error met persoonsnummer
  3. Vast contract ZONDER einddatum      → geen error (alleen info)
  4. auto_map: exacte kolom wint van substring-match (regression test mapping-bug)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.validator import run_file_checks, auto_map, KIKV_REFERENCE

SCHEMA   = "werkovereenkomst"
ALIASES  = KIKV_REFERENCE[SCHEMA]["col_aliases"]

# ─── helpers ──────────────────────────────────────────────────────────────────

def issues_by_id(issues: list) -> dict:
    return {i["id"]: i for i in issues}

def make_mapping(headers: list) -> dict:
    return auto_map(headers, ALIASES)

# ─── Scenario 1 ───────────────────────────────────────────────────────────────

def test_tijdelijk_met_einddatum_geen_error():
    """Tijdelijk contract met ingevulde einddatum → géén 'missing_einddatum_temp' error."""
    headers = ["DienstverbandNummer", "PersoneelsNummer", "OvereenkomstType", "StartDatum", "EindDatum"]
    mapping = make_mapping(headers)

    rows = [
        {
            "DienstverbandNummer": "D001",
            "PersoneelsNummer":    "P100",
            "OvereenkomstType":    "bepaalde tijd",
            "StartDatum":          "01/01/2024",
            "EindDatum":           "31/12/2024",
        },
        {
            "DienstverbandNummer": "D002",
            "PersoneelsNummer":    "P101",
            "OvereenkomstType":    "jaarcontract",
            "StartDatum":          "01/03/2024",
            "EindDatum":           "28/02/2025",
        },
    ]

    issues = issues_by_id(run_file_checks(SCHEMA, rows, mapping))

    assert "missing_einddatum_temp" not in issues, (
        f"Onverwachte error voor tijdelijk contract mét einddatum: {issues.get('missing_einddatum_temp')}"
    )
    print("✓  Scenario 1 geslaagd: tijdelijk + einddatum → geen error")

# ─── Scenario 2 ───────────────────────────────────────────────────────────────

def test_tijdelijk_zonder_einddatum_geeft_error_met_persoon():
    """Tijdelijk contract ZONDER einddatum → error die het persoonsnummer toont."""
    headers = ["DienstverbandNummer", "PersoneelsNummer", "OvereenkomstType", "StartDatum", "EindDatum"]
    mapping = make_mapping(headers)

    rows = [
        {   # tijdelijk, ZONDER einddatum → moet falen
            "DienstverbandNummer": "D003",
            "PersoneelsNummer":    "P200",
            "OvereenkomstType":    "bepaalde tijd",
            "StartDatum":          "01/01/2024",
            "EindDatum":           "",
        },
        {   # tijdelijk, MET einddatum → moet slagen
            "DienstverbandNummer": "D004",
            "PersoneelsNummer":    "P201",
            "OvereenkomstType":    "halfjaarcontract",
            "StartDatum":          "01/06/2024",
            "EindDatum":           "30/11/2024",
        },
    ]

    issues = issues_by_id(run_file_checks(SCHEMA, rows, mapping))

    assert "missing_einddatum_temp" in issues, \
        "Verwachtte error 'missing_einddatum_temp' maar die ontbreekt"

    issue = issues["missing_einddatum_temp"]
    assert issue["severity"] == "error", \
        f"Verwacht severity='error', maar kreeg '{issue['severity']}'"
    assert issue["count"] == 1, \
        f"Verwacht count=1 (alleen P200), maar count={issue['count']}"
    assert "P200" in (issue.get("detail") or ""), \
        f"Verwacht persoon P200 in detail, maar detail='{issue.get('detail')}'"

    print(f"✓  Scenario 2 geslaagd: tijdelijk zonder einddatum → error (detail: '{issue['detail']}')")

# ─── Scenario 3 ───────────────────────────────────────────────────────────────

def test_vast_zonder_einddatum_geen_error():
    """Vast contract ('onbepaalde tijd') zonder einddatum → géén error, max. een info."""
    headers = ["DienstverbandNummer", "PersoneelsNummer", "OvereenkomstType", "StartDatum", "EindDatum"]
    mapping = make_mapping(headers)

    rows = [
        {
            "DienstverbandNummer": "D005",
            "PersoneelsNummer":    "P300",
            "OvereenkomstType":    "onbepaalde tijd",
            "StartDatum":          "01/01/2020",
            "EindDatum":           "",   # actief contract, geen einddatum verwacht
        },
    ]

    issues = issues_by_id(run_file_checks(SCHEMA, rows, mapping))

    assert "missing_einddatum_temp" not in issues, \
        f"Onverwachte error voor vast contract: {issues.get('missing_einddatum_temp')}"

    if "open_contracts" in issues:
        assert issues["open_contracts"]["severity"] == "info", \
            "Open contract moet severity='info' zijn, niet error/warning"

    print("✓  Scenario 3 geslaagd: vast contract zonder einddatum → geen error")

# ─── Scenario 4 — regression: auto_map mapping-bug ───────────────────────────

def test_automap_exacte_kolom_wint_van_substring():
    """
    Regression test voor de auto_map substring-bug:
    Als een bestand de kolommen ['Datum', 'EindDatum'] bevat (in die volgorde),
    moet 'EindDatum' worden gemapped op het veld 'einddatum', niet 'Datum'.
    'Datum' normalized = 'datum', wat als substring in 'einddatum' zit.
    Met de oude implementatie zou 'Datum' ten onrechte winnen.
    """
    headers_tricky = ["Datum", "EindDatum", "StartDatum", "OvereenkomstType",
                      "PersoneelsNummer", "DienstverbandNummer"]
    mapping = make_mapping(headers_tricky)

    assert mapping.get("einddatum") == "EindDatum", (
        f"Bug: auto_map heeft '{mapping.get('einddatum')}' gemapped op 'einddatum' "
        f"in plaats van 'EindDatum'"
    )
    assert mapping.get("startdatum") == "StartDatum", (
        f"Startdatum incorrectly mapped to '{mapping.get('startdatum')}'"
    )
    print(f"✓  Scenario 4 geslaagd: auto_map mapping correct → einddatum='{mapping['einddatum']}'")

# ─── runner ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        test_tijdelijk_met_einddatum_geen_error,
        test_tijdelijk_zonder_einddatum_geeft_error_met_persoon,
        test_vast_zonder_einddatum_geen_error,
        test_automap_exacte_kolom_wint_van_substring,
    ]

    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except AssertionError as e:
            print(f"✗  {t.__name__} GEFAALD: {e}")
            failed += 1
        except Exception as e:
            print(f"✗  {t.__name__} EXCEPTION: {e}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"Resultaat: {passed} geslaagd, {failed} gefaald")
    if failed:
        sys.exit(1)
