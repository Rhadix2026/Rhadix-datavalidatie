"""
test_readiness_rapport.py — De opbouw van het indicatieve Readiness-rapport.

Toetst dat het rapport dezelfde drempels en teksten aanhoudt als de weergave op
het scherm, en dat de twee toevoegingen — managementsamenvatting en
antwoordenbijlage — kloppen met de gegeven antwoorden.
"""
import pytest

from app.services.readiness_content import INHOUD
from app.services.readiness_pdf import bouw_pdf
from app.services.readiness_rapport import TITEL, bouw
from app.services.readiness_scoring import bereken

GEMENGD = [2, 1, 0, 3, 3, 3, 1, 1, 1, 2, 2, 2, 0, 0, 3]


def maak(check="data", antwoorden=None, naam="Jan de Vries", organisatie="Zorggroep Voorbeeld"):
    return bouw(bereken(check, antwoorden or GEMENGD), naam=naam, organisatie=organisatie)


# ── Titel en voorbehoud ───────────────────────────────────────────────────────

def test_rapport_heet_indicatief():
    r = maak()
    assert r.titel == TITEL == "Indicatief Readiness-rapport op basis van uw antwoorden"
    assert "indicatief" in r.voorbehoud.lower()
    assert "geen audit" in r.voorbehoud.lower()
    assert "vervangt geen onderzoek" in r.voorbehoud.lower()


@pytest.mark.parametrize("check, verwacht", [
    ("data", "Datagereedheidsscan"),
    ("kikv", "KIK-V-ondersteuning"),
])
def test_vervolgstap_wijst_naar_de_juiste_dienst(check, verwacht):
    assert verwacht in maak(check).vervolg


# ── Managementsamenvatting ────────────────────────────────────────────────────

def test_samenvatting_noemt_score_categorie_en_de_twee_zwakste():
    r = maak()
    u = bereken("data", GEMENGD)
    assert "53 van 100" in r.samenvatting
    assert '"In ontwikkeling"' in r.samenvatting
    for d in u.aandachtspunten:
        assert d.naam in r.samenvatting
    assert u.aandachtspunten[0].definitie["advice"] in r.samenvatting


def test_samenvatting_noemt_sterke_punten_als_die_er_zijn():
    r = maak(antwoorden=[3] * 15)
    assert "fundament" in r.samenvatting
    for naam, _ in r.dimensies:
        assert naam in r.samenvatting


def test_samenvatting_is_eerlijk_als_er_geen_sterke_punten_zijn():
    r = maak(antwoorden=[0] * 15)
    assert "geen van de vijf dimensies" in r.samenvatting.lower()
    assert r.geen_sterke_punten is not None
    assert r.sterke_punten == []


# ── Sterke punten ─────────────────────────────────────────────────────────────

def test_sterke_punten_gebruiken_dezelfde_drempel_als_het_scherm():
    #  dimensie 1 op 2-2-2 (67, alle antwoorden >= 2) is sterk;
    #  dimensie 2 op 3-3-1 (78, maar één antwoord onder 2) is dat niet.
    antwoorden = [2, 2, 2] + [3, 3, 1] + [0] * 9
    r = maak(antwoorden=antwoorden)
    namen = [naam for naam, _ in r.sterke_punten]
    assert namen == [INHOUD["checks"]["data"]["dims"][0]["name"]]


def test_alles_maximaal_maakt_alle_vijf_sterk():
    r = maak(antwoorden=[3] * 15)
    assert len(r.sterke_punten) == 5
    assert r.geen_sterke_punten is None


# ── Analyse per dimensie ──────────────────────────────────────────────────────

def test_blokken_staan_oplopend_op_score():
    r = maak()
    scores = [b.score for b in r.blokken]
    assert scores == sorted(scores)
    assert r.blokken[0].prioriteit == "Hoogste prioriteit"
    assert r.blokken[1].prioriteit == "Tweede prioriteit"


def test_hoog_scorende_dimensie_krijgt_vasthouden():
    r = maak(antwoorden=[0] * 12 + [3, 3, 3])
    hoog = [b for b in r.blokken if b.score == 100]
    assert hoog and hoog[0].prioriteit == "Vasthouden"


def test_aandachtspunten_volgen_de_afzonderlijke_antwoorden():
    """Alleen vragen met 0 of 1 punt leveren een aandachtspunt op."""
    #  dimensie 1: vraag 1 = 3, vraag 2 = 1, vraag 3 = 0
    r = maak(antwoorden=[3, 1, 0] + [3] * 12)
    blok = next(b for b in r.blokken if b.naam == INHOUD["checks"]["data"]["dims"][0]["name"])
    findings = INHOUD["checks"]["data"]["dims"][0]["findings"]
    assert blok.aandachtspunten == [findings[1], findings[2]]
    assert blok.wat_al_staat == [INHOUD["checks"]["data"]["dims"][0]["strengths"][0]]
    assert blok.deels_geregeld == []


def test_deels_geregeld_toont_vraag_en_gegeven_antwoord():
    """Herleidbaar naar de invoer: niet alleen dát er twee punten zijn gegeven,
    maar welk antwoord dat was."""
    r = maak(antwoorden=[2, 0, 0] + [0] * 12)
    blok = next(b for b in r.blokken if b.naam == INHOUD["checks"]["data"]["dims"][0]["name"])
    vraag = INHOUD["checks"]["data"]["dims"][0]["q"][0]
    assert blok.deels_geregeld == [(vraag.rstrip("?"), "Ja, voor de meeste toepassingen bekend")]
    assert not blok.deels_geregeld[0][0].endswith("?")


def test_sterke_dimensie_herhaalt_wat_al_staat_niet():
    r = maak(antwoorden=[3, 3, 3] + [0] * 12)
    blok = next(b for b in r.blokken if b.score == 100)
    assert blok.wat_al_staat == [], "dat staat al onder Sterke punten"


def test_elke_dimensie_heeft_een_verbeteractie():
    r = maak()
    for blok in r.blokken:
        assert blok.verbeteractie
        assert blok.interpretatie


# ── Prioritering ──────────────────────────────────────────────────────────────

def test_prioritering_kent_drie_groepen():
    r = maak()
    assert [kop for kop, _ in r.prioritering] == ["Eerst doen", "Daarna", "Verder ontwikkelen"]
    verdeeld = sum(len(regels) for _, regels in r.prioritering)
    assert verdeeld == 5, "elke dimensie komt precies één keer voor"


def test_prioritering_draagt_het_gegeven_antwoord_mee():
    r = maak()
    for _, regels in r.prioritering:
        for naam, score, tekst, antwoord in regels:
            assert antwoord, f"{naam} mist het gegeven antwoord"


def test_prioritering_leidt_geen_aantoonbaarheid_meer_af_uit_score_twee():
    r = maak(antwoorden=[2, 2, 2] + [0] * 12)
    teksten = [t for _, regels in r.prioritering for _, _, t, _ in regels]
    assert not any(t.startswith("Aantoonbaar maken") for t in teksten)


def test_alles_maximaal_zet_alles_in_verder_ontwikkelen():
    r = maak(antwoorden=[3] * 15)
    eerst, daarna, verder = r.prioritering
    assert eerst[1] == [] and daarna[1] == []
    assert len(verder[1]) == 5
    assert all("Vasthouden en benutten" in tekst for _, _, tekst, _ in verder[1])


def test_volgende_stap_bij_deels_geregeld():
    r = maak(antwoorden=[2, 2, 2] + [0] * 12)
    regels = [t for _, regels in r.prioritering for _, _, t, _ in regels]
    assert any(t.startswith("Volgende stap: ") for t in regels)


# ── Antwoordenbijlage ─────────────────────────────────────────────────────────

def test_bijlage_bevat_alle_vijftien_vragen():
    r = maak()
    assert len(r.bijlage) == 5
    assert sum(len(vragen) for _, vragen in r.bijlage) == 15


def test_bijlage_geeft_per_vraag_het_gegeven_antwoord():
    r = maak(antwoorden=[3, 2, 1] + [0] * 12)
    _, vragen = r.bijlage[0]
    assert [antwoord for _, antwoord in vragen] == [
        "Ja, volledig vastgelegd en actueel",
        "Voor de meeste gegevens is dit bekend",
        "Alleen met aanzienlijke handmatige bewerkingen"]


def test_bijlage_van_de_data_check_gebruikt_de_eigen_labels():
    r = maak(antwoorden=[0] * 15)
    alle = [antwoord for _, vragen in r.bijlage for _, antwoord in vragen]
    assert all(a.startswith("Nee") for a in alle)
    assert len(set(alle)) == 15, "elke vraag heeft haar eigen nulantwoord"


def test_bijlage_toont_weet_ik_niet_bij_de_kikv_datastationvraag():
    r = maak(check="kikv", antwoorden=[3] * 12 + [0, 0, 0])
    _, vragen = r.bijlage[4]
    assert vragen[0][1] == "Nee / onbekend / Weet ik niet"
    assert vragen[1][1] == "Nee / onbekend"


def test_bijlage_volgt_de_schermvolgorde():
    r = maak()
    assert [naam for naam, _ in r.bijlage] == [naam for naam, _ in r.dimensies]


# ── PDF ───────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("check", ["data", "kikv"])
def test_pdf_wordt_gebouwd(check):
    pdf = bouw_pdf(maak(check))
    assert pdf[:5] == b"%PDF-"
    assert len(pdf) > 5_000


@pytest.mark.parametrize("antwoorden", [[0] * 15, [3] * 15, GEMENGD, [2] * 15])
def test_pdf_lukt_bij_elke_uitslag(antwoorden):
    """Ook als er geen sterke punten of geen aandachtspunten zijn."""
    assert bouw_pdf(maak(antwoorden=antwoorden))[:5] == b"%PDF-"


def test_pdf_verdraagt_ampersand_in_organisatienaam():
    """De dimensienaam 'Standaardisatie & betekenis' en een ingevulde
    organisatienaam met & mogen de opmaak niet breken."""
    pdf = bouw_pdf(maak(organisatie="Zorg & Welzijn <Twente>"))
    assert pdf[:5] == b"%PDF-"
