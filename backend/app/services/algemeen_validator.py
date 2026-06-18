"""
algemeen_validator.py
Pre-scan validatie voor generieke AFAS Profit XML-exports en Nedap ONS CSV-exports.
Geen KIK-V of ZIB kennis vereist — checkt beschikbaarheid en basisformaten.
"""
from __future__ import annotations
import re
from typing import Any

# ── AFAS Profit veldtemplates ──────────────────────────────────────────────────
# Elke file-type heeft verplichte velden (required) en optionele velden (optional)
# met bijbehorend type voor formaatvalidatie.

AFAS_TEMPLATES: dict[str, dict] = {
    "employees": {
        "label": "AFAS Medewerkers",
        "icon": "👤",
        "color": "#6366f1",
        "source": "afas",
        "detect": ["profit_employees", "profit_employee"],
        # Header-signatures die AFAS onderscheiden van ONS
        "header_signature": {"bsn", "employeeid", "mail"},
        "required": {
            "EmployeeId":       "id",
            "BSN":              "bsn",
            "DateOfBirth":      "date",
            "FirstName":        "text",
            "BirthName":        "text",
            "Gender":           "gender",
            "EmploymentStart":  "date",
            "Mail":             "email",
        },
        "optional": {
            "DateBirth":        "date",   # basic variant
            "PersonId":         "id",
            "EmploymentEnd":    "date",
            "EmploymentType":   "text",
            "FunctionId":       "text",
            "FunctionDesc":     "text",
            "OrgUnit":          "text",
            "FTE":              "number",
            "HourPerWeek":      "number",
            "ZIPCode":          "postcode",
            "City":             "text",
            "Mobile":           "phone",
        },
    },
    "timetable": {
        "label": "AFAS Werkroosters",
        "icon": "📅",
        "color": "#0ea5e9",
        "source": "afas",
        "detect": ["profit_timetable", "timetable"],
        "header_signature": {"hoursperweek", "startdate", "employeeid"},
        "required": {
            "EmployeeId":   "id",
            "StartDate":    "date",
            "HoursPerWeek": "number",
        },
        "optional": {
            "EndDate":      "date",
            "MinHours":     "number",
            "MaxHours":     "number",
            "DaysPerWeek":  "number",
            "PartTime":     "number",
        },
    },
    "illness": {
        "label": "AFAS Verzuim",
        "icon": "🏥",
        "color": "#ef4444",
        "source": "afas",
        "detect": ["profit_illness", "illness"],
        "header_signature": {"absencetypeid", "startdate", "employeeid"},
        "required": {
            "EmployeeId":    "id",
            "StartDate":     "date",
            "AbsenceTypeId": "text",
        },
        "optional": {
            "BSN":          "bsn",
            "EndDate":      "date",
            "Presence":     "number",
            "ReasonId":     "text",
            "ReportDate":   "date",
        },
    },
    "employers": {
        "label": "AFAS Werkgevers",
        "icon": "🏢",
        "color": "#0891b2",
        "source": "afas",
        "detect": ["profit_employers", "profit_employer", "employers", "werkgever"],
        "header_signature": {"employerid", "organisationid", "addressline1"},
        "required": {
            "EmployerId":     "id",
            "Name":           "text",
        },
        "optional": {
            "OrganisationId": "id",
            "AddressLine1":   "text",
            "AddressLine3":   "text",
            "AddressLine4":   "text",
            "DimAx1":         "text",
            "DimAx2":         "text",
            "DimAx3":         "text",
            "DimAx4":         "text",
            "DimAx5":         "text",
            "UnitId":         "number",
        },
    },
    "functions": {
        "label": "AFAS Functies",
        "icon": "🧩",
        "color": "#7c3aed",
        "source": "afas",
        "detect": ["profit_functions", "profit_function", "functies", "functie"],
        "header_signature": {"functionid", "functiondesc", "functiontype"},
        "required": {
            "FunctionId":   "id",
            "FunctionDesc": "text",
        },
        "optional": {
            "Employer":     "id",
            "Blocked":      "text",
            "FunctionType": "text",
        },
    },
    "organisation": {
        "label": "AFAS Organigram",
        "icon": "🗂️",
        "color": "#d97706",
        "source": "afas",
        "detect": ["profit_organizationchart", "organizationchart", "organigram"],
        "header_signature": {"unitdesc", "upperunit", "level1"},
        "required": {
            "Unitd":    "id",
            "UnitDesc": "text",
        },
        "optional": {
            "Level":     "text",
            "Manager":   "text",
            "UpperUnit": "id",
            "Level0":    "text",
            "Level1":    "text",
            "Level2":    "text",
            "Level3":    "text",
            "StartDate": "date",
            "EndDate":   "date",
        },
    },
}

# ── Nedap ONS veldtemplates ────────────────────────────────────────────────────
# Op basis van de ONS OpenAPI-spec (https://ons-api.nl):
#   Person, Employee, PresenceLog, moves.Absence, Team

ONS_TEMPLATES: dict[str, dict] = {
    "ons_employees": {
        "label": "ONS Medewerkers",
        "icon": "👤",
        "color": "#0ea5e9",
        "source": "ons",
        "detect": ["ons_employee", "ons_person", "ons_medewerker", "nedap_employee"],
        "header_signature": {"identificationno", "dateofbirth", "firstname"},
        "required": {
            "uuid":             "id",
            "firstName":        "text",
            "name":             "text",
            "identificationNo": "bsn",
            "dateOfBirth":      "date",
            "gender":           "gender",
        },
        "optional": {
            "emailAddress":      "email",
            "mobilePhone":       "phone",
            "mobilePhoneNumber": "phone",
            "homeEmailAddress":  "email",
            "teamName":          "text",
        },
    },
    "ons_contracts": {
        "label": "ONS Contracten",
        "icon": "📋",
        "color": "#0ea5e9",
        "source": "ons",
        "detect": ["ons_contract", "ons_employment", "nedap_contract"],
        "header_signature": {"contractid", "employeeobjectid", "begindate"},
        "required": {
            "contractId":        "id",
            "employeeObjectId":  "id",
            "beginDate":         "date",
            "fixedHoursPerWeek": "number",
        },
        "optional": {
            "endDate":           "date",
            "varHoursPerWeek":   "number",
            "contractType":      "text",
            "teamName":          "text",
            "teamObjectId":      "id",
        },
    },
    "ons_presence": {
        "label": "ONS Aanwezigheidsregistratie",
        "icon": "🕐",
        "color": "#0ea5e9",
        "source": "ons",
        "detect": ["ons_presence", "presencelog", "ons_aanwezigheid"],
        "header_signature": {"employeeobjectid", "duration", "activityobjectid"},
        "required": {
            "employeeObjectId":  "id",
            "date":              "date",
            "startDate":         "date",
            "duration":          "number",
        },
        "optional": {
            "clientObjectId":    "id",
            "endDate":           "date",
            "activityObjectId":  "id",
        },
    },
    "ons_absence": {
        "label": "ONS Verzuim",
        "icon": "🏥",
        "color": "#0ea5e9",
        "source": "ons",
        "detect": ["ons_absence", "ons_verzuim", "moves_absence"],
        "header_signature": {"employeenumber", "begindatetime", "absencetype"},
        "required": {
            "employeeNumber":  "id",
            "beginDateTime":   "date",
            "absenceType":     "text",
        },
        "optional": {
            "remoteId":              "id",
            "expectedEndDateTime":   "date",
        },
    },
    "ons_teams": {
        "label": "ONS Teams",
        "icon": "🏢",
        "color": "#0ea5e9",
        "source": "ons",
        "detect": ["ons_team", "ons_location", "nedap_team"],
        "header_signature": {"identificationno", "externcode", "begindate"},
        "required": {
            "id":               "id",
            "name":             "text",
            "identificationNo": "id",
            "beginDate":        "date",
        },
        "optional": {
            "endDate":    "date",
            "externCode": "text",
            "agbCode":    "text",
        },
    },
}

# Gecombineerde template-map (AFAS + ONS)
ALL_TEMPLATES: dict[str, dict] = {**AFAS_TEMPLATES, **ONS_TEMPLATES}

# ── Formaatvalidatoren ─────────────────────────────────────────────────────────

def _valid_bsn(val: str) -> bool:
    v = re.sub(r'\D', '', val)
    if len(v) not in (8, 9):
        return False
    v = v.zfill(9)
    total = sum(int(v[i]) * (9 - i) for i in range(8)) - int(v[8])
    return total % 11 == 0

def _valid_date(val: str) -> bool:
    val = val.strip()
    patterns = [
        r'^\d{4}-\d{2}-\d{2}$',          # yyyy-mm-dd
        r'^\d{2}-\d{2}-\d{4}$',          # dd-mm-yyyy
        r'^\d{2}/\d{2}/\d{4}$',          # dd/mm/yyyy
    ]
    return any(re.match(p, val) for p in patterns)

def _valid_email(val: str) -> bool:
    return bool(re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', val.strip()))

def _valid_postcode(val: str) -> bool:
    return bool(re.match(r'^\d{4}\s?[A-Za-z]{2}$', val.strip()))

def _valid_number(val: str) -> bool:
    try: float(val.replace(',', '.')); return True
    except: return False

def _valid_gender(val: str) -> bool:
    return val.strip().upper() in ('M', 'V', 'W', 'O', 'MALE', 'FEMALE', 'MAN', 'VROUW')

VALIDATORS = {
    "bsn":      _valid_bsn,
    "date":     _valid_date,
    "email":    _valid_email,
    "postcode": _valid_postcode,
    "number":   _valid_number,
    "gender":   _valid_gender,
    "id":       lambda v: bool(v.strip()),
    "text":     lambda v: bool(v.strip()),
    "phone":    lambda v: bool(re.sub(r'\D', '', v)),
}

# ── Detectie ───────────────────────────────────────────────────────────────────

def _detect_template(filename: str, headers: list[str]) -> str | None:
    """
    Detecteert het template-type op basis van bestandsnaam en headers.
    Strategie:
      1. Exacte prefix-match op bestandsnaam (bijv. 'ons_' → ONS, 'profit_' → AFAS)
      2. Keyword-match op bestandsnaam
      3. Header-signature: meest specifieke match wint
    """
    fn = filename.lower().replace('_', '').replace('-', '').replace('.', '')
    header_low = {h.lower() for h in headers}

    # 1. Naam-gebaseerde detectie — doorzoek alle templates (ONS first voor prioriteit)
    for tkey, tpl in {**ONS_TEMPLATES, **AFAS_TEMPLATES}.items():
        for kw in tpl["detect"]:
            kw_norm = kw.replace('_', '')
            if kw_norm in fn:
                return tkey

    # 2. Header-signature: zoek template met meeste overlap
    best_key   = None
    best_score = 0
    for tkey, tpl in ALL_TEMPLATES.items():
        sig = tpl.get("header_signature", set())
        score = len(sig & header_low)
        if score > best_score:
            best_score = score
            best_key   = tkey

    if best_score >= 2:
        return best_key

    # 3. Fallback (legacy)
    if {"bsn", "employeeid"} & header_low:
        return "employees"
    if {"hoursperweek", "startdate", "employeeid"} & header_low:
        return "timetable"
    if {"absencetypeid", "startdate"} & header_low:
        return "illness"
    if {"identificationno", "dateofbirth"} & header_low:
        return "ons_employees"
    if {"contractid", "employeeobjectid"} & header_low:
        return "ons_contracts"
    if {"employeeobjectid", "begindatetime"} & header_low:
        return "ons_absence"

    return None

# ── Hoofd-validator ────────────────────────────────────────────────────────────

def validate_algemeen(files_input: list[dict]) -> dict:
    """
    files_input: list van { filename, headers, rows }
    Returns: { file_results, summary }
    """
    file_results = []

    for fi in files_input:
        filename = fi["filename"]
        headers  = fi["headers"]
        rows     = fi["rows"]
        tkey     = _detect_template(filename, headers)

        if not tkey:
            file_results.append({
                "filename":    filename,
                "template":    None,
                "label":       "Onbekend bestandstype",
                "icon":        "❓",
                "color":       "#9ca3af",
                "rows":        len(rows),
                "issues":      [{"field": "-", "type": "unknown_type",
                                 "message": f"Bestandstype niet herkend: {filename}",
                                 "severity": "warning", "count": 1}],
                "completeness": 0,
                "quality":      0,
                "rhadix_index": 0,
            })
            continue

        tpl         = ALL_TEMPLATES[tkey]
        req_fields  = tpl["required"]
        opt_fields  = tpl["optional"]
        all_fields  = {**req_fields, **opt_fields}
        header_set  = set(headers)
        issues      = []

        # ── Beschikbaarheid: verplichte velden aanwezig? ───────────────────
        present_req = {f: f in header_set for f in req_fields}
        n_present   = sum(present_req.values())
        completeness = round(100 * n_present / max(len(req_fields), 1))

        for f, present in present_req.items():
            if not present:
                issues.append({
                    "field":    f,
                    "type":     "missing_field",
                    "message":  f"Verplicht veld '{f}' ontbreekt in de export.",
                    "severity": "error",
                    "count":    len(rows),
                })

        # ── Kwaliteit: formaatvalidatie op aanwezige velden ────────────────
        quality_checks = 0
        quality_passed = 0
        MAX_ISSUES     = 100

        for field, ftype in all_fields.items():
            if field not in header_set:
                continue
            validator = VALIDATORS.get(ftype, lambda v: True)
            field_issues: list[dict] = []
            field_pass = 0
            field_total = 0

            for idx, row in enumerate(rows):
                val = (row.get(field) or "").strip()
                if not val:
                    continue
                field_total += 1
                if validator(val):
                    field_pass += 1
                elif len(field_issues) < 5:
                    field_issues.append({
                        "row":   idx + 2,
                        "value": val[:50],
                    })

            if field_total > 0:
                quality_checks += field_total
                quality_passed += field_pass
                fail_count = field_total - field_pass
                if fail_count > 0 and len(issues) < MAX_ISSUES:
                    severity = "error" if field in req_fields else "warning"
                    issues.append({
                        "field":    field,
                        "type":     f"invalid_{ftype}",
                        "message":  f"{fail_count} van {field_total} waarden in '{field}' "
                                    f"voldoen niet aan het {ftype}-formaat.",
                        "severity": severity,
                        "count":    fail_count,
                        "examples": field_issues,
                    })

        quality = round(100 * quality_passed / max(quality_checks, 1))
        rhadix_index = round(completeness * quality / 100)

        file_results.append({
            "filename":     filename,
            "template":     tkey,
            "label":        tpl["label"],
            "icon":         tpl["icon"],
            "color":        tpl["color"],
            "rows":         len(rows),
            "completeness": completeness,
            "quality":      quality,
            "rhadix_index": rhadix_index,
            "issues":       issues,
            "required_fields": list(req_fields.keys()),
            "present_fields":  sorted(header_set & set(all_fields.keys())),
            "missing_required": [f for f, p in present_req.items() if not p],
        })

    # ── Samenvatting ───────────────────────────────────────────────────────────
    known = [r for r in file_results if r["template"]]
    overall_completeness = round(sum(r["completeness"] for r in known) / max(len(known), 1))
    overall_quality      = round(sum(r["quality"]      for r in known) / max(len(known), 1))
    overall_index        = round(overall_completeness * overall_quality / 100)

    return {
        "standard":     "algemeen",
        "file_results": file_results,
        "summary": {
            "completeness": overall_completeness,
            "quality":      overall_quality,
            "rhadix_index": overall_index,
            "total_rows":   sum(r["rows"] for r in file_results),
            "total_files":  len(file_results),
            "error_count":  sum(len([i for i in r["issues"] if i["severity"] == "error"]) for r in file_results),
            "warn_count":   sum(len([i for i in r["issues"] if i["severity"] == "warning"]) for r in file_results),
        },
    }
