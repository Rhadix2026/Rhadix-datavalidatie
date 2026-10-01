"""
bouw_graaf.py — happy-flow + fictieve vestigingsverrijking -> RDF-graaf.

Keten die hiermee reproduceerbaar wordt:

    happy-flow CSV -> gecontroleerde verrijking A/B -> triples
        -> ONGEWIJZIGDE UP 1.3.5-query -> resultaten A / B / organisatie

De module wijzigt geen enkele query. Zij bouwt alleen de triples die de query's
verwachten, uit twee bronnen die strikt gescheiden blijven:

  * frontend/public/kikv-voorbeeldset/   — de bestaande happy-flow testset
  * vestigingsverrijking.csv            — FICTIEF, alleen voor het rekenvoorbeeld

Welke triples uit welke bron komen staat in `herkomst()`.

GRENS: er wordt niets gemodelleerd wat de happy-flow set niet bevat. Ontbreken
gegevens — urenregistratie, kwalificatieniveau, leveringsvorm, capaciteit,
diagnose, grootboekrubrieken — dan blijven die triples weg en levert de
betreffende query geen rijen. Dat is het bedoelde gedrag: het hiaat moet zichtbaar
blijven, niet worden opgevuld.
"""
from __future__ import annotations

import csv
import pathlib
import re

from rdflib import Graph, Literal, Namespace, RDF, URIRef
from rdflib.namespace import XSD

ONZ_G = Namespace("http://purl.org/ozo/onz-g#")
ONZ_ORG = Namespace("http://purl.org/ozo/onz-org#")
ONZ_PERS = Namespace("http://purl.org/ozo/onz-pers#")
ONZ_ZORG = Namespace("http://purl.org/ozo/onz-zorg#")
HF = Namespace("http://rhadix.nl/happyflow#")
PC = Namespace("http://rhadix.nl/postcode/")

HIER = pathlib.Path(__file__).resolve().parent
WORTEL = HIER.parents[3]
HAPPY = WORTEL / "frontend" / "public" / "kikv-voorbeeldset"
VERRIJKING = HIER / "vestigingsverrijking.csv"

# 1 fte = 36 uur per week, de omrekenfactor die Algemene uitgangspunten 1.0.5 noemt.
FTE_UREN = 36


def _iso(nl: str) -> str | None:
    """dd-mm-jjjj -> jjjj-mm-dd. Leeg blijft leeg (open einddatum)."""
    nl = (nl or "").strip()
    if not nl:
        return None
    if "T" in nl:                      # ONS levert soms een tijdstempel
        nl = nl.split("T")[0]
    if nl.count("-") == 2 and len(nl.split("-")[0]) == 4:
        return nl                      # al ISO
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
    """Per triple-groep: waar komen de gegevens vandaan?"""
    return {
        "overeenkomst (type, periode)": "happy-flow: werkovereenkomst_afas_hrm.csv",
        "persoon en geboortedatum": "happy-flow: medewerker_afas_hrm.csv",
        "functie en zorgverlener-functie": "happy-flow: medewerker_afas_hrm.csv + functie_ons.csv",
        "contractomvang en eenheid": "happy-flow: werkovereenkomst_afas_hrm.csv (Contractomvang, als fte)",
        "ziekteperiode": "happy-flow: verzuim_afas_hrm.csv",
        "cliënt, Wlz-indicatie en zorgprofiel": "happy-flow: client_ons.csv",
        "locatie, vestiging, vestigingsnummer": "FICTIEF: vestigingsverrijking.csv",
        "postcode, postcodegebied, zorgkantoorregio, zorgkantoor": "FICTIEF: vestigingsverrijking.csv",
    }


def ontbreekt() -> dict[str, str]:
    """Wat bewust NIET wordt gemodelleerd, omdat de happy-flow het niet bevat."""
    return {
        "GewerktePeriode en gewerkte uren": "geen urenregistratie in de set (raakt 2.1, 6.1, 7.1, 8.1)",
        "VerloondePeriode": "geen verloningsgegevens (raakt 2.2)",
        "ODBKwalificatieWaarde": "geen kwalificatieniveau (raakt 6.1, 13.3, 13.4)",
        "ZwangerschapsVerlof": "SoortVerzuim kent alleen ziekte en ongeval (raakt 11.2, 11.4, 12.2)",
        "Leveringsvorm": "geen leveringsvorm bij de cliënten (raakt 14.2, 14.3)",
        "WoonEenheid en capaciteit": "geen capaciteitsgegevens (raakt 15.1, 15.2, 15.3)",
        "diagnose / zorgproceskenmerk": "geen diagnosegegevens (raakt 16.1)",
        "Grootboekrubriek, Grootboekpost, EindSaldo":
            "rubrieken zijn plaatshouders zonder RGS/Prismant en zonder peildatumsaldo (raakt 8.2 en 18 t/m 24)",
        "Inhuur-, uitzend-, oproep-, vrijwilligers- en BBL-overeenkomst":
            "OvereenkomstType kent alleen bepaalde en onbepaalde tijd (raakt 9.1, 10.1)",
    }


def _vestigingsketen(g: Graph, verrijking: dict[str, dict]) -> None:
    """De fictieve vestigingen, de postcoderoute en het zorgkantoor."""
    zorgkantoor = HF["zorgkantoor_voorbeeld"]
    gezien_vestiging: set[str] = set()
    gezien_regio: set[str] = set()
    for rij in verrijking.values():
        vnum, pc6, regio = rij["vestigingsnummer"], rij["postcode6"], rij["zorgkantoorregio"]
        vest, regio_uri = HF[f"vestiging_{vnum}"], HF[f"regio_{regio}"]

        if regio not in gezien_regio:
            g.add((regio_uri, RDF.type, ONZ_ORG.ZorgkantoorRegio))
            g.add((zorgkantoor, ONZ_G.hasOperatingRange, regio_uri))
            gezien_regio.add(regio)

        if vnum in gezien_vestiging:
            continue
        gezien_vestiging.add(vnum)

        g.add((vest, RDF.type, ONZ_ORG.Vestiging))
        vnr = HF[f"vestnr_{vnum}"]
        g.add((vest, ONZ_G.identifiedBy, vnr))
        g.add((vnr, RDF.type, ONZ_ORG.Vestigingsnummer))
        g.add((vnr, ONZ_G.hasDataValue, Literal(rij["vestiging"])))

        # vestiging -hasLocalizableArea-> gebied -identifiedBy-> adres
        #          -hasPart-> adresdeel -hasPart-> postcode6
        gebied, adres, adresdeel = HF[f"gebied_{vnum}"], HF[f"adres_{vnum}"], HF[f"adresdeel_{vnum}"]
        g.add((vest, ONZ_G.hasLocalizableArea, gebied))
        g.add((gebied, ONZ_G.identifiedBy, adres))
        g.add((adres, ONZ_G.hasPart, adresdeel))
        g.add((adresdeel, ONZ_G.hasPart, PC[pc6]))

        # De query knipt de laatste twee tekens af en zoekt daarmee het gebied op.
        pc4 = URIRef(str(PC[pc6])[:-2])
        pc_gebied = HF[f"pcgebied_{pc6[:4]}"]
        g.add((pc_gebied, ONZ_G.identifiedBy, pc4))
        g.add((pc_gebied, ONZ_G.partOf, regio_uri))


def bouw(met_vestigingen: bool = True) -> Graph:
    """Bouwt de graaf. Zonder verrijking blijft alleen de organisatietak over."""
    g = Graph()
    for pre, ns in [("onz-g", ONZ_G), ("onz-org", ONZ_ORG), ("onz-pers", ONZ_PERS), ("onz-zorg", ONZ_ZORG)]:
        g.bind(pre, ns)

    functietype = {r["FunctionDesc"]: r["FunctionType"] for r in _lees("functie_ons.csv")}
    for naam, soort in functietype.items():
        fu = HF[f"functie_{naam.replace(' ', '_')}"]
        g.add((fu, RDF.type, ONZ_G.OccupationalPositionRole))
        if soort.strip().lower() == "zorg":
            g.add((fu, RDF.type, ONZ_PERS.ZorgverlenerFunctie))

    medewerker = {r["PersoneelsNummer"]: r for r in _lees("medewerker_afas_hrm.csv")}
    verrijking = _lees_verrijking() if met_vestigingen else {}
    if verrijking:
        _vestigingsketen(g, verrijking)

    # ── De eenheid fte, met de omrekenfactor die de query uitleest ──
    eenheid_fte = HF["eenheid_fte"]
    g.add((eenheid_fte, ONZ_G.hasDataValue, Literal(FTE_UREN)))

    overeenkomst_van_persoon: dict[str, URIRef] = {}
    for r in _lees("werkovereenkomst_afas_hrm.csv"):
        dvn, pn = r["DienstverbandNummer"], r["PersoneelsNummer"]
        ov, afspraak, persoon = HF[f"ov{dvn}"], HF[f"afs{dvn}"], HF[f"persoon{pn}"]
        overeenkomst_van_persoon[pn] = ov

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

        # persoon als mens, met geboortedatum
        mw = medewerker.get(pn) or {}
        g.add((persoon, RDF.type, ONZ_G.Human))
        geb = _iso(mw.get("Geboortedatum", ""))
        if geb:
            g.add((persoon, ONZ_G.hasDateOfBirth, Literal(geb, datatype=XSD.date)))

        # functie
        functienaam = mw.get("Functie", "")
        if functienaam in functietype:
            g.add((afspraak, ONZ_G.isAbout, HF[f"functie_{functienaam.replace(' ', '_')}"]))

        # contractomvang: afspraak -hasPart-> omvang -isAbout-> waarde
        omvang = r.get("Contractomvang", "").strip()
        if omvang:
            co, cow = HF[f"omvang{dvn}"], HF[f"omvangwaarde{dvn}"]
            g.add((afspraak, ONZ_G.hasPart, co))
            g.add((co, RDF.type, ONZ_PERS.ContractOmvang))
            g.add((co, ONZ_G.isAbout, cow))
            g.add((cow, RDF.type, ONZ_PERS.ContractOmvangWaarde))
            g.add((cow, ONZ_G.hasDataValue, Literal(float(omvang))))
            g.add((cow, ONZ_G.hasUnitOfMeasure, eenheid_fte))

        # locatie binnen de fictieve vestiging
        rij = verrijking.get(dvn)
        if rij:
            locatie = HF[f"locatie_{dvn}"]
            g.add((afspraak, ONZ_G.isAbout, locatie))
            g.add((locatie, RDF.type, ONZ_G.StationaryArtifact))
            g.add((locatie, ONZ_G.partOf, HF[f"vestiging_{rij['vestigingsnummer']}"]))

    # ── Ziekteperiodes, gekoppeld aan de overeenkomst van de persoon ──
    for i, r in enumerate(_lees("verzuim_afas_hrm.csv"), 1):
        pn = r["PersoneelsNummer"]
        ov = overeenkomst_van_persoon.get(pn)
        if not ov:
            continue
        zp = HF[f"ziekteperiode{i}"]
        g.add((zp, RDF.type, ONZ_PERS.ZiektePeriode))
        g.add((zp, ONZ_G.definedBy, ov))
        g.add((zp, ONZ_G.startDatum, Literal(_iso(r["Startmoment"]), datatype=XSD.date)))
        eind = _iso(r.get("Eindmoment", ""))
        if eind:
            g.add((zp, ONZ_G.eindDatum, Literal(eind, datatype=XSD.date)))

    # ── Cliënten: zorgproces, Wlz-indicatie en zorgprofiel ──
    # client_ons.csv levert wlzProfiel als VV4, VG3 enzovoort; de ontologie kent
    # 4VV, 5VV, ... De omzetting draait de notatie om; profielen buiten de
    # VV-reeks blijven staan zoals ze zijn en vallen door de VALUES-lijst van de
    # query automatisch af.
    for i, r in enumerate(_lees("client_ons.csv"), 1):
        prof = (r.get("wlzProfiel") or "").strip()
        if not prof:
            continue
        omgedraaid = f"{prof[2:]}{prof[:2]}" if prof[:2].isalpha() and prof[2:].isdigit() else prof
        client, zorgproces, indicatie = HF[f"client{i}"], HF[f"zorgproces{i}"], HF[f"indicatie{i}"]
        start, eind = _iso(r.get("startDate", "")), _iso(r.get("endDate", ""))
        if not start:
            continue
        g.add((client, RDF.type, ONZ_G.Human))
        g.add((zorgproces, RDF.type, ONZ_ZORG.NursingProcess))
        g.add((zorgproces, ONZ_G.definedBy, indicatie))
        g.add((zorgproces, ONZ_G.startDatum, Literal(start, datatype=XSD.date)))
        g.add((indicatie, RDF.type, ONZ_ZORG.WlzIndicatie))
        g.add((indicatie, ONZ_G.hasPart, ONZ_ZORG[omgedraaid]))
        g.add((indicatie, ONZ_G.isAbout, client))
        g.add((indicatie, ONZ_G.startDatum, Literal(start, datatype=XSD.date)))
        if eind:
            g.add((zorgproces, ONZ_G.eindDatum, Literal(eind, datatype=XSD.date)))
            g.add((indicatie, ONZ_G.eindDatum, Literal(eind, datatype=XSD.date)))
        # Cliënten over A en B verdeeld volgens dezelfde 60/40-sleutel.
        if verrijking:
            vnum = "000011112222" if i <= 36 else "000033334444"
            locatie = HF[f"clientlocatie{i}"]
            g.add((zorgproces, ONZ_G.hasPerdurantLocation, locatie))
            g.add((locatie, RDF.type, ONZ_G.StationaryArtifact))
            g.add((locatie, ONZ_G.partOf, HF[f"vestiging_{vnum}"]))

    return g


# ── Query's uitvoeren zonder ze te wijzigen ──────────────────────────────────
PARAMETERS = {
    "peildatum": '"{peildatum}"^^xsd:date',
    "jaar": "{jaar}",
    "kwartaal": '"{kwartaal}"',
    "startperiode": '"{startperiode}"^^xsd:date',
    "eindperiode": '"{eindperiode}"^^xsd:date',
}
STANDAARD = dict(peildatum="2026-01-01", jaar=2026, kwartaal="Q1",
                 startperiode="2025-01-01", eindperiode="2025-12-31")


def query_135(nummer: str, **waarden) -> str:
    """Leest de ongewijzigde query en activeert uitsluitend de parameter-BINDs.

    Een BIND op ?zorgkantoor wordt NIET geactiveerd: de query's verwijzen daar naar
    onz-org:ZorgkantoorMenzis, een instantie die in deze testset niet bestaat. De
    variabele blijft dus ongebonden en bindt aan het fictieve zorgkantoor uit de
    verrijking. Dat is de enige manier om de vestigingstak te laten lopen zonder de
    query te veranderen.
    """
    w = {**STANDAARD, **waarden}
    q = (HIER / "queries" / f"{nummer}.rq").read_text(encoding="utf-8")
    uit = []
    for regel in q.split("\n"):
        kaal = regel.strip().lstrip("#").strip()
        marge = regel[: len(regel) - len(regel.lstrip())]
        geraakt = False
        # De bron schrijft de BIND soms als "BIND(" en soms als "BIND (" met spatie,
        # en de parameternaam staat niet altijd direct voor de sluitende haak.
        if regel.strip().startswith("#") and re.match(r"BIND\s*\(", kaal):
            for naam, vorm in PARAMETERS.items():
                if re.search(rf"AS\s+\?{naam}\s*\)\s*$", kaal):
                    uit.append(f"{marge}BIND({vorm.format(**w)} AS ?{naam})")
                    geraakt = True
                    break
        if not geraakt:
            uit.append(regel)
    return "\n".join(uit)


def voer_uit(nummer: str, graaf: Graph | None = None, **waarden) -> list[tuple]:
    """Resultaatrijen van één indicator, als tuples van tekst (None blijft None)."""
    g = graaf if graaf is not None else bouw()
    return [tuple(None if v is None else str(v) for v in rij)
            for rij in g.query(query_135(nummer, **waarden))]
