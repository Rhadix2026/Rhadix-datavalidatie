"""
algemeen_benchmark.py
─────────────────────
Benchmark van een geladen AFAS Profit HRM-export tegen het
*Referentieontwerp KIK-V v6.0 Profit HRM (AFAS)*.

Aanroepen ná de pre-scan/checks (validate_algemeen). Vergelijkt de daadwerkelijk
aangeleverde bronvelden met de velden die het referentieontwerp voorschrijft en
laat per gegevenselement / KIK-V-concept zien waar de verschillen zitten.

Alleen AFAS-bestanden tellen mee — het referentieontwerp is AFAS-specifiek.
"""
from __future__ import annotations
from typing import Any

from app.services.algemeen_validator import _detect_template, AFAS_TEMPLATES
from app.services.reference_design_afas import (
    REFERENCE_META,
    REFERENCE_ELEMENTEN,
    UITWISSELPROFIELEN,
    PROFIEL_NOTE,
    COVERED, MISSING, OUT_OF_SCOPE,
)


def _present_field_names(files_input: list[dict]) -> tuple[dict[str, list[str]], list[str]]:
    """
    Bepaal welke AFAS-velden aanwezig zijn in de aangeleverde bestanden.

    Returns:
      present: { lowercased_veldnaam: [bestandsnamen die het veld bevatten] }
      afas_files: lijst van herkende AFAS-bestandsnamen
    """
    present: dict[str, list[str]] = {}
    afas_files: list[str] = []

    for fi in files_input:
        filename = fi.get("filename", "")
        headers  = fi.get("headers", []) or []
        tkey     = _detect_template(filename, headers)
        # Alleen AFAS-templates meenemen
        if not tkey or tkey not in AFAS_TEMPLATES:
            continue
        afas_files.append(filename)
        for h in headers:
            key = h.strip().lower()
            if not key:
                continue
            present.setdefault(key, [])
            if filename not in present[key]:
                present[key].append(filename)

    return present, afas_files


def _is_present(field: str | None, aliases: list[str], present: dict[str, list[str]]) -> list[str]:
    """Geef de bestanden waarin het veld (of een alias) voorkomt; lege lijst = afwezig."""
    if not field:
        return []
    for cand in [field, *aliases]:
        files = present.get(cand.strip().lower())
        if files:
            return files
    return []


def benchmark_against_reference(files_input: list[dict]) -> dict[str, Any]:
    """
    files_input: list van { filename, headers, rows }
    Returns: benchmark-resultaat (zie structuur onderaan).
    """
    present, afas_files = _present_field_names(files_input)
    applicable = len(afas_files) > 0

    elementen_out: list[dict] = []
    referenced_fields: set[str] = set()

    tot_covered = tot_missing = tot_oos = 0

    for el in REFERENCE_ELEMENTEN:
        concepts_out: list[dict] = []
        el_covered = el_missing = el_oos = 0

        for c in el["concepts"]:
            field   = c.get("field")
            aliases = c.get("aliases", []) or []
            if field:
                referenced_fields.add(field.lower())
                for a in aliases:
                    referenced_fields.add(a.lower())

            if not field:
                status   = OUT_OF_SCOPE
                file_hits = []
                el_oos += 1
            else:
                file_hits = _is_present(field, aliases, present)
                if file_hits:
                    status = COVERED
                    el_covered += 1
                else:
                    status = MISSING
                    el_missing += 1

            concepts_out.append({
                "concept":    c["concept"],
                "afas_attr":  c.get("afas_attr", ""),
                "field":      field,
                "status":     status,
                "present_in": file_hits,
                "transform":  c.get("transform", ""),
                "note":       c.get("note", ""),
            })

        denom = el_covered + el_missing
        coverage = round(100 * el_covered / denom) if denom else None
        elementen_out.append({
            "key":          el["key"],
            "label":        el["label"],
            "covered":      el_covered,
            "missing":      el_missing,
            "out_of_scope": el_oos,
            "coverage":     coverage,
            "concepts":     concepts_out,
        })
        tot_covered += el_covered
        tot_missing += el_missing
        tot_oos     += el_oos

    denom = tot_covered + tot_missing
    overall_coverage = round(100 * tot_covered / denom) if denom else 0

    # Velden die wél zijn aangeleverd maar niet in het referentieontwerp voorkomen
    extra_fields = sorted(
        {f for f in present.keys() if f not in referenced_fields}
    )

    return {
        "applicable":  applicable,
        "reference":   REFERENCE_META,
        "afas_files":  afas_files,
        "summary": {
            "coverage":             overall_coverage,
            "concepts_total":       tot_covered + tot_missing + tot_oos,
            "concepts_covered":     tot_covered,
            "concepts_missing":     tot_missing,
            "concepts_out_of_scope": tot_oos,
        },
        "elementen":   elementen_out,
        "extra_fields": extra_fields,
        "profielen": {
            "note":  PROFIEL_NOTE,
            "items": UITWISSELPROFIELEN,
        },
    }
