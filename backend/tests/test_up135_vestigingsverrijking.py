"""
Regressietest op de keten

    happy-flow -> fictieve vestigingsverrijking A/B -> triples
        -> ONGEWIJZIGDE UP 1.3.5-query -> resultaten A / B / organisatie

De test legt de uitkomsten vast die in de rekenhandleiding als voorbeeld staan.
Wijzigt de happy-flow set, de verrijking of de opbouw naar triples, dan valt deze
test om en moet het voorbeeld in de handleiding worden herzien.

Bewust GEEN assertie op de exacte percentagewaarde van 3.1: die kolom komt op
rdflib leeg terug omdat de expressie twee aliassen uit dezelfde SELECT hergebruikt
(reviewpunt R-12 in de handleiding). De test legt dat gedrag juist vást, zodat een
toekomstige wijziging — in de bron of in de store — opvalt.
"""
from __future__ import annotations

import importlib.util
import pathlib

import pytest

FIXTURE = pathlib.Path(__file__).resolve().parent / "fixtures" / "up135_vestigingsverrijking"

rdflib = pytest.importorskip("rdflib", reason="rdflib is nodig om de UP-query uit te voeren")

_spec = importlib.util.spec_from_file_location("bouw_graaf", FIXTURE / "bouw_graaf.py")
bouw_graaf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bouw_graaf)

ORG = "Organisatie (gecontracteerd + algemeen)"
PEIL = "2026-01-01"


def _rijen(nummer: str, met_vestigingen: bool = True) -> dict[str, tuple]:
    g = bouw_graaf.bouw(met_vestigingen=met_vestigingen)
    q = bouw_graaf.query_135(nummer, peildatum=PEIL)
    uit = {}
    for rij in g.query(q):
        waarden = tuple(None if v is None else str(v) for v in rij)
        uit[waarden[0]] = waarden[1:]
    return uit


# ── De verrijking zelf ────────────────────────────────────────────────────────

def test_verrijking_verdeelt_de_bronrecords_60_40():
    """De 60/40-verdeling zit in de bronrecords, niet in de einduitkomst."""
    rijen = bouw_graaf._lees_verrijking()
    assert len(rijen) == 40
    a = sum(1 for r in rijen.values() if r["vestiging"] == "Vestiging A")
    b = sum(1 for r in rijen.values() if r["vestiging"] == "Vestiging B")
    assert (a, b) == (24, 16)          # 60% / 40% van 40 overeenkomsten
    assert a + b == 40                 # elke overeenkomst is toegewezen


def test_zonder_verrijking_alleen_de_organisatieregel():
    """Zonder vestigingsgegevens levert de query uitsluitend de organisatietak."""
    rijen = _rijen("3.1", met_vestigingen=False)
    assert set(rijen) == {ORG}


# ── Indicator 3.1: gewone tellingen en een percentage ─────────────────────────

def test_31_drie_regels_en_optelbare_tellingen():
    rijen = _rijen("3.1")
    assert set(rijen) == {ORG, "Vestiging A", "Vestiging B"}

    bep_a, tot_a = int(rijen["Vestiging A"][0]), int(rijen["Vestiging A"][1])
    bep_b, tot_b = int(rijen["Vestiging B"][0]), int(rijen["Vestiging B"][1])
    bep_o, tot_o = int(rijen[ORG][0]), int(rijen[ORG][1])

    # Gewone tellingen: A + B is hier gelijk aan het organisatietotaal, omdat
    # elke overeenkomst aan een vestiging is toegewezen.
    assert bep_a + bep_b == bep_o
    assert tot_a + tot_b == tot_o
    assert (bep_o, tot_o) == (5, 28)


def test_31_organisatiepercentage_is_geen_gemiddelde_van_a_en_b():
    """Teller en noemer worden op organisatieniveau opnieuw bepaald."""
    rijen = _rijen("3.1")
    bep_a, tot_a = int(rijen["Vestiging A"][0]), int(rijen["Vestiging A"][1])
    bep_b, tot_b = int(rijen["Vestiging B"][0]), int(rijen["Vestiging B"][1])
    bep_o, tot_o = int(rijen[ORG][0]), int(rijen[ORG][1])

    pct = lambda t, n: round(100 * t / n, 2) if n else None
    pct_a, pct_b, pct_o = pct(bep_a, tot_a), pct(bep_b, tot_b), pct(bep_o, tot_o)

    # Het organisatiepercentage volgt uit de opnieuw gesommeerde teller en noemer
    # en is niet het ongewogen gemiddelde van A en B.
    assert pct_o == pct(bep_a + bep_b, tot_a + tot_b)
    ongewogen = round((pct_a + pct_b) / 2, 2)
    assert pct_o != ongewogen, "voorbeeld verliest zijn didactische waarde als deze gelijk zijn"


def test_31_percentagekolom_blijft_leeg_reviewpunt_r12():
    """Vastgelegd gedrag: de aliasverwijzing levert op rdflib een lege kolom."""
    rijen = _rijen("3.1")
    assert rijen[ORG][2] is None


# ── Indicator 1.2: unieke tellingen ──────────────────────────────────────────

def test_12_unieke_tellingen_en_de_grens_van_deze_testset():
    rijen = _rijen("1.2")
    assert set(rijen) == {ORG, "Vestiging A", "Vestiging B"}

    tot_a = int(rijen["Vestiging A"][2])
    tot_b = int(rijen["Vestiging B"][2])
    tot_o = int(rijen[ORG][2])

    # In deze set heeft elke persoon precies één overeenkomst bij één vestiging.
    # Daardoor valt A + B hier samen met het organisatietotaal. Een persoon die
    # bij twee vestigingen werkt zou per vestiging één keer tellen en voor de
    # organisatie óók één keer, waardoor A + B hoger uitvalt. Deze testset kan
    # dat niet aantonen; dat is in de handleiding als beperking vermeld.
    assert tot_a + tot_b == tot_o
    assert tot_o == 28

    # Niet-zorg is 0 omdat alle functies in de set type "Zorg" hebben.
    assert int(rijen[ORG][1]) == 0
    assert int(rijen[ORG][0]) == 28
