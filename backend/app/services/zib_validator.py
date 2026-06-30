"""
zib_validator.py — Stap 1 + Stap 2 validatie voor ZIB's (Nictiz 2020)

Stap 1: zijn de verplichte ZIB-velden aanwezig en niet leeg?
Stap 2: kunnen de waarden worden gevalideerd (BSN-elfproef, datumformaat, codelijsten)?

Retourneert hetzelfde resultaatformaat als de KIK-V validator,
zodat de frontend hetzelfde Dashboard/Beschikbaarheid kan tonen.
"""

import re
from typing import Any
from app.services.zib_rules import ZIB_FIELD_RULES, detect_zib_schema
from app.services.dataquality import is_date
from app.services.prescan import (
    detect_format, validate_format,
    prescan_columns, prescan_quality_stats,
)

# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalize(val: Any) -> str:
    return str(val or "").strip().lower()

def _bsn_elfproef(val: str) -> bool:
    """Valideert een BSN via de elfproef."""
    digits = re.sub(r"\D", "", str(val or ""))
    if len(digits) not in (8, 9):
        return False
    if len(digits) == 8:
        digits = "0" + digits
    total = sum(int(d) * (9 - i) for i, d in enumerate(digits[:8]))
    total -= int(digits[8])
    return total % 11 == 0

def _auto_map(headers: list[str], field_rules: dict) -> dict[str, str]:
    """
    Mapt interne veldnamen naar kolomnamen in het bestand.
    Prioriteit: exacte match > alias-match > substring-match.
    """
    norm_headers = {h.strip().lower().replace(" ", "_").replace("-", "_"): h for h in headers}
    field_map: dict[str, str] = {}

    for field, rules in field_rules.items():
        aliases = [field] + rules.get("aliases", [])
        matched = None
        # 1. Exacte match
        for alias in aliases:
            a = alias.strip().lower().replace(" ", "_").replace("-", "_")
            if a in norm_headers:
                matched = norm_headers[a]
                break
        # 2. Substring-match (alias bevat headernaam of vice versa)
        if not matched:
            for alias in aliases:
                a = alias.strip().lower().replace(" ", "_").replace("-", "_")
                for nh, orig in norm_headers.items():
                    if a in nh or nh in a:
                        matched = orig
                        break
                if matched:
                    break
        if matched:
            field_map[field] = matched

    return field_map

# ── Waarde-validatie ──────────────────────────────────────────────────────────

def _validate_value(field: str, value: Any, rules: dict) -> list[str]:
    """Retourneert een lijst van issues voor een waarde (leeg = OK)."""
    issues = []
    val_str = str(value).strip() if value is not None else ""

    if not val_str:
        if rules.get("required"):
            issues.append(f"Verplicht veld is leeg")
        return issues

    vtype = rules.get("type", "string")

    if vtype == "bsn":
        digits = re.sub(r"\D", "", val_str)
        if not digits.isdigit():
            issues.append(f"BSN «{val_str}» bevat niet-numerieke tekens")
        elif len(digits) not in (8, 9):
            issues.append(f"BSN «{val_str}» heeft {len(digits)} cijfers (verwacht 8 of 9)")
        elif not _bsn_elfproef(val_str):
            issues.append(f"BSN «{val_str}» is ongeldig (elfproef mislukt)")

    elif vtype == "date":
        if not is_date(val_str):
            issues.append(f"Waarde «{val_str}» is geen geldige datum (verwacht dd/mm/yyyy)")

    elif vtype == "code":
        allowed_values = [av["value"] for av in rules.get("allowed_values", [])]
        if allowed_values and _normalize(val_str) not in allowed_values:
            issues.append(
                f"Waarde «{val_str}» is niet toegestaan. "
                f"Geldige waarden: {', '.join(allowed_values)}"
            )

    elif vtype == "numeric":
        try:
            float(val_str.replace(",", "."))
        except ValueError:
            issues.append(f"Waarde «{val_str}» is geen getal")

    elif vtype == "string":
        # Auto-detect format op veldnaam en valideer via open standaard
        fmt = detect_format(field)
        if fmt:
            ok, msg = validate_format(fmt, val_str)
            if not ok:
                issues.append(msg)

    return issues

# ── Rhadix Index formule ──────────────────────────────────────────────────────
#
# Rhadix Index = Databeschikbaarheid × Datakwaliteit
#
# Databeschikbaarheid = (aanwezige verplichte veldinstanties / verwachte) × 100
# Datakwaliteit       = (kwalitatief goedgekeurde veldinstanties / aanwezige) × 100
# Dataverzuim         = 100 - Rhadix Index

def _rhadix_index(beschikbaarheid: float, kwaliteit: float) -> float:
    return round(beschikbaarheid * kwaliteit / 100, 1)

# ── Per-bestand validatie ─────────────────────────────────────────────────────

def validate_zib_file(schema_key: str, rows: list[dict], filename: str) -> dict:
    """
    Valideert één bestand tegen de ZIB-regels.

    Retourneert:
    {
        schema_key, filename, field_map,
        beschikbaarheid_score,   # % verplichte velden aanwezig
        kwaliteit_score,         # % aanwezige velden met geldige waarde
        rhadix_index,            # beschikbaarheid × kwaliteit / 100
        dataverzuim,             # 100 - rhadix_index
        score,                   # alias voor rhadix_index (backward compat)
        issues: [...]
    }
    """
    field_rules = ZIB_FIELD_RULES.get(schema_key, {})
    if not rows or not field_rules:
        return {
            "schema_key": schema_key, "filename": filename,
            "field_map": {},
            "beschikbaarheid_score": 0.0, "kwaliteit_score": 0.0,
            "rhadix_index": 0.0, "dataverzuim": 100.0, "score": 0.0,
            "issues": [],
        }

    headers = list(rows[0].keys())
    field_map = _auto_map(headers, field_rules)

    issues: list[dict] = []

    # Tellers voor de twee dimensies
    aanwezig_vereist = 0      # verplichte veldinstanties die aanwezig zijn
    verwacht_vereist = 0      # totaal verwachte verplichte veldinstanties
    kwalitatief_goed = 0      # aanwezige veldinstanties die de kwaliteitscheck passeren
    aanwezig_totaal  = 0      # totaal aanwezige veldinstanties (verplicht + optioneel)

    for field, rules in field_rules.items():
        col_name      = field_map.get(field)
        concept_label = rules.get("concept_label", field)
        is_required   = rules.get("required", False)

        # Kolom ontbreekt helemaal
        if not col_name:
            if is_required:
                verwacht_vereist += len(rows)   # alle rijen missen dit veld
                issues.append({
                    "label": concept_label,
                    "severity": "error",
                    "detail": f"Kolom niet gevonden in bestand ({filename})",
                    "count": len(rows),
                    "rows": [],
                    "allowed_values": rules.get("allowed_values", []),
                    "source": f"ZIB: {rules.get('concept_uri', '')}",
                })
            continue

        error_rows:   list[dict] = []
        value_errors: list[dict] = []
        empty_count = 0

        for i, row in enumerate(rows):
            value   = row.get(col_name, row.get(field, ""))
            val_str = str(value).strip() if value is not None else ""

            if is_required:
                verwacht_vereist += 1

            if not val_str:
                empty_count += 1
                if is_required:
                    # Ontbreekt → niet aanwezig, niet goed
                    if len(error_rows) < 10:
                        error_rows.append({
                            "rowNumber": i + 1, "personId": "",
                            "field": concept_label, "currentValue": "",
                            "expectedValue": rules.get("description", ""),
                            "message": "Verplicht veld is leeg",
                        })
                # Optioneel leeg veld telt niet mee voor kwaliteit
            else:
                # Veld is aanwezig
                if is_required:
                    aanwezig_vereist += 1
                aanwezig_totaal += 1

                val_issues = _validate_value(field, value, rules)
                if not val_issues:
                    kwalitatief_goed += 1
                else:
                    if len(value_errors) < 10:
                        value_errors.append({
                            "rowNumber": i + 1, "personId": "",
                            "field": concept_label,
                            "currentValue": str(value)[:60],
                            "expectedValue": rules.get("description", ""),
                            "message": "; ".join(val_issues),
                        })

        if empty_count > 0 and is_required:
            issues.append({
                "label": concept_label,
                "severity": "error",
                "detail": f"{empty_count} rijen met lege waarde",
                "count": empty_count,
                "rows": error_rows,
                "allowed_values": rules.get("allowed_values", []),
                "source": f"ZIB: {rules.get('concept_uri', '')}",
            })

        if value_errors:
            issues.append({
                "label": f"{concept_label} — ongeldige waarde",
                "severity": "error",
                "detail": f"{len(value_errors)} rijen met ongeldige waarde",
                "count": len(value_errors),
                "rows": value_errors,
                "allowed_values": rules.get("allowed_values", []),
                "source": f"ZIB: {rules.get('concept_uri', '')}",
            })

    # ── Pre-scan extra kolommen (buiten ZIB-schema) ───────────────────────────
    known_col_names = set(field_map.values())
    extra_issues = prescan_columns(rows, known_cols=known_col_names)
    extra_checked, extra_errors = prescan_quality_stats(rows, known_cols=known_col_names)
    issues.extend(extra_issues)

    # ── Scores berekenen (inclusief extra kolommen in kwaliteit) ──────────────
    beschikbaarheid    = round(aanwezig_vereist / verwacht_vereist * 100, 1) if verwacht_vereist > 0 else 100.0
    combined_aanwezig  = aanwezig_totaal + extra_checked
    combined_goed      = kwalitatief_goed + (extra_checked - extra_errors)
    kwaliteit          = round(combined_goed / combined_aanwezig * 100, 1) if combined_aanwezig > 0 else 100.0
    rhadix             = _rhadix_index(beschikbaarheid, kwaliteit)
    dataverzuim        = round(100 - rhadix, 1)

    return {
        "schema_key":           schema_key,
        "filename":             filename,
        "field_map":            field_map,
        "beschikbaarheid_score": beschikbaarheid,
        "kwaliteit_score":      kwaliteit,
        "rhadix_index":         rhadix,
        "dataverzuim":          dataverzuim,
        "score":                rhadix,   # backward compatibility
        "issues":               issues,
    }

# ── Hoofd-functie: volledige ZIB-scan ────────────────────────────────────────

def validate_zib(files: list[dict]) -> dict:
    """
    Valideert een lijst van bestanden tegen de ZIB-standaard.

    Returns
    -------
    {
        standard: "zib",
        beschikbaarheid_score,  # gemiddelde beschikbaarheid
        kwaliteit_score,        # gemiddelde kwaliteit
        rhadix_index,           # beschikbaarheid × kwaliteit / 100
        dataverzuim,            # 100 - rhadix_index
        score,                  # alias voor rhadix_index
        file_results: [...],
        run_id: None,
        created_at: None,
    }
    """
    file_results = []

    for f in files:
        filename   = f["filename"]
        rows       = f["rows"]
        schema_key = detect_zib_schema(filename)

        if not schema_key:
            file_results.append({
                "schema_key": "onbekend", "filename": filename,
                "field_map": {},
                "beschikbaarheid_score": None, "kwaliteit_score": None,
                "rhadix_index": None, "dataverzuim": None, "score": None,
                "issues": [{
                    "label": "Schema niet herkend", "severity": "warning",
                    "detail": (
                        f"Bestandsnaam «{filename}» is niet herkend als ZIB-schema. "
                        "Verwacht: patient, probleem, medicatieafspraak, allergie."
                    ),
                    "count": 0, "rows": [],
                }],
            })
            continue

        result = validate_zib_file(schema_key, rows, filename)
        file_results.append(result)

    # Gemiddelden over bestanden met een score
    scored = [r for r in file_results if r.get("rhadix_index") is not None]
    avg_beschikbaarheid = round(sum(r["beschikbaarheid_score"] for r in scored) / len(scored), 1) if scored else 0.0
    avg_kwaliteit       = round(sum(r["kwaliteit_score"]       for r in scored) / len(scored), 1) if scored else 0.0
    avg_rhadix          = _rhadix_index(avg_beschikbaarheid, avg_kwaliteit)
    avg_dataverzuim     = round(100 - avg_rhadix, 1)

    return {
        "standard":             "zib",
        "beschikbaarheid_score": avg_beschikbaarheid,
        "kwaliteit_score":      avg_kwaliteit,
        "rhadix_index":         avg_rhadix,
        "dataverzuim":          avg_dataverzuim,
        "score":                avg_rhadix,
        "file_results":         file_results,
        "run_id":               None,
        "created_at":           None,
    }
