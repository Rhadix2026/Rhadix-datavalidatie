"""
readiness_scoring.py — De rekenregels van de Readiness Checks, serverzijdig.

Dit is de serverzijdige tegenhanger van de rekenlogica die in de browser op
rhoderlanden.rhadix.nl draait. De regels zijn **niet opnieuw bedacht**: ze zijn
één op één overgenomen uit de vastgestelde baseline `baseline-2026-09-21`, en
`test_readiness_pariteit.py` bewijst uitputtend dat beide implementaties voor
elke mogelijke uitkomst hetzelfde antwoord geven.

De regels
---------
* Vijf dimensies van elk drie vragen, samen vijftien vragen.
* Per antwoord 3, 2, 1 of 0 punten (zie `INHOUD["answers"]`).
* Dimensiescore = som van de drie antwoorden ÷ 9 × 100, afgerond.
* Totaalscore  = gemiddelde van de vijf **afgeronde** dimensiescores, afgerond.
* Rangschikking = oplopend op score; bij gelijke score wint de laagste
  dimensie-index, zodat de volgorde van het scherm wordt aangehouden.

Afronding
---------
JavaScript rondt met `Math.round`, dat een half punt **naar boven** afrondt.
Python's ingebouwde `round()` rondt een half punt naar het even getal
(bankiersafronding). Bij de waarden die hier voorkomen doet dat verschil zich
niet voor — een dimensiescore is altijd n ÷ 9 × 100 en een totaalscore altijd
een vijfvoud-gemiddelde, geen van beide levert ooit exact een half punt op —
maar we nemen het gedrag van de browser hier bewust letterlijk over in
`_rond()`, zodat de pariteit niet van die toevalligheid afhangt.

Vertrouwensgrens
----------------
De browser stuurt **uitsluitend de vijftien antwoorden** mee. Totaalscore,
dimensiescores en aandachtspunten worden hier opnieuw berekend; een door de
client meegestuurde score wordt nooit overgenomen. Zie `readiness.py`.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from app.services.readiness_content import INHOUD

AANTAL_DIMENSIES = 5
VRAGEN_PER_DIMENSIE = 3
AANTAL_VRAGEN = AANTAL_DIMENSIES * VRAGEN_PER_DIMENSIE
MAX_PUNTEN_PER_DIMENSIE = VRAGEN_PER_DIMENSIE * 3   # 9

GELDIGE_CHECKS = tuple(INHOUD["checks"].keys())     # ("data", "kikv")


def _rond(waarde: float) -> int:
    """Afronden zoals JavaScript's Math.round: een half punt gaat naar boven."""
    return math.floor(waarde + 0.5)


@dataclass
class DimensieScore:
    index: int
    naam: str
    score: int                       # 0-100
    punten: list[int]                # de drie ruwe antwoorden, in vraagvolgorde
    definitie: dict = field(repr=False)   # het dimensieblok uit INHOUD

    @property
    def band(self) -> int:
        return band(self.score)


@dataclass
class Uitslag:
    check: str
    titel: str
    totaal: int                      # 0-100
    categorie: str
    duiding: str
    dimensies: list[DimensieScore]   # in schermvolgorde
    gerangschikt: list[DimensieScore]  # oplopend op score
    antwoorden: list[int]

    @property
    def band(self) -> int:
        return band(self.totaal)

    @property
    def aandachtspunten(self) -> list[DimensieScore]:
        """De twee laagst scorende dimensies — hetzelfde tweetal dat het
        scherm als preview toont."""
        return self.gerangschikt[:2]


def band(score: int) -> int:
    """Bandindeling 0-3, exact zoals de browser: <=39, <=59, <=79, anders."""
    if score <= 39:
        return 0
    if score <= 59:
        return 1
    if score <= 79:
        return 2
    return 3


def categorie(score: int, check: str) -> str:
    """Categorienaam bij een score. De bovenste band heeft in `cats` geen
    eigen naam en erft `top` van de check ("Datagereed" / "KIK-V-gereed")."""
    naam = INHOUD["cats"][band(score)][2]
    return naam or INHOUD["checks"][check]["top"]


def controleer_antwoorden(check: str, antwoorden: list[int]) -> None:
    """Werpt ValueError bij een onbekende check of ongeldige antwoordreeks."""
    if check not in GELDIGE_CHECKS:
        raise ValueError(f"Onbekende check: {check!r}")
    if len(antwoorden) != AANTAL_VRAGEN:
        raise ValueError(f"Verwacht {AANTAL_VRAGEN} antwoorden, kreeg {len(antwoorden)}")
    toegestaan = {punten for _, punten in INHOUD["answers"]}
    for i, a in enumerate(antwoorden):
        if a not in toegestaan:
            raise ValueError(f"Antwoord {i + 1} is {a!r}; toegestaan zijn {sorted(toegestaan)}")


def bereken(check: str, antwoorden: list[int]) -> Uitslag:
    """Bereken de volledige uitslag uit de vijftien afzonderlijke antwoorden."""
    controleer_antwoorden(check, antwoorden)
    blok = INHOUD["checks"][check]

    dimensies: list[DimensieScore] = []
    for di, dim in enumerate(blok["dims"]):
        punten = antwoorden[di * VRAGEN_PER_DIMENSIE:(di + 1) * VRAGEN_PER_DIMENSIE]
        score = _rond(sum(punten) / MAX_PUNTEN_PER_DIMENSIE * 100)
        dimensies.append(DimensieScore(index=di, naam=dim["name"], score=score,
                                       punten=list(punten), definitie=dim))

    totaal = _rond(sum(d.score for d in dimensies) / AANTAL_DIMENSIES)
    gerangschikt = sorted(dimensies, key=lambda d: (d.score, d.index))

    return Uitslag(
        check=check,
        titel=blok["title"],
        totaal=totaal,
        categorie=categorie(totaal, check),
        duiding=blok["meaning"][band(totaal)],
        dimensies=dimensies,
        gerangschikt=gerangschikt,
        antwoorden=list(antwoorden),
    )


# ── Afgeleide teksten, gelijk aan wat het scherm toont ────────────────────────

BANDWOORD = [
    "Uw antwoorden wijzen erop dat de basis hier nog niet op orde is.",
    "Uw antwoorden wijzen op eerste stappen die nog niet structureel zijn.",
    "Uw antwoorden wijzen erop dat dit grotendeels op orde is.",
    "Uw antwoorden wijzen erop dat dit sterk is ingericht.",
]


def interpretatie(dim: DimensieScore) -> str:
    """Duiding van één dimensie — zelfde samenstelling als `interp()` in de browser."""
    b = dim.band
    return BANDWOORD[b] + " " + (dim.definitie["high"] if b >= 2 else dim.definitie["low"])


def is_sterk_punt(dim: DimensieScore) -> bool:
    """Een dimensie telt als sterk punt bij score >= 67 én alle drie de
    antwoorden minimaal 'Grotendeels geregeld'. Zelfde drempel als het scherm."""
    return dim.score >= 67 and all(p >= 2 for p in dim.punten)


def antwoordlabel(punten: int) -> str:
    """Het label dat bij een aantal punten hoort, bijvoorbeeld 3 → 'Aantoonbaar geregeld'."""
    for label, waarde in INHOUD["answers"]:
        if waarde == punten:
            return label
    raise ValueError(f"Geen label voor {punten!r}")


def antwoordlabel_voor_vraag(check: str, vraag_index: int, punten: int) -> str:
    """Als bovenstaande, maar houdt rekening met een extra antwoordmogelijkheid
    bij een specifieke vraag. Bij KIK-V, dimensie 5, vraag 1 bestaat naast
    'Nee / onbekend' ook 'Weet ik niet'; beide leveren 0 punten op.

    Die twee zijn achteraf niet uit elkaar te houden — de browser stuurt alleen
    het puntenaantal mee. We tonen daarom bij 0 punten op zo'n vraag beide
    mogelijkheden, zodat de antwoordenbijlage niets suggereert wat niet vaststaat.
    """
    di, qi = divmod(vraag_index, VRAGEN_PER_DIMENSIE)
    extra = INHOUD["checks"][check]["dims"][di].get("extra")
    basis = antwoordlabel(punten)
    if extra and extra["idx"] == qi and punten == 0:
        return f"{basis} / {extra['label']}"
    return basis
