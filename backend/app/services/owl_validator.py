"""
owl_validator.py — Ontology-driven structural & relational validation
=====================================================================
Part 1 of the OWL + SPARQL pipeline.

Produces two SEPARATE scores:
  structural_score  — OWL class-level field conformance (0-100)
  relational_score  — cross-file referential integrity (0-100)

Does NOT modify existing beschikbaarheid/kwaliteit/rhadix scores.

Architecture
------------
structural_validation(files_data, field_rules)
  • For every field with a concept_uri:
    - Verify the field value maps to a valid OWL concept
    - Verify that concept is within the expected subclass hierarchy
    - Verify property range constraints (xsd:string, xsd:date, etc.)
  → structural_score, structural_issues[]

relational_validation(files_data, field_rules)
  • For every declared FK relationship:
    - werkovereenkomst.personeelsnummer ⊆ medewerker.personeelsnummer
    - verzuim.personeelsnummer          ⊆ medewerker.personeelsnummer
    - functie.personeelsnummer          ⊆ medewerker.personeelsnummer (if present)
  → relational_score, relational_issues[]
"""
from __future__ import annotations
import re
from app.services.dataquality import is_date
from datetime import datetime
from typing import Optional

from app.services.ontology_index import CONCEPTS, PROPERTIES, get_subclasses
from app.services.rules import FIELD_RULES

# ─── Namespace helpers ────────────────────────────────────────────────────────
XSD_DATE   = "http://www.w3.org/2001/XMLSchema#date"
XSD_STRING = "http://www.w3.org/2001/XMLSchema#string"
XSD_INT    = "http://www.w3.org/2001/XMLSchema#integer"
XSD_DEC    = "http://www.w3.org/2001/XMLSchema#decimal"

# ─── Foreign-key relationships between schemas ────────────────────────────────
# (child_schema, child_field, parent_schema, parent_field)
FK_RELATIONS = [
    ("werkovereenkomst", "personeelsnummer", "medewerker", "personeelsnummer"),
    ("verzuim",          "personeelsnummer", "medewerker", "personeelsnummer"),
    ("functie",          "personeelsnummer", "medewerker", "personeelsnummer"),
]

# ─── Structural rules derived from OWL ───────────────────────────────────────

def _build_valid_concept_set(concept_uri: str) -> set[str]:
    """Return the full subclass closure (including self) as a set of URIs."""
    return set(get_subclasses(concept_uri)) | {concept_uri}


def _check_range(val: str, range_uri: str) -> bool:
    """Validate a string value against an XSD range constraint."""
    if not range_uri or not val.strip():
        return True  # empty or no constraint → not a range violation
    if range_uri == XSD_DATE:
        return is_date(val)
    if range_uri in (XSD_INT,):
        return val.strip().lstrip("-").isdigit()
    if range_uri == XSD_DEC:
        try:
            float(val.strip())
            return True
        except ValueError:
            return False
    return True  # xsd:string and unknown ranges always pass


# Map FIELD_RULES.allowedValues concept_uri → name for lookup
def _build_allowed_uri_map(field_rules_entry: dict) -> dict[str, str]:
    """Build {concept_uri: label} from allowedValues list."""
    return {
        av["concept_uri"]: av.get("label", av.get("value", ""))
        for av in field_rules_entry.get("allowedValues", [])
        if isinstance(av, dict) and av.get("concept_uri")
    }


def validate_structural(
    files_data: list[dict],
    max_issues: int = 500,
) -> dict:
    """
    Structural validation: OWL class-level conformance.

    Parameters
    ----------
    files_data : list of {filename, schema_key, rows[], mapping{}}

    Returns
    -------
    {
        structural_score : float 0-100
        structural_issues: list[{filename, schema_key, field, source_row,
                                  current_value, expected_concept,
                                  issue_type, message, severity}]
        checks_total     : int
        checks_passed    : int
        rule_coverage    : list[{schema_key, field, concept_uri, checks}]
    }
    """
    issues: list[dict] = []
    checks_total  = 0
    checks_passed = 0
    rule_coverage: list[dict] = []

    for fd in files_data:
        schema_key = fd.get("schema_key") or ""
        filename   = fd.get("filename", "")
        rows       = fd.get("rows", [])
        mapping    = fd.get("mapping", {})

        field_rules = FIELD_RULES.get(schema_key, {})
        if not field_rules:
            continue

        for field_key, rule in field_rules.items():
            concept_uri = rule.get("concept_uri")
            if not concept_uri:
                continue

            # Resolve actual column name in this file
            col_name = mapping.get(field_key) or field_key
            range_uri = None

            # Try to find a PROPERTY that provides range info for this concept
            for prop_uri, prop in PROPERTIES.items():
                if prop.get("domain") == concept_uri or prop.get("range") == concept_uri:
                    range_uri = prop.get("range") or ""
                    break

            # Allowed-value concept set (for enum-like fields)
            allowed_uri_map = _build_allowed_uri_map(rule)
            valid_uris = _build_valid_concept_set(concept_uri) if not allowed_uri_map else set(allowed_uri_map.keys())

            field_checks = 0
            field_passes = 0

            for row_idx, row in enumerate(rows):
                val = (row.get(col_name) or "").strip()

                if not val:
                    # Missing value — only fail if required
                    if rule.get("required"):
                        checks_total  += 1
                        field_checks  += 1
                        if len(issues) < max_issues:
                            issues.append({
                                "filename":        filename,
                                "schema_key":      schema_key,
                                "field":           field_key,
                                "source_column":   col_name,
                                "source_row":      row_idx + 2,
                                "current_value":   "",
                                "expected_concept": concept_uri.split("#")[-1],
                                "issue_type":      "missing_required",
                                "message":         f"Verplicht veld «{rule.get('label', field_key)}» is leeg.",
                                "severity":        "error",
                                "validation_layer": "structural",
                            })
                    continue

                checks_total += 1
                field_checks += 1

                failed = False

                # 1. Range constraint check (xsd type)
                if range_uri and not _check_range(val, range_uri):
                    failed = True
                    if len(issues) < max_issues:
                        issues.append({
                            "filename":        filename,
                            "schema_key":      schema_key,
                            "field":           field_key,
                            "source_column":   col_name,
                            "source_row":      row_idx + 2,
                            "current_value":   val,
                            "expected_concept": concept_uri.split("#")[-1],
                            "issue_type":      "range_violation",
                            "message":         f"Waarde «{val}» voldoet niet aan XSD range «{range_uri.split('#')[-1]}».",
                            "severity":        "warning",
                            "validation_layer": "structural",
                        })

                # 2. Allowed-value concept-URI check (enum fields)
                if allowed_uri_map:
                    norm_val = val.lower().strip()
                    matched_uri = None
                    for av in rule.get("allowedValues", []):
                        if isinstance(av, dict):
                            if av.get("value", "").lower() == norm_val:
                                matched_uri = av.get("concept_uri")
                                break
                    if matched_uri and matched_uri not in valid_uris:
                        failed = True
                        if len(issues) < max_issues:
                            issues.append({
                                "filename":        filename,
                                "schema_key":      schema_key,
                                "field":           field_key,
                                "source_column":   col_name,
                                "source_row":      row_idx + 2,
                                "current_value":   val,
                                "expected_concept": concept_uri.split("#")[-1],
                                "issue_type":      "subclass_violation",
                                "message":         (f"Waarde-concept «{matched_uri.split('#')[-1]}» "
                                                    f"is geen geldige subklasse van «{concept_uri.split('#')[-1]}»."),
                                "severity":        "error",
                                "validation_layer": "structural",
                            })

                if not failed:
                    checks_passed += 1
                    field_passes  += 1

            rule_coverage.append({
                "schema_key":  schema_key,
                "field":       field_key,
                "concept_uri": concept_uri,
                "checks":      field_checks,
                "passed":      field_passes,
            })

    structural_score = round(checks_passed / checks_total * 100, 1) if checks_total else 100.0

    return {
        "structural_score":  structural_score,
        "structural_issues": issues,
        "checks_total":      checks_total,
        "checks_passed":     checks_passed,
        "rule_coverage":     rule_coverage,
    }


# ─── Relational validation (cross-file FK integrity) ─────────────────────────

def validate_relational(files_data: list[dict]) -> dict:
    """
    Relational validation: referential integrity between schemas.

    Checks declared FK_RELATIONS. Reports every dangling reference.

    Returns
    -------
    {
        relational_score  : float 0-100
        relational_issues : list[{child_file, child_schema, child_field,
                                   source_row, current_value,
                                   parent_schema, parent_field, message}]
        fk_results        : list[{relation, child_file, parent_file,
                                   total, orphaned, pass_rate}]
    }
    """
    # Build index: schema_key → {col → set of values}
    schema_index: dict[str, dict[str, set]] = {}
    schema_to_file: dict[str, str] = {}

    for fd in files_data:
        sk  = fd.get("schema_key") or ""
        rows = fd.get("rows", [])
        mapping = fd.get("mapping", {})
        if not sk:
            continue
        schema_to_file[sk] = fd.get("filename", sk)
        idx: dict[str, set] = {}
        for field_key in FIELD_RULES.get(sk, {}):
            col = mapping.get(field_key) or field_key
            idx[field_key] = {(r.get(col) or "").strip() for r in rows if (r.get(col) or "").strip()}
        schema_index[sk] = idx

    issues: list[dict] = []
    fk_results: list[dict] = []
    total_refs   = 0
    total_passed = 0

    for child_sk, child_fld, parent_sk, parent_fld in FK_RELATIONS:
        if child_sk not in schema_index or parent_sk not in schema_index:
            continue

        parent_values = schema_index[parent_sk].get(parent_fld, set())
        if not parent_values:
            continue  # parent table not uploaded — skip silently

        child_file = schema_to_file.get(child_sk, child_sk)

        # Find the actual child file data
        child_fd = next((fd for fd in files_data if fd.get("schema_key") == child_sk), None)
        if not child_fd:
            continue

        child_mapping = child_fd.get("mapping", {})
        child_col = child_mapping.get(child_fld) or child_fld
        child_rows = child_fd.get("rows", [])

        orphaned = 0
        for row_idx, row in enumerate(child_rows):
            val = (row.get(child_col) or "").strip()
            if not val:
                continue
            total_refs += 1
            if val in parent_values:
                total_passed += 1
            else:
                orphaned += 1
                if len(issues) < 500:
                    issues.append({
                        "child_file":    child_file,
                        "child_schema":  child_sk,
                        "child_field":   child_fld,
                        "source_row":    row_idx + 2,
                        "current_value": val,
                        "parent_schema": parent_sk,
                        "parent_field":  parent_fld,
                        "severity":      "error",
                        "issue_type":    "referential_integrity",
                        "message":       (f"Personeelsnummer «{val}» in {child_sk}.{child_fld} "
                                          f"bestaat niet in {parent_sk}.{parent_fld}."),
                        "validation_layer": "relational",
                    })

        total_in_child = sum(1 for r in child_rows if (r.get(child_col) or "").strip())
        fk_results.append({
            "relation":    f"{child_sk}.{child_fld} → {parent_sk}.{parent_fld}",
            "child_file":  child_file,
            "parent_file": schema_to_file.get(parent_sk, parent_sk),
            "total":       total_in_child,
            "orphaned":    orphaned,
            "pass_rate":   round((total_in_child - orphaned) / total_in_child * 100, 1) if total_in_child else 100.0,
        })

    relational_score = round(total_passed / total_refs * 100, 1) if total_refs else 100.0

    return {
        "relational_score":  relational_score,
        "relational_issues": issues,
        "fk_results":        fk_results,
        "total_refs":        total_refs,
        "total_passed":      total_passed,
    }
