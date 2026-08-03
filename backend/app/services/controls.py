"""
controls.py - Generieke controles (doelarchitectuur Laag 2, Stap 2 - slice 2.1).

Herbruikbare checks die op het canonieke model (Laag 1) werken en één uniforme
bevinding opleveren. De checks hergebruiken de al gedeelde primitieven en de
bestaande formaatvalidators, zodat het gedrag identiek is aan de huidige paden
(pariteit per constructie). Eén implementatie i.p.v. drie.

SLICE 2.1: alleen het fundament (checks + Finding + kolomrunner). Nog geen
validator omgezet en niet aangesloten op de endpoints; dat gebeurt in latere
slices, met pariteitstests per recordtype.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence

# Hergebruik de bestaande formaatvalidators (bsn/date/email/postcode/number/
# gender/verzuimtype/...) - één bron van waarheid.
from app.services.algemeen_validator import VALIDATORS as _FORMAT_VALIDATORS
from app.services.dataquality import parse_date as _parse_date


@dataclass
class Finding:
    """Uniforme bevinding uit een generieke controle."""
    concept: str
    check: str                      # 'required' | 'date' | 'bsn' | 'email' | ...
    severity: str                   # 'error' | 'warning'
    message: str
    count: int = 0
    examples: list = field(default_factory=list)


def is_present(value) -> bool:
    """True als de waarde niet leeg is."""
    if value is None:
        return False
    return bool(str(value).strip())


def check_value(check: str, value, allowed=None) -> bool:
    """True als de waarde slaagt voor de generieke check.

    Lege waarden zijn 'niet van toepassing' voor formaatchecks (True); alleen
    'required' faalt op een lege waarde. Onbekende checks slagen (geen effect).
    """
    s = "" if value is None else str(value).strip()
    if check == "required":
        return bool(s)
    if not s:
        return True
    if check in ("codelist", "code"):
        if not allowed:
            return True
        return s.lower() in {str(a).strip().lower() for a in allowed}
    key = "number" if check == "numeric" else check
    validator = _FORMAT_VALIDATORS.get(key)
    if validator is None:
        return True
    return bool(validator(s))


def run_column(values: Sequence, concept: str, check: str,
               severity: str = "warning", allowed=None, max_examples: int = 50) -> Optional[Finding]:
    """Draai één check over de waarden van één kolom. Geef een Finding met het
    aantal fouten + voorbeelden, of None als alles slaagt."""
    total = 0
    passed = 0
    examples: list = []
    for idx, value in enumerate(values):
        s = "" if value is None else str(value).strip()
        if check != "required" and not s:
            continue
        total += 1
        if check_value(check, value, allowed=allowed):
            passed += 1
        elif len(examples) < max_examples:
            examples.append({"row": idx + 2, "value": s[:50]})
    fail = total - passed
    if fail <= 0:
        return None
    return Finding(
        concept=concept, check=check, severity=severity, count=fail,
        message=f"{fail} van {total} waarden voldoen niet aan '{check}'.",
        examples=examples,
    )


def column_values(cf, source_column: str) -> list:
    """Genormaliseerde waarden (cell.value) van één bronkolom uit een CanonicalFile."""
    return [row.cells[source_column].value
            for row in cf.rows if source_column in row.cells]


def run_unique(values: Sequence, concept: str, severity: str = "error",
               max_examples: int = 50) -> Optional[Finding]:
    """Signaleer dubbele (niet-lege) waarden in een kolom. `count` = het aantal
    rijen dat betrokken is bij een duplicaat, gelijk aan KIK-V's `dup_id`."""
    counts: dict = {}
    for v in values:
        s = "" if v is None else str(v).strip()
        if s:
            counts[s] = counts.get(s, 0) + 1
    dupes = {v for v, c in counts.items() if c > 1}
    if not dupes:
        return None
    involved = [v for v in values if (str(v).strip() if v is not None else "") in dupes]
    examples = [{"value": v} for v in list(dupes)[:max_examples]]
    return Finding(
        concept=concept, check="unique", severity=severity, count=len(involved),
        message=f"{len(dupes)} waarde(n) komen meerdere keren voor ({len(involved)} rijen).",
        examples=examples,
    )


def run_date_order(start_values, end_values, concept: str, severity: str = "error",
                   max_examples: int = 50) -> Optional[Finding]:
    """Cross-field: signaleer rijen waar de einddatum vóór de startdatum ligt.

    `start_values` en `end_values` zijn per rij uitgelijnd. Alleen rijen waar
    beide datums parsebaar zijn tellen mee - identiek aan KIK-V's bespoke
    `end_before_start` (verdict-pariteit)."""
    fail = 0
    examples: list = []
    for idx, (sv, ev) in enumerate(zip(start_values, end_values)):
        sd = _parse_date(sv)
        ed = _parse_date(ev)
        if sd and ed and ed < sd:
            fail += 1
            if len(examples) < max_examples:
                examples.append({"row": idx + 2, "start": str(sv), "end": str(ev)})
    if fail <= 0:
        return None
    return Finding(
        concept=concept, check="date_order", severity=severity, count=fail,
        message=f"{fail} rij(en) met einddatum vóór startdatum.",
        examples=examples,
    )


def run_conditional_required(trigger_values, target_values, trigger_set, concept: str,
                             severity: str = "error", max_examples: int = 50) -> Optional[Finding]:
    """Conditioneel verplicht: als het trigger-veld een waarde uit `trigger_set`
    heeft, moet het doelveld (`concept`) gevuld zijn. Per rij uitgelijnd.

    Verdict-pariteit met KIK-V's bespoke `missing_einddatum_temp` (einddatum
    verplicht bij een tijdelijk contracttype)."""
    norm = {str(t).strip().lower() for t in trigger_set}
    fail = 0
    examples: list = []
    for idx, (tv, gv) in enumerate(zip(trigger_values, target_values)):
        tvs = "" if tv is None else str(tv).strip().lower()
        gvs = "" if gv is None else str(gv).strip()
        if tvs in norm and not gvs:
            fail += 1
            if len(examples) < max_examples:
                examples.append({"row": idx + 2, "trigger": tvs})
    if fail <= 0:
        return None
    return Finding(
        concept=concept, check="conditional_required", severity=severity, count=fail,
        message=f"{fail} rij(en): '{concept}' is verplicht bij deze waarde.",
        examples=examples,
    )


def run_forbidden_value(values, concept: str, forbidden, severity: str = "error",
                        max_examples: int = 50) -> Optional[Finding]:
    """Signaleer verboden/placeholder-waarden (bv. KIK-V personeelsnummer '99999')."""
    fset = {str(x).strip() for x in forbidden}
    fail = 0
    examples: list = []
    for idx, v in enumerate(values):
        s = "" if v is None else str(v).strip()
        if s and s in fset:
            fail += 1
            if len(examples) < max_examples:
                examples.append({"row": idx + 2, "value": s})
    if fail <= 0:
        return None
    return Finding(
        concept=concept, check="forbidden", severity=severity, count=fail,
        message=f"{fail} rij(en) met een verboden/placeholder-waarde.",
        examples=examples,
    )


def run_range(values, concept: str, lo: float, hi: float, severity: str = "error",
              max_examples: int = 50) -> Optional[Finding]:
    """Signaleer niet-numerieke of buiten-bereik waarden (bv. verzuimpercentage 0-100).
    Lege waarden tellen niet mee - verdict-pariteit met KIK-V's `invalid_pct`."""
    fail = 0
    examples: list = []
    for idx, v in enumerate(values):
        s = "" if v is None else str(v).strip()
        if not s:
            continue
        try:
            x = float(s)
            ok = (lo <= x <= hi)
        except ValueError:
            ok = False
        if not ok:
            fail += 1
            if len(examples) < max_examples:
                examples.append({"row": idx + 2, "value": s[:50]})
    if fail <= 0:
        return None
    return Finding(
        concept=concept, check="range", severity=severity, count=fail,
        message=f"{fail} waarde(n) buiten bereik {lo}-{hi} of niet-numeriek.",
        examples=examples,
    )
