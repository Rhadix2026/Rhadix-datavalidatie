"""
Tests voor de AFAS-bevindingen (test echte-klantdata, 2026-06):
  1. Verzuimsoort: AFAS-codes (Z, ZW, ...) en -omschrijving ('Ziek') zijn geldig.
  2. parse_date: ISO/jaar-eerst + yyyymmdd + dd-mm-yyyy; eind<start werkt op AFAS-ISO.
  3. Kruisverwijzing: personeelsnummer-normalisatie (000164 == 164) → geen false-positive,
     en de bevinding levert uitklapbare detailrijen.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.validator import (
    run_file_checks, run_cross_checks, auto_map, parse_date, KIKV_REFERENCE,
)
from app.services.rules import normalize_verzuimtype


def by_id(issues): return {i["id"]: i for i in issues}

VERZ_ALIASES = KIKV_REFERENCE["verzuim"]["col_aliases"]


# ─── 1. Verzuimsoort: AFAS-codes/omschrijving geldig ──────────────────────────
def test_afas_verzuim_codes_geldig():
    headers = ["EmployeeId", "StartDate", "AbsenceTypeId", "AbsenceTypeDesc"]
    mapping = auto_map(headers, VERZ_ALIASES)
    rows = [
        {"EmployeeId": "001", "StartDate": "2026-04-22T00:00:00Z", "AbsenceTypeId": "Z",   "AbsenceTypeDesc": "Ziek"},
        {"EmployeeId": "002", "StartDate": "2026-04-22T00:00:00Z", "AbsenceTypeId": "ZW",  "AbsenceTypeDesc": "Zwangerschap / bevalling"},
        {"EmployeeId": "003", "StartDate": "2026-04-22T00:00:00Z", "AbsenceTypeId": "D",   "AbsenceTypeDesc": "Arbeidsongeschikt door derde"},
        {"EmployeeId": "004", "StartDate": "2026-04-22T00:00:00Z", "AbsenceTypeId": "ZZW", "AbsenceTypeDesc": "Ziek als gevolg van zwangerschap"},
    ]
    issues = by_id(run_file_checks("verzuim", rows, mapping))
    assert "invalid_soort" not in issues, f"AFAS-codes onterecht afgekeurd: {issues.get('invalid_soort')}"


def test_echt_ongeldige_verzuimsoort_wel_afgekeurd():
    headers = ["EmployeeId", "StartDate", "AbsenceTypeId"]
    mapping = auto_map(headers, VERZ_ALIASES)
    rows = [{"EmployeeId": "001", "StartDate": "2026-04-22T00:00:00Z", "AbsenceTypeId": "XYZ"}]
    issues = by_id(run_file_checks("verzuim", rows, mapping))
    assert "invalid_soort" in issues and issues["invalid_soort"]["count"] == 1


def test_normalize_verzuimtype_mapping():
    assert normalize_verzuimtype("Z") == "ziek"
    assert normalize_verzuimtype("ZW") == "zwangerschapsverlof"
    assert normalize_verzuimtype("Ziek") == "ziek"
    assert normalize_verzuimtype("ziek") == "ziek"          # al KIK-V
    assert normalize_verzuimtype("ONBEKEND") == "onbekend"  # blijft (wordt afgekeurd)


# ─── 2. parse_date ────────────────────────────────────────────────────────────
def test_parse_date_formaten():
    from datetime import datetime
    assert parse_date("2026-04-22T00:00:00Z") == datetime(2026, 4, 22)
    assert parse_date("2026-04-22")            == datetime(2026, 4, 22)
    assert parse_date("20260422")              == datetime(2026, 4, 22)
    assert parse_date("22-04-2026")            == datetime(2026, 4, 22)
    assert parse_date("22/04/2026")            == datetime(2026, 4, 22)
    assert parse_date("rommel") is None
    assert parse_date("") is None


def test_eind_voor_start_werkt_op_iso():
    headers = ["EmployeeId", "StartDate", "EndDate", "AbsenceTypeId"]
    mapping = auto_map(headers, VERZ_ALIASES)
    rows = [{"EmployeeId": "001", "StartDate": "2026-04-22T00:00:00Z",
             "EndDate": "2026-04-20T00:00:00Z", "AbsenceTypeId": "Z"}]
    issues = by_id(run_file_checks("verzuim", rows, mapping))
    assert "end_before_start" in issues, "eind<start niet gedetecteerd op ISO-datums"


# ─── 3. Kruisverwijzing: voorloopnul-normalisatie ─────────────────────────────
def _fd(schema, headers, rows):
    return {"mapping": auto_map(headers, KIKV_REFERENCE[schema]["col_aliases"]),
            "rows": rows}

def test_voorloopnul_geen_false_positive():
    files = {
        "medewerker": _fd("medewerker", ["PersoneelsNummer"],
                          [{"PersoneelsNummer": "164"}, {"PersoneelsNummer": "165"}]),
        "verzuim": _fd("verzuim", ["EmployeeId", "StartDate", "AbsenceTypeId"],
                       [{"EmployeeId": "000164", "StartDate": "2026-01-01T00:00:00Z", "AbsenceTypeId": "Z"},
                        {"EmployeeId": "000165", "StartDate": "2026-01-01T00:00:00Z", "AbsenceTypeId": "Z"}]),
    }
    cross = by_id(run_cross_checks(files))
    assert "verz_unknown" not in cross, f"Onterechte false-positive door voorloopnullen: {cross.get('verz_unknown')}"


def test_echt_onbekende_persoon_met_uitklapbare_rijen():
    files = {
        "medewerker": _fd("medewerker", ["PersoneelsNummer"], [{"PersoneelsNummer": "164"}]),
        "verzuim": _fd("verzuim", ["EmployeeId", "StartDate", "AbsenceTypeId"],
                       [{"EmployeeId": "000164", "StartDate": "2026-01-01T00:00:00Z", "AbsenceTypeId": "Z"},
                        {"EmployeeId": "000999", "StartDate": "2026-01-01T00:00:00Z", "AbsenceTypeId": "Z"}]),
    }
    cross = by_id(run_cross_checks(files))
    assert "verz_unknown" in cross
    iss = cross["verz_unknown"]
    assert iss["count"] == 1
    assert iss["rows"] and iss["rows"][0]["personId"] == "000999"   # uitklapbare detailrij aanwezig
