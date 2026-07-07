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
from app.services.controls import Finding, run_column, column_values


@dataclass
class Profile:
    """Declaratieve regelset voor één recordtype."""
    record_type: str
    required: dict = field(default_factory=dict)   # {concept: check}
    optional: dict = field(default_factory=dict)   # {concept: check}

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
        f = run_column(column_values(cf, col), concept, check, severity=severity)
        if f:
            findings.append(f)

    return findings
