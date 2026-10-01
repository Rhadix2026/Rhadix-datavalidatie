"""
bouw_graaf.py — happy-flow + fictieve vestigingsverrijking -> RDF-graaf.

Keten die hiermee reproduceerbaar wordt:

    happy-flow CSV -> gecontroleerde verrijking A/B -> triples
        -> ONGEWIJZIGDE UP 1.3.5-query -> resultaten A / B / organisatie

De module wijzigt geen enkele query. Zij bouwt alleen de triples die de
query's verwachten, uit twee bronnen die strikt gescheiden blijven:

  * frontend/public/kikv-voorbeeldset/   — de bestaande happy-flow testset
  * vestigingsverrijking.csv            — FICTIEF, alleen voor het rekenvoorbeeld

Welke triples uit welke bron komen, is terug te zien in `herkomst()`.
"""
from __future__ import annotations

import csv
import pathlib

from rdflib import Graph, Literal, Namespace, RDF, URIRef
from rdflib.namespace import XSD

ONZ_G = Namespace("http://purl.org/ozo/onz-g#")
ONZ_ORG = Namespace("http://purl.org/ozo/onz-org#")
ONZ_PERS = Namespace("http://purl.org/ozo/onz-pers#")
HF = Namespace("http://rhadix.nl/happyflow#")
PC = Namespace("http://rhadix.nl/postcode/")

HIER = pathlib.Path(__file__).resolve().parent
# backend/tests/fixtures/up135_vestigingsverrijking -> repo-wortel
WORTEL = HIER.parents[3]
HAPPY = WORTEL / "frontend" / "public" / "kikv-voorbeeldset"
VERRIJKING = HIER / "vestigingsverrijking.csv"


def _iso(nl: str) -> str | None:
    """dd-mm-jjjj -> jjjj-mm-dd. Leeg blijft leeg (open einddatum)."""
    nl = (nl or "").strip()
    if not nl:
        return None
    dag, maand, jaar = nl.split("-")
    return f"{jaar}-{maand}-{dag}"


def _lees(naam: str) -> list[dict]:
    with open(HAPPY / naam, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _lees_verrijking() -> dict[str, dict]:
    """De verrijkingstabel, met commentaarregels (#) overgeslagen."""
    with open(VERRIJKING, newline="", encoding="utf-8") as f:
        regels = [r for r in f if not r.lstrip().startswith("#")]
    return {r["DienstverbandNummer"]: r for r in csv.DictReader(regels)}


def herkomst() -> dict[str, str]:
    """Documenteert per triple-groep waar de gegevens vandaan komen."""
    return {
        "overeenkomst (type, periode)": "happy-flow: werkovereenkomst_afas_hrm.csv",
        "persoon": "happy-flow: werkovereenkomst_afas_hrm.csv (PersoneelsNummer)",
        "functie en zorgverlener-functie": "happy-flow: medewerker_afas_hrm.csv + functie_ons.csv",
        "locatie, vestiging, vestigingsnummer": "FICTIEF: vestigingsverrijking.csv",
        "postcode, postcodegebied, zorgkantoorregio, zorgkantoor": "FICTIEF: vestigingsverrijking.csv",
    }


def bouw(met_vestigingen: bool = True) -> Graph:
    """Bouwt de graaf. Zonder verrijking blijft alleen de organisatietak over."""
    g = Graph()
    g.bind("onz-g", ONZ_G)
    g.bind("onz-org", ONZ_ORG)
    g.bind("onz-pers", ONZ_PERS)

    # ── Functieregister: FunctionDesc -> is het een zorgverlener-functie? ──
    functietype = {r["FunctionDesc"]: r["FunctionType"] for r in _lees("functie_ons.csv")}
    for naam, soort in functietype.items():
        fu = HF[f"functie_{naam.replace(' ', '_')}"]
        g.add((fu, RDF.type, ONZ_G.OccupationalPositionRole))
        if soort.strip().lower() == "zorg":
            g.add((fu, RDF.type, ONZ_PERS.ZorgverlenerFunctie))

    medewerker = {r["PersoneelsNummer"]: r for r in _lees("medewerker_afas_hrm.csv")}
    verrijking = _lees_verrijking() if met_vestigingen else {}

    # ── Vestigingen, postcoderoute en zorgkantoor (uitsluitend fictief) ──
    zorgkantoor = HF["zorgkantoor_voorbeeld"]
    gezien_vestiging: set[str] = set()
    gezien_regio: set[str] = set()
    for rij in verrijking.values():
        vnum, pc6, regio = rij["vestigingsnummer"], rij["postcode6"], rij["zorgkantoorregio"]
        vest = HF[f"vestiging_{vnum}"]
        regio_uri = HF[f"regio_{regio}"]

        if regio not in gezien_regio:
            g.add((regio_uri, RDF.type, ONZ_ORG.ZorgkantoorRegio))
            g.add((zorgkantoor, ONZ_G.hasOperatingRange, regio_uri))
            gezien_regio.add(regio)

        if vnum in gezien_vestiging:
            continue
        gezien_vestiging.add(vnum)

        g.add((vest, RDF.type, ONZ_ORG.Vestiging))

        # vestigingsnummer, zoals de query het uitleest
        vnr = HF[f"vestnr_{vnum}"]
        g.add((vest, ONZ_G.identifiedBy, vnr))
        g.add((vnr, RDF.type, ONZ_ORG.Vestigingsnummer))
        g.add((vnr, ONZ_G.hasDataValue, Literal(rij["vestiging"])))

        # De route die de query aflegt om bij de zescijferige postcode te komen:
        #   vestiging -hasLocalizableArea-> gebied -identifiedBy-> adres
        #            -hasPart-> adresdeel -hasPart-> postcode6
        gebied = HF[f"gebied_{vnum}"]
        adres = HF[f"adres_{vnum}"]
        adresdeel = HF[f"adresdeel_{vnum}"]
        g.add((vest, ONZ_G.hasLocalizableArea, gebied))
        g.add((gebied, ONZ_G.identifiedBy, adres))
        g.add((adres, ONZ_G.hasPart, adresdeel))
        g.add((adresdeel, ONZ_G.hasPart, PC[pc6]))

        # De query knipt de laatste twee tekens van de postcode-IRI af en zoekt
        # daarmee het postcodegebied op; dat gebied is deel van de regio.
        pc4 = URIRef(str(PC[pc6])[:-2])
        pc_gebied = HF[f"pcgebied_{pc6[:4]}"]
        g.add((pc_gebied, ONZ_G.identifiedBy, pc4))
        g.add((pc_gebied, ONZ_G.partOf, regio_uri))

    # ── Overeenkomsten, afspraken, personen, functies en locaties ──
    for r in _lees("werkovereenkomst_afas_hrm.csv"):
        dvn, pn = r["DienstverbandNummer"], r["PersoneelsNummer"]
        ov = HF[f"ov{dvn}"]
        afspraak = HF[f"afs{dvn}"]
        persoon = HF[f"persoon{pn}"]

        soort = r["OvereenkomstType"].strip().lower()
        g.add((ov, RDF.type, ONZ_PERS.ArbeidsOvereenkomst))
        g.add((ov, RDF.type, ONZ_PERS.ArbeidsOvereenkomstBepaaldeTijd if soort == "bepaalde tijd"
               else ONZ_PERS.ArbeidsOvereenkomstOnbepaaldeTijd))
        g.add((ov, ONZ_PERS.heeftOpdrachtnemer, persoon))
        g.add((ov, ONZ_G.hasPart, afspraak))

        g.add((afspraak, RDF.type, ONZ_PERS.WerkOvereenkomstAfspraak))
        g.add((afspraak, ONZ_G.startDatum, Literal(_iso(r["StartDatum"]), datatype=XSD.date)))
        eind = _iso(r["EindDatum"])
        if eind:
            g.add((afspraak, ONZ_G.eindDatum, Literal(eind, datatype=XSD.date)))

        functienaam = (medewerker.get(pn) or {}).get("Functie", "")
        if functienaam in functietype:
            g.add((afspraak, ONZ_G.isAbout, HF[f"functie_{functienaam.replace(' ', '_')}"]))

        rij = verrijking.get(dvn)
        if rij:
            # locatie is een eigen onverplaatsbaar artefact binnen de vestiging;
            # de query loopt er met partOf* naartoe.
            locatie = HF[f"locatie_{dvn}"]
            g.add((afspraak, ONZ_G.isAbout, locatie))
            g.add((locatie, RDF.type, ONZ_G.StationaryArtifact))
            g.add((locatie, ONZ_G.partOf, HF[f"vestiging_{rij['vestigingsnummer']}"]))

    return g


def query_135(nummer: str, peildatum: str = "2026-01-01", bron: pathlib.Path | None = None) -> str:
    """Leest de ongewijzigde 1.3.5-query en activeert alleen de peildatum-BIND."""
    bron = bron or (HIER / "queries" / f"{nummer}.rq")
    q = bron.read_text(encoding="utf-8")
    # De bron levert de peildatum-BIND uitgecommentarieerd; activeren is de
    # enige toegestane wijziging. De query zelf blijft ongemoeid.
    uit = []
    for regel in q.split("\n"):
        kaal = regel.strip()
        if kaal.startswith("#") and "AS ?peildatum" in kaal:
            voor = regel[: len(regel) - len(regel.lstrip())]
            uit.append(f'{voor}BIND("{peildatum}"^^xsd:date AS ?peildatum)')
        else:
            uit.append(regel)
    return "\n".join(uit)
