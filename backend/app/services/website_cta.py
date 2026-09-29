"""
website_cta.py — Van een knop op de website naar kanaal, interesse en status.

De site heeft drie tot vier oproepen per pagina die allemaal op dezelfde
contactpagina uitkomen. Zonder parameter is niet te zien wélke knop iemand
aanklikte, en dan is elk contact "iemand heeft het formulier ingevuld".

De knoppen geven daarom twee dingen mee:

    contact.html?van=<pagina>&cta=<oproep>

`van` is de pagina waar iemand vandaan kwam en bepaalt de **interesse**;
`cta` is de knop zelf en bepaalt het **kanaal** en de **status**.

Waarom die twee gescheiden zijn: dezelfde knop kan op meerdere pagina's staan
("Plan een kennismaking" staat in de kop van elke pagina), en dezelfde pagina
heeft meerdere knoppen. Kruis je ze, dan krijg je een tabel van veertig regels
die niemand meer bijhoudt.

Onbekende waarden zijn geen fout. Iemand die de contactpagina rechtstreeks
opent of een oude link volgt, levert gewoon `Contactformulier / Algemeen /
Nieuw` op — dat is waar, en beter dan raden.
"""
from __future__ import annotations

# ── Kanaal en status per knop ─────────────────────────────────────────────────
# Status "Lead" alleen bij een blijk van commerciële of vervolginteresse. Wie
# het algemene contactformulier invult is "Nieuw": kwalificeren is mensenwerk,
# geen formulier.
CTA = {
    "kennismaking":     ("Kennismaking",      "Lead"),
    "pilot":            ("Pilotaanvraag",     "Lead"),
    "dienst":           ("Kennismaking",      "Lead"),
    "ontwikkelpartner": ("Ontwikkelpartner",  "Lead"),
    "uitslag":          ("Kennismaking",      "Lead"),
    "contact":          ("Contactformulier",  "Nieuw"),
}
STANDAARD_KANAAL = "Contactformulier"
STANDAARD_STATUS = "Nieuw"

# ── Interesse per pagina ──────────────────────────────────────────────────────
PAGINA = {
    "datagereedheidsscan":     "Datagereedheidsscan",
    "implementatiegereedheid": "Implementatiegereedheid",
    "dataregie-realisatie":    "Dataregie en realisatie",
    "ai-gereedheid":           "AI-gereedheid",
    "rhadix":                  "Rhadix",
    "data-readiness":          "Readiness Check",
    "readiness-check":         "Readiness Check",
}
STANDAARD_INTERESSE = "Algemeen"

# De Data Readiness Check zelf is geen knop maar een eigen ingang.
KANAAL_READINESS = "Data Readiness Check"
INTERESSE_READINESS = "Readiness Check"
# Wie alleen een rapport opvraagt heeft nog geen vervolginteresse getoond.
STATUS_READINESS = "Nieuw"

BASIS_URL = "https://rhoderlandengroep.nl/"


def _schoon(waarde: str | None) -> str:
    """Alleen kleine letters, cijfers en koppeltekens; de rest telt niet mee."""
    tekst = (waarde or "").strip().lower()
    return "".join(t for t in tekst if t.isalnum() or t == "-")[:64]


def duiding(van: str | None, cta: str | None) -> tuple[str, str, str, str]:
    """Geeft (kanaal, interesse, status, bronpagina) voor een formulierinzending."""
    pagina = _schoon(van)
    knop = _schoon(cta)
    kanaal, status = CTA.get(knop, (STANDAARD_KANAAL, STANDAARD_STATUS))
    interesse = PAGINA.get(pagina, STANDAARD_INTERESSE)
    return kanaal, interesse, status, pagina


def bron_url(bronpagina: str | None) -> str:
    """De volledige URL van de pagina waar iemand vandaan kwam."""
    pagina = _schoon(bronpagina)
    if not pagina or pagina in ("index", "home"):
        return BASIS_URL
    return f"{BASIS_URL}{pagina}.html"


def campagne_kort(campagne: dict | None) -> str:
    """Bron, medium en campagne op één regel: linkedin/cpc/najaar-2026.

    Compact genoeg om in een kolom te tonen en te filteren. De volledige set
    blijft daarnaast leesbaar in de omschrijving van de activiteit.
    """
    if not campagne:
        return ""
    delen = [str(campagne.get(s) or "").strip()
             for s in ("utm_source", "utm_medium", "utm_campaign")]
    while delen and not delen[-1]:
        delen.pop()
    return "/".join(d or "–" for d in delen)[:255]
