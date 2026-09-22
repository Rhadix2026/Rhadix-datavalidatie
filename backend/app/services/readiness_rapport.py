"""
readiness_rapport.py — Bouwt het indicatieve Readiness-rapport op uit de uitslag.

Levert één neutrale structuur die zowel de PDF als de e-mail voedt, zodat beide
hetzelfde vertellen. Geen opmaak, geen HTML: alleen tekst en getallen.

De opbouw volgt de rapportweergave die de bezoeker op het scherm ziet — zelfde
drempels, zelfde teksten, zelfde volgorde — met twee toevoegingen die het
rapport meer waard maken dan het scherm:

* een **managementsamenvatting** die de uitslag in één alinea duidt;
* een **antwoordenbijlage** met per vraag het gegeven antwoord, zodat het
  rapport controleerbaar en intern bespreekbaar is.

Het rapport heet overal "Indicatief Readiness-rapport op basis van uw
antwoorden". Dat is geen slag om de arm maar een feitelijke afbakening: het
rust op een zelfbeoordeling en niet op onderzoek van de werkelijke data.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.services.readiness_content import INHOUD
from app.services.readiness_scoring import (
    VRAGEN_PER_DIMENSIE, Uitslag, antwoordlabel_voor_vraag, band, interpretatie,
    is_sterk_punt,
)

TITEL = "Indicatief Readiness-rapport op basis van uw antwoorden"

VOORBEHOUD = (
    "Dit is een indicatief rapport op basis van uw eigen antwoorden. Het geeft een "
    "eerste beeld en vervangt geen onderzoek naar de werkelijke situatie in uw data, "
    "systemen, processen en governance. Het is dus geen audit en geen nulmeting."
)

VERVOLG = {
    "data": (
        "De Datagereedheidsscan van Rhoderlanden Groep onderzoekt wél de werkelijke "
        "situatie: uw data, systemen, processen en governance. Daar waar dit rapport "
        "aanwijzingen geeft, levert die scan vaststellingen."
    ),
    "kikv": (
        "De KIK-V-ondersteuning van Rhoderlanden Groep gaat verder waar dit rapport "
        "ophoudt: onderzoek van uw werkelijke registraties, de mapping naar de "
        "KIK-V-definities en de technische uitwisseling."
    ),
}


@dataclass
class DimensieBlok:
    naam: str
    score: int
    prioriteit: str                  # "Hoogste prioriteit" | "Tweede prioriteit" | "Vasthouden" | ""
    interpretatie: str
    wat_al_staat: list[str] = field(default_factory=list)
    aandachtspunten: list[str] = field(default_factory=list)
    deels_geregeld: list[tuple[str, str]] = field(default_factory=list)   # (vraag, antwoord)
    verbeteractie: str = ""


@dataclass
class Rapport:
    titel: str
    check: str
    check_titel: str
    soort: str                       # "Data" | "KIK-V"
    naam: str
    organisatie: str
    totaal: int
    categorie: str
    duiding: str
    samenvatting: str
    dimensies: list[tuple[str, int]]          # (naam, score) in schermvolgorde
    sterke_punten: list[tuple[str, str]]      # (dimensie, tekst)
    geen_sterke_punten: str | None
    blokken: list[DimensieBlok]               # oplopend op score
    prioritering: list[tuple[str, list[tuple[str, int, str, str]]]]  # (dim, score, tekst, antwoord)
    bijlage: list[tuple[str, list[tuple[str, str]]]]   # (dimensie, [(vraag, antwoord)])
    voorbehoud: str
    vervolg: str


# ── Deelstukken ───────────────────────────────────────────────────────────────

GEEN_STERKE_PUNTEN = (
    "Geen enkele dimensie komt op basis van uw antwoorden als organisatiebreed sterk "
    "punt naar voren. Dat is geen diskwalificatie: het betekent dat de eerste winst zit "
    "in het aantoonbaar maken van wat al gedeeltelijk geregeld is. Positieve antwoorden "
    "binnen een dimensie vindt u terug onder \"Wat al staat\"."
)


def _samenvatting(u: Uitslag) -> str:
    """Een managementsamenvatting die uitsluitend uit de eigen antwoorden volgt."""
    sterk = [d for d in u.dimensies if is_sterk_punt(d)]
    zwak = u.aandachtspunten
    soort = INHOUD["checks"][u.check]["kind"]

    regels = [
        f"Uw {soort} Readiness Check komt uit op {u.totaal} van 100, wat valt in de "
        f"categorie \"{u.categorie}\". {u.duiding}"
    ]

    if sterk:
        namen = ", ".join(d.naam for d in sterk[:-1])
        laatste = sterk[-1].naam
        wie = f"{namen} en {laatste}" if namen else laatste
        regels.append(
            f"Op {'dit punt' if len(sterk) == 1 else 'deze punten'} staat het fundament: "
            f"{wie}. Die winst is vooral te behouden door hem aantoonbaar te houden."
        )
    else:
        regels.append(
            "Geen van de vijf dimensies komt organisatiebreed als sterk punt naar voren; "
            "de eerste winst zit in het aantoonbaar maken van wat al gedeeltelijk geregeld is."
        )

    regels.append(
        f"De meeste ruimte zit bij {zwak[0].naam} ({zwak[0].score}) en "
        f"{zwak[1].naam} ({zwak[1].score}). Begin daar: {zwak[0].definitie['advice']}"
    )
    return " ".join(regels)


def _antwoord(check: str, dim, vraag_nummer: int) -> str:
    """Het label dat de bezoeker bij deze vraag koos."""
    return antwoordlabel_voor_vraag(
        check, dim.index * VRAGEN_PER_DIMENSIE + vraag_nummer, dim.punten[vraag_nummer])


def _blok(check: str, dim, rang: int) -> DimensieBlok:
    d = dim.definitie
    sterk = is_sterk_punt(dim)
    prioriteit = (
        "Vasthouden" if band(dim.score) >= 3
        else "Hoogste prioriteit" if rang == 0
        else "Tweede prioriteit" if rang == 1
        else ""
    )
    return DimensieBlok(
        naam=dim.naam,
        score=dim.score,
        prioriteit=prioriteit,
        interpretatie=interpretatie(dim),
        # Bij een dimensie die al als sterk punt is genoemd, laten we "Wat al staat"
        # weg — dat zou hetzelfde twee keer zeggen. Zo doet het scherm het ook.
        wat_al_staat=[] if sterk else [d["strengths"][i] for i, p in enumerate(dim.punten) if p == 3],
        aandachtspunten=[d["findings"][i] for i, p in enumerate(dim.punten) if p <= 1],
        # Vraag én gegeven antwoord, zodat het rapport herleidbaar blijft naar
        # wat de bezoeker werkelijk heeft aangeklikt. Sinds de antwoorden per
        # vraag verschillen, zegt "2 punten" op zichzelf niet meer genoeg.
        deels_geregeld=[(d["q"][i].rstrip("?"), _antwoord(check, dim, i))
                        for i, p in enumerate(dim.punten) if p == 2],
        verbeteractie=d["advice"],
    )


def _prioritering(u: Uitslag) -> list[tuple[str, list[tuple[str, int, str, str]]]]:
    """Drie groepen, zelfde verdeling en zelfde formulering als op het scherm.

    De tekst per dimensie volgt uit het zwakste antwoord binnen die dimensie.
    Bij twee punten luidde die vroeger "Aantoonbaar maken: …", maar dat leidde
    een betekenis af uit de score die er niet meer in zit: sinds elke vraag
    eigen antwoorden heeft, betekent twee punten niet overal hetzelfde. Het is
    nu "Volgende stap: …", met het werkelijk gegeven antwoord erbij.
    """
    laag = [d for d in u.gerangschikt if band(d.score) < 3]
    hoog = [d for d in u.gerangschikt if band(d.score) >= 3]
    groepen = [
        ("Eerst doen", laag[:2]),
        ("Daarna", laag[2:4]),
        ("Verder ontwikkelen", laag[4:] + hoog),
    ]

    uit = []
    for kop, dims in groepen:
        regels = []
        for d in dims:
            laagste = min(d.punten)
            i = d.punten.index(laagste)
            if laagste >= 3:
                tekst = "Vasthouden en benutten: " + d.definitie["high"]
            elif laagste == 2:
                s = d.definitie["strengths"][i]
                tekst = "Volgende stap: " + s[0].lower() + s[1:]
            else:
                tekst = d.definitie["findings"][i]
            regels.append((d.naam, d.score, tekst, _antwoord(u.check, d, i)))
        uit.append((kop, regels))
    return uit


def _bijlage(u: Uitslag) -> list[tuple[str, list[tuple[str, str]]]]:
    """Per dimensie de drie vragen met het gegeven antwoord."""
    uit = []
    for di, dim in enumerate(u.dimensies):
        vragen = []
        for qi, vraag in enumerate(dim.definitie["q"]):
            vragen.append((vraag, _antwoord(u.check, dim, qi)))
        uit.append((dim.naam, vragen))
    return uit


# ── Samenstellen ──────────────────────────────────────────────────────────────

def bouw(u: Uitslag, naam: str, organisatie: str) -> Rapport:
    sterke = [(d.naam, d.definitie["high"]) for d in u.dimensies if is_sterk_punt(d)]
    return Rapport(
        titel=TITEL,
        check=u.check,
        check_titel=u.titel,
        soort=INHOUD["checks"][u.check]["kind"],
        naam=naam,
        organisatie=organisatie,
        totaal=u.totaal,
        categorie=u.categorie,
        duiding=u.duiding,
        samenvatting=_samenvatting(u),
        dimensies=[(d.naam, d.score) for d in u.dimensies],
        sterke_punten=sterke,
        geen_sterke_punten=None if sterke else GEEN_STERKE_PUNTEN,
        blokken=[_blok(u.check, d, rang) for rang, d in enumerate(u.gerangschikt)],
        prioritering=_prioritering(u),
        bijlage=_bijlage(u),
        voorbehoud=VOORBEHOUD,
        vervolg=VERVOLG[u.check],
    )
