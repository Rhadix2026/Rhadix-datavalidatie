"""
score_accounting.py — verantwoording bij een score (B-22, richting 1).

Dit raakt **geen enkele scoreformule**. Het legt alleen vast hoe een score tot
stand kwam, zodat een gebruiker kan zien wat er wél en niet in verwerkt is.

De drie validatieroutes gebruiken onvergelijkbare definities van "score":

    kikv      score = max(0, 100 - (fouten * 5 + waarschuwingen * 2))
              foutgestuurd, ernst weegt mee, straf is absoluut
    zib       score = rhadix-index, gemiddeld over bestanden
    algemeen  quality = geslaagde waardecontroles / totaal
              rhadix_index = completeness * quality / 100
              het aantal bevindingen weegt hier NIET mee

Daarom vullen alle drie dezelfde omslag, met per route andere inhoud. Eén
gegevenscontract, één weergavecomponent, geen nieuw cijfer.

**Controles en bevindingen zijn niet hetzelfde getal.** Eén bevinding bundelt
meerdere afgekeurde controles: vijf rijen met een ongeldige BSN geven één
bevinding met `count: 5` en vijf afgekeurde controles. En een ontbrekend
verplicht veld geeft één bevinding terwijl er op dat veld nul controles zijn
uitgevoerd. De twee mogen daarom nooit naast elkaar als vergelijkbare aantallen
worden gepresenteerd.
"""
from __future__ import annotations

from typing import Any, Optional

# Verandert alleen wanneer een scoreformule wijzigt, niet bij elke release.
SCORE_VERSION = "2026.10"

FORMULES = {
    "kikv":     "score = max(0, 100 - (fouten x 5 + waarschuwingen x 2))",
    "zib":      "score = rhadix-index, gemiddeld over de bestanden",
    "algemeen": "quality = geslaagde waardecontroles / uitgevoerde waardecontroles; "
                "rhadix_index = completeness x quality / 100",
}


def score_version(path: str) -> dict[str, str]:
    """Versie, route en formule horen bij elkaar: zonder de route zegt een
    versienummer niets, want de drie routes rekenen verschillend."""
    return {
        "version": SCORE_VERSION,
        "path":    path,
        "formula": FORMULES.get(path, "onbekend"),
    }


def _telling(issues: list[dict], in_score: bool) -> dict[str, Any]:
    uitgekozen = [i for i in issues if bool(i.get("in_score")) is in_score]
    per_type: dict[str, int] = {}
    for i in uitgekozen:
        per_type[i.get("type") or "onbekend"] = per_type.get(i.get("type") or "onbekend", 0) + 1
    return {
        "errors":   sum(1 for i in uitgekozen if i.get("severity") == "error"),
        "warnings": sum(1 for i in uitgekozen if i.get("severity") == "warning"),
        "by_type":  per_type,
    }


def toelichting(score_label: str, score_waarde: Any, buiten: int) -> str:
    """Neutraal en feitelijk. Geen bewering dat een score van 100 betekent dat
    de gegevens foutloos zijn — dat is precies de indruk die B-22 blootlegde."""
    basis = f"{score_label} {score_waarde} volgens berekening {SCORE_VERSION}."
    if buiten <= 0:
        return f"{basis} Alle vastgestelde bevindingen zijn in deze score verwerkt."
    if buiten == 1:
        return f"{basis} Daarnaast is 1 bevinding vastgesteld die niet in deze score is verwerkt."
    return (f"{basis} Daarnaast zijn {buiten} bevindingen vastgesteld "
            "die niet in deze score zijn verwerkt.")


def bouw(
    *,
    path: str,
    issues: list[dict],
    score_label: str,
    score_waarde: Any,
    checks_executed: Optional[int] = None,
    checks_passed: Optional[int] = None,
    skipped: Optional[dict[str, int]] = None,
) -> dict[str, Any]:
    """Bouwt de verantwoording. `checks_*` mag None zijn voor routes die geen
    waardecontroles tellen maar bevindingen afstraffen (kikv, zib); de sleutels
    blijven dan aanwezig met None, zodat het contract uniform is.
    """
    in_score  = _telling(issues, True)
    buiten    = _telling(issues, False)
    aantal_buiten = buiten["errors"] + buiten["warnings"]
    checks_failed = (
        None if (checks_executed is None or checks_passed is None)
        else max(0, checks_executed - checks_passed)
    )
    return {
        # Uitgevoerde controles — NIET te verwarren met het aantal bevindingen.
        "checks": {
            "executed": checks_executed,
            "passed":   checks_passed,
            "failed":   checks_failed,
            "skipped":  skipped or {},
            "note":     "Eén bevinding kan meerdere afgekeurde controles bundelen; een "
                        "ontbrekend veld geeft een bevinding zonder uitgevoerde controles. "
                        "Controles en bevindingen zijn daarom geen vergelijkbare aantallen.",
        },
        # Vastgestelde bevindingen, gesplitst naar wat de score heeft geraakt.
        "findings": {
            "in_score":      in_score,
            "outside_score": buiten,
        },
        "score_covers_all_findings": aantal_buiten == 0,
        "explanation": toelichting(score_label, score_waarde, aantal_buiten),
    }
