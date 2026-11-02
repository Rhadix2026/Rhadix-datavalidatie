"""
test_readiness_ingetrokken.py — B-19(a): ingetrokken indicatoren buiten de score.

Twee grondslagen, bewust gescheiden:

  1. titelmarkering — het profiel markeert de indicator zelf als vervallen
     (NZa Basisinformatie 10.1: titel "10.1. Vervallen").
  2. register       — de intrekking is buiten het profiel aangetoond en staat
     expliciet vastgelegd (Zorgkantoren 13.4, versieverschil 1.3.4 -> 1.3.5).

De scherpste eis staat onderaan: het ontbreken van een SPARQL-bestand is op
zichzelf GEEN bewijs van intrekking. Zo'n indicator blijft meetellen en wordt
als aandachtspunt gemeld. Dat is de scheidslijn tussen B-19(a) en B-19(b), en
die moet blijven liggen waar hij ligt.
"""
import pytest

from app.services.readiness_analyzer import (
    INGETROKKEN_REGISTER,
    analyze_readiness,
)

# Een minimale scan: niets geüpload, dus alles wat telt komt op blocked uit.
SCAN: dict = {"file_results": []}


def _ind(ind_id, titel, *, met_query=True, klassen=None):
    """Bouwt één indicator zoals de importer die oplevert."""
    files = {"markdown": {"filename": f"Indicator {ind_id}.md", "content": ""}}
    if met_query:
        files["sparql"] = {"filename": f"Indicator {ind_id}.rq", "parsed": {}}
    return {
        "id": ind_id,
        "files": files,
        "metadata": {"title": titel, "rdf_classes": klassen or ["onz-pers:Medewerker"],
                     "predicates": ["onz-g:hasQuality"]},
    }


def _profiel(naam, versie, indicatoren):
    return {"name": naam, "version": versie, "ref": versie,
            "indicators": {i["id"]: i for i in indicatoren}}


# ── grondslag 1: titelmarkering ─────────────────────────────────────────────

@pytest.mark.parametrize("titel", [
    "10.1. Vervallen",
    "3.2 vervallen per 2026",
    "7.1 Ingetrokken",
    "8.1 Deprecated",
    "9.1 Withdrawn",
])
def test_titelmarkering_sluit_uit(titel):
    p = _profiel("Willekeurig profiel", "1.0.0", [_ind("10.1", titel), _ind("1.1", "1.1 Gewoon")])
    m = analyze_readiness(p, SCAN)
    assert m["total_indicators"] == 1
    assert "10.1" not in m["indicator_results"]
    assert "1.1" in m["indicator_results"]
    uit = m["retired_indicators"]
    assert [x["id"] for x in uit] == ["10.1"]
    assert uit[0]["basis"] == "titelmarkering"
    assert uit[0]["reason"] and uit[0]["evidence"]


def test_titel_zonder_markering_telt_mee():
    """'Vervallenverklaring' mag niet aanslaan — het patroon staat op woordgrenzen."""
    p = _profiel("P", "1.0.0", [_ind("1.1", "1.1 Beleid rond vervallenverklaring van contracten")])
    m = analyze_readiness(p, SCAN)
    assert m["total_indicators"] == 1
    assert m["retired_indicators"] == []


# ── grondslag 2: register ───────────────────────────────────────────────────

ZK_NAAM = "Uitwisselprofiel Zorgkantoren Inkoopondersteuning en beleidsontwikkeling"


def test_register_sluit_zorgkantoren_13_4_uit_in_1_3_5():
    p = _profiel(ZK_NAAM, "1.3.5", [
        _ind("13.4", "13.4 Hoeveel personeel stroomt door naar een aflopend kwalificatieniveau?",
             met_query=False),
        _ind("13.1", "13.1 Iets anders"),
    ])
    m = analyze_readiness(p, SCAN)
    assert m["total_indicators"] == 1
    assert "13.4" not in m["indicator_results"]
    uit = m["retired_indicators"]
    assert [x["id"] for x in uit] == ["13.4"]
    assert uit[0]["basis"] == "register"
    assert "1.3.5" in uit[0]["reason"]
    assert "c064e4d68ec1" in uit[0]["evidence"]
    # staat niet óók als aandachtspunt gemeld
    assert [x["id"] for x in m["missing_query_indicators"]] == []


def test_register_geldt_niet_voor_een_andere_versie():
    """1.3.4 had de query nog; het register mag daar niet op aanslaan."""
    p = _profiel(ZK_NAAM, "1.3.4", [_ind("13.4", "13.4 Doorstroom", met_query=True)])
    m = analyze_readiness(p, SCAN)
    assert m["total_indicators"] == 1
    assert m["retired_indicators"] == []


def test_register_geldt_niet_voor_een_ander_profiel():
    p = _profiel("Uitwisselprofiel ActiZ Belangenbehartiging", "1.3.5",
                 [_ind("13.4", "13.4 Toevallig hetzelfde nummer")])
    m = analyze_readiness(p, SCAN)
    assert m["total_indicators"] == 1
    assert m["retired_indicators"] == []


def test_register_is_navolgbaar():
    """Elke regel moet herleidbaar zijn: profiel, versie, reden en bron."""
    assert INGETROKKEN_REGISTER, "register mag niet leeg zijn zolang 13.4 wordt uitgesloten"
    for regel in INGETROKKEN_REGISTER:
        assert regel["profile_name"] and regel["indicator_id"]
        assert regel["versions"] and all(isinstance(v, str) for v in regel["versions"])
        assert len(regel["reason"]) > 20
        assert len(regel["evidence"]) > 20


# ── de scheidslijn: geen query is geen bewijs ───────────────────────────────

def test_ontbrekende_query_zonder_grondslag_telt_mee_en_wordt_gemeld():
    """De kern van voorwaarde 4: niet stilzwijgend uitsluiten."""
    p = _profiel("Onbekend profiel", "9.9.9", [
        _ind("5.1", "5.1 Een gewone vraag", met_query=False),
        _ind("5.2", "5.2 Nog een vraag"),
    ])
    m = analyze_readiness(p, SCAN)
    assert m["total_indicators"] == 2            # 5.1 telt mee
    assert "5.1" in m["indicator_results"]
    assert m["retired_indicators"] == []
    aandacht = m["missing_query_indicators"]
    assert [x["id"] for x in aandacht] == ["5.1"]
    assert aandacht[0]["title"].startswith("5.1")
    assert "intrekking" in aandacht[0]["note"]


def test_indicator_met_query_komt_niet_in_het_aandachtspunt():
    p = _profiel("P", "1.0.0", [_ind("1.1", "1.1 Met query")])
    m = analyze_readiness(p, SCAN)
    assert m["missing_query_indicators"] == []


# ── ingetrokken is niet 'blocked' ──────────────────────────────────────────

def test_ingetrokken_wordt_niet_als_geblokkeerd_gepresenteerd():
    p = _profiel("P", "1.0.0", [_ind("1.1", "1.1 Vervallen"), _ind("1.2", "1.2 Gewoon")])
    m = analyze_readiness(p, SCAN)
    assert m["blocked"] == 1                     # alleen 1.2
    assert m["fully_computable"] + m["partially_computable"] + m["blocked"] == m["total_indicators"]
    assert all(x["readiness"] != "retired" for x in m["indicator_results"].values())


def test_alles_ingetrokken_geeft_geen_deling_door_nul():
    p = _profiel("P", "1.0.0", [_ind("1.1", "1.1 Vervallen")])
    m = analyze_readiness(p, SCAN)
    assert m["total_indicators"] == 0
    assert m["profile_readiness_score"] == 0.0
    assert len(m["retired_indicators"]) == 1


# ── de indexsleutel blijft overgeslagen ────────────────────────────────────

def test_indexsleutel_komt_nergens_terecht():
    p = _profiel("P", "1.0.0", [_ind("1.1", "1.1 Gewoon")])
    p["indicators"]["-INDEX"] = {"id": "-INDEX", "files": {"markdown": {}}, "metadata": {"title": None}}
    m = analyze_readiness(p, SCAN)
    assert m["total_indicators"] == 1
    assert [x["id"] for x in m["retired_indicators"]] == []
    assert [x["id"] for x in m["missing_query_indicators"]] == []
