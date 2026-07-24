"""
control_profiles.py - Declaratieve profielen (doelarchitectuur Laag 3, Stap 2 - slice 2.2).

Een profiel beschrijft per recordtype welke concepten verplicht/optioneel zijn en
met welke generieke check ze gevalideerd worden. De `run_profile`-runner past de
generieke controles (Laag 2) toe op een `CanonicalFile` (Laag 1) en levert
uniforme bevindingen. "Nieuwe standaard = nieuw profiel, geen nieuwe app."

SLICE 2.2: het profielschema + de runner + het eerste profiel, afgeleid uit de
bestaande Algemeen-templates zodat de uitkomst identiek is aan `validate_algemeen`
(pariteit). Nog niet aangesloten op de endpoints.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from app.services.algemeen_validator import ALL_TEMPLATES
from app.services.zib_rules import ZIB_FIELD_RULES
from app.services.validator import KIKV_REFERENCE
from app.services.controls import Finding, run_column, run_unique, column_values, run_date_order


@dataclass
class Profile:
    """Declaratieve regelset voor één recordtype."""
    record_type: str
    required: dict = field(default_factory=dict)   # {concept: check}
    optional: dict = field(default_factory=dict)   # {concept: check}
    codelists: dict = field(default_factory=dict)  # {concept: [toegestane waarden]}
    unique: list = field(default_factory=list)     # concepten die uniek moeten zijn
    date_orders: list = field(default_factory=list)  # (start_concept, eind_concept)-paren

    @property
    def all_fields(self) -> dict:
        return {**self.required, **self.optional}


def profile_from_algemeen_template(record_type: str) -> Optional[Profile]:
    """Bouw een profiel uit een bestaand Algemeen-template (required/optional -> check)."""
    tpl = ALL_TEMPLATES.get(record_type)
    if not tpl:
        return None
    return Profile(
        record_type=record_type,
        required=dict(tpl.get("required", {})),
        optional=dict(tpl.get("optional", {})),
    )


# ZIB-typen -> generieke check
_ZIB_CHECK = {"bsn": "bsn", "date": "date", "code": "codelist", "numeric": "number",
              "string": "text"}


def profile_from_zib(record_type: str) -> Optional[Profile]:
    """Bouw een profiel uit ZIB_FIELD_RULES (required/type/allowed_values -> check)."""
    rules = ZIB_FIELD_RULES.get(record_type)
    if not rules:
        return None
    required, optional, codelists = {}, {}, {}
    for field_name, r in rules.items():
        check = _ZIB_CHECK.get(r.get("type", "string"), "text")
        (required if r.get("required") else optional)[field_name] = check
        allowed = [av["value"] for av in r.get("allowed_values", []) if "value" in av]
        if allowed:
            codelists[field_name] = allowed
    unique = _KIKV_UNIQUE.get(record_type, [])
    unique = [c for c in unique if c in required or c in optional]
    return Profile(record_type=record_type, required=required, optional=optional,
                   codelists=codelists, unique=unique)


# KIK-V veld-niveau -> generieke check. De bespoke KIK-V-regels (dubbele
# identifiers, cross-field, berekeningsregels) blijven in run_file_checks en
# horen bij een rijker profiel (relationele/berekeningsregels) - latere stap.
# Primaire identifiers die KIK-V op duplicaten controleert (dup_id).
_KIKV_UNIQUE = {"medewerker": ["personeelsnummer"]}
# Cross-field datumvolgorde per recordtype (eind mag niet vóór start liggen).
_KIKV_DATE_ORDER = {"verzuim": [("startmoment", "eindmoment")]}


def profile_from_kikv(record_type: str) -> Optional[Profile]:
    """Bouw een veld-niveau profiel uit KIKV_REFERENCE (required_cols, datumvelden,
    overeenkomsttype-codelijst)."""
    schema = KIKV_REFERENCE.get(record_type)
    if not schema:
        return None
    required_cols = set(schema.get("required_cols", []))
    concepts = list(schema.get("col_aliases", {}).keys())
    allowed_types = schema.get("allowed_types", [])
    required, optional, codelists = {}, {}, {}
    for concept in concepts:
        if "datum" in concept.lower():
            check = "date"
        elif concept == "overeenkomsttype" and allowed_types:
            check = "codelist"
            codelists[concept] = allowed_types
        else:
            check = "text"
        (required if concept in required_cols else optional)[concept] = check
    unique = _KIKV_UNIQUE.get(record_type, [])
    unique = [c for c in unique if c in required or c in optional]
    all_concepts = set(required) | set(optional)
    date_orders = [(a, b) for (a, b) in _KIKV_DATE_ORDER.get(record_type, [])
                   if a in all_concepts and b in all_concepts]
    return Profile(record_type=record_type, required=required, optional=optional,
                   codelists=codelists, unique=unique, date_orders=date_orders)


def _column_for(cf, concept: str) -> Optional[str]:
    """Bronkolom bij een concept: via field_concepts, val terug op identiteit."""
    for col, con in (cf.field_concepts or {}).items():
        if con == concept:
            return col
    if concept in set(cf.fields):
        return concept
    return None


def run_profile(cf, profile: Profile) -> list[Finding]:
    """Pas een profiel toe op een canoniek bestand; geef uniforme bevindingen.

    - Ontbrekend verplicht concept -> Finding(check='missing', severity='error').
    - Aanwezig veld -> generieke formaatcheck; ernst 'error' als verplicht, anders
      'warning'. Identiek aan het huidige Algemeen-gedrag (pariteit).
    """
    findings: list[Finding] = []
    present = set(cf.fields)

    # 1. Beschikbaarheid: verplichte concepten aanwezig?
    for concept in profile.required:
        col = _column_for(cf, concept)
        if col is None or col not in present:
            findings.append(Finding(
                concept=concept, check="missing", severity="error",
                message=f"Verplicht veld '{concept}' ontbreekt in de export.",
                count=len(cf.rows),
            ))

    # 2. Kwaliteit: formaatcheck op aanwezige velden.
    for concept, check in profile.all_fields.items():
        col = _column_for(cf, concept)
        if col is None or col not in present:
            continue
        severity = "error" if concept in profile.required else "warning"
        allowed = profile.codelists.get(concept)
        f = run_column(column_values(cf, col), concept, check, severity=severity, allowed=allowed)
        if f:
            findings.append(f)

    # 3. Uniciteit (relationele regel, bv. KIK-V dup_id).
    for concept in profile.unique:
        col = _column_for(cf, concept)
        if col is None or col not in present:
            continue
        f = run_unique(column_values(cf, col), concept, severity="error")
        if f:
            findings.append(f)

    # 4. Cross-field datumvolgorde (bv. KIK-V verzuim: eindmoment >= startmoment).
    for start_c, end_c in profile.date_orders:
        sc = _column_for(cf, start_c)
        ec = _column_for(cf, end_c)
        if sc is None or ec is None or sc not in present or ec not in present:
            continue
        starts = [(row.cells[sc].value if sc in row.cells else None) for row in cf.rows]
        ends = [(row.cells[ec].value if ec in row.cells else None) for row in cf.rows]
        f = run_date_order(starts, ends, end_c, severity="error")
        if f:
            findings.append(f)

    return findings
