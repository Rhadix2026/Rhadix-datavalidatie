"""
test_readiness_pariteit.py — Bewijst dat server en browser hetzelfde doen.

Twee soorten pariteit, allebei tegen de vastgestelde website-baseline
`baseline-2026-09-21`:

**Inhoud.** De regel `window.RG_READINESS = {...};` die de browser gebruikt,
wordt gegenereerd uit `readiness_content.INHOUD`. De test toont aan dat die
generatie **byte-identiek** is aan wat er vandaag in beide pagina's staat. Zo
staat vast dat het centraliseren van de inhoud niets aan de live checks
verandert.

**Scoring.** De rekenfuncties worden letterlijk uit de baseline geknipt en
onder Node uitgevoerd (zie `readiness_js_harnas.py`). Vervolgens worden beide
implementaties op dezelfde invoer vergeleken:

* **uitputtend** over alle 10^5 combinaties van dimensietotalen — dat is de
  volledige uitkomstruimte, want een dimensiescore hangt uitsluitend af van de
  som van haar drie antwoorden;
* **steekproefsgewijs** over volledige antwoordreeksen van vijftien vragen, met
  een vaste zaadwaarde zodat de test reproduceerbaar is.

Vergeleken worden totaalscore, de vijf dimensiescores, de categorie, de
rangschikking én de duidende tekst.

Zonder Node of zonder de website-baseline slaat de scoringspariteit over met
een expliciete melding. Buiten pytest is dit bestand ook rechtstreeks te
draaien:

    python tests/test_readiness_pariteit.py
"""
from __future__ import annotations

import itertools
import json
import pathlib
import random
import re
import sys
import tempfile

try:
    import pytest
except ModuleNotFoundError:                                # pragma: no cover
    # Buiten de testcontainer draait dit bestand ook zelfstandig; dan zijn de
    # markers niet nodig. Deze stub houdt de module importeerbaar.
    class _Stub:
        class mark:
            @staticmethod
            def skipif(*_a, **_k):
                return lambda f: f

            @staticmethod
            def parametrize(*_a, **_k):
                return lambda f: f

    pytest = _Stub()                                       # type: ignore[assignment]

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import readiness_js_harnas as harnas                      # noqa: E402
from app.scripts.genereer_readiness_config import (        # noqa: E402
    CONFIGBESTAND, PAGINAS, REGEL, configuratieregel,
)
from app.services import readiness_scoring as S            # noqa: E402
from app.services.readiness_content import INHOUD          # noqa: E402

beschikbaar, reden = harnas.beschikbaar()
vereist_baseline = pytest.mark.skipif(
    not harnas.baseline_pagina().exists(),
    reason=f"website-baseline niet gevonden op {harnas.baseline_pagina()}",
)
vereist_node = pytest.mark.skipif(not beschikbaar, reason=reden)


def _vector(dimensietotalen):
    """Vijftien antwoorden uit vijf dimensietotalen (elk 0 t/m 9)."""
    uit = []
    for totaal in dimensietotalen:
        basis, rest = divmod(totaal, 3)
        uit += [basis + (1 if i < rest else 0) for i in range(3)]
    return uit


def _python_uitslag(check: str, punten: list[int]) -> dict:
    u = S.bereken(check, punten)
    return {
        "totaal": u.totaal,
        "categorie": u.categorie,
        "dimensies": [d.score for d in u.dimensies],
        "rangschikking": [d.index for d in u.gerangschikt],
        "duiding": u.duiding,
    }


def _vergelijk(gevallen: list[dict]) -> int:
    """Draait de gevallen door browser én server en vergelijkt alles."""
    with tempfile.TemporaryDirectory() as tmp:
        js_uitslagen = harnas.draai(gevallen, pathlib.Path(tmp))

    assert len(js_uitslagen) == len(gevallen)
    afwijkingen = []
    for geval, js in zip(gevallen, js_uitslagen):
        py = _python_uitslag(geval["check"], geval["punten"])
        if py != js:
            afwijkingen.append((geval, js, py))
            if len(afwijkingen) >= 5:
                break
    assert not afwijkingen, "browser en server rekenen verschillend:\n" + "\n".join(
        f"  {g['check']} {g['punten']}\n    browser: {js}\n    server : {py}"
        for g, js, py in afwijkingen
    )
    return len(gevallen)


# ── Inhoudelijke pariteit ─────────────────────────────────────────────────────

@vereist_baseline
def test_gegenereerde_configuratie_is_identiek_aan_de_baseline():
    """De kern van het centraliseren: genereren verandert niets aan de site."""
    pad = harnas.sitemap() / CONFIGBESTAND
    treffer = REGEL.search(pad.read_text(encoding="utf-8"))
    assert treffer, f"{CONFIGBESTAND} bevat geen configuratieregel"
    assert treffer.group(0) == configuratieregel(), (
        f"De uit readiness_content.py gegenereerde configuratie wijkt af van {CONFIGBESTAND}."
    )


@vereist_baseline
@pytest.mark.parametrize("pagina", PAGINAS)
def test_checkpagina_laadt_de_configuratie(pagina):
    """Zonder dit script staat de wizard stil."""
    tekst = (harnas.sitemap() / pagina).read_text(encoding="utf-8")
    assert CONFIGBESTAND in tekst
    assert "assets/site.js" in tekst


@vereist_baseline
def test_baseline_bevat_de_verwachte_checks_en_vragen():
    """Vangt op dat de site stilletjes andere vragen zou gaan tonen."""
    ruwe = REGEL.search(
        (harnas.configbestand()).read_text(encoding="utf-8")
    ).group(1)
    uit_de_site = json.loads(ruwe)
    assert list(uit_de_site["checks"]) == ["data", "kikv"]
    for check in ("data", "kikv"):
        dims = uit_de_site["checks"][check]["dims"]
        assert len(dims) == 5
        assert sum(len(d["q"]) for d in dims) == 15


@vereist_baseline
@pytest.mark.parametrize("pagina, verwachte_check", [
    ("data-readiness.html", "data"),
    ("kik-v-readiness.html", "kikv"),
])
def test_pagina_kiest_de_juiste_check(pagina, verwachte_check):
    tekst = (harnas.sitemap() / pagina).read_text(encoding="utf-8")
    assert re.search(rf'class="wizard" data-check="{verwachte_check}"', tekst)


# ── Labelpariteit ─────────────────────────────────────────────────────────────

@vereist_node
def test_browser_en_rapport_tonen_dezelfde_antwoorden():
    """Wat de bezoeker aanklikt, is wat het rapport terugleest.

    Sinds de Data Readiness Check eigen antwoorden per vraag heeft, is dit geen
    vanzelfsprekendheid meer: de browser leest ze uit `qa`, het rapport uit
    dezelfde bron via `antwoordmogelijkheden()`. Deze test haalt de lijsten uit
    de échte browsercode en legt ze naast de serverzijde.
    """
    checks = ["data", "kikv"]
    with tempfile.TemporaryDirectory() as tmp:
        uit_de_browser = harnas.draai_antwoorden(checks, pathlib.Path(tmp))

    for check, per_vraag in zip(checks, uit_de_browser):
        assert len(per_vraag) == S.AANTAL_VRAGEN
        for i, browserlijst in enumerate(per_vraag):
            serverlijst = [list(x) for x in S.antwoordmogelijkheden(check, i)]
            assert browserlijst == serverlijst, (
                f"{check}, vraag {i + 1}:\n  browser: {browserlijst}\n  server : {serverlijst}")


@vereist_node
def test_elk_gegeven_antwoord_leest_hetzelfde_terug():
    """Voor elke vraag en elk puntenaantal: het label dat het rapport toont is
    precies de knop die de bezoeker heeft aangeklikt."""
    with tempfile.TemporaryDirectory() as tmp:
        uit_de_browser = harnas.draai_antwoorden(["data"], pathlib.Path(tmp))[0]

    for i, browserlijst in enumerate(uit_de_browser):
        for label, punten in browserlijst:
            assert S.antwoordlabel_voor_vraag("data", i, punten) == label


def test_data_check_heeft_eigen_antwoorden_per_vraag():
    dims = INHOUD["checks"]["data"]["dims"]
    assert all("qa" in d for d in dims)
    for d in dims:
        assert len(d["qa"]) == 3
        assert all(len(v) == 4 for v in d["qa"])
    alle = [label for d in dims for v in d["qa"] for label in v]
    assert len(alle) == 60

    # Binnen één vraag moeten de vier antwoorden uiteraard verschillen. Over
    # vragen heen mag een formulering terugkomen: "Grotendeels, maar niet voor
    # alle gegevens" past zowel bij eigenaarschap als bij ontsluiting. Dat is
    # geen knip-en-plakfout maar dezelfde nuance bij een andere vraag.
    for d in dims:
        for vraag_labels in d["qa"]:
            assert len(set(vraag_labels)) == 4


def test_kikv_valt_terug_op_de_globale_antwoorden():
    """De KIK-V-check blijft technisch ongewijzigd."""
    assert all("qa" not in d for d in INHOUD["checks"]["kikv"]["dims"])
    assert S.antwoordmogelijkheden("kikv", 0) == [
        ("Aantoonbaar geregeld", 3), ("Grotendeels geregeld", 2),
        ("Beperkt geregeld", 1), ("Nee / onbekend", 0)]
    assert S.antwoordmogelijkheden("kikv", 12)[-1] == ("Weet ik niet", 0)


# ── Scoringspariteit ──────────────────────────────────────────────────────────

@vereist_node
@pytest.mark.parametrize("check", ["data", "kikv"])
def test_scoring_uitputtend_over_alle_dimensietotalen(check):
    """Alle 100.000 combinaties van dimensietotalen, browser tegen server.

    Dit is de volledige uitkomstruimte: een dimensiescore hangt alleen af van de
    som van haar drie antwoorden, dus 10 mogelijkheden per dimensie.
    """
    gevallen = [
        {"check": check, "punten": _vector(combo)}
        for combo in itertools.product(range(10), repeat=5)
    ]
    assert _vergelijk(gevallen) == 100_000


@vereist_node
@pytest.mark.parametrize("check", ["data", "kikv"])
def test_scoring_op_volledige_antwoordreeksen(check):
    """Steekproef over echte antwoordreeksen, inclusief de uitersten."""
    rng = random.Random(20260921)
    gevallen = [
        {"check": check, "punten": [0] * 15},
        {"check": check, "punten": [3] * 15},
        {"check": check, "punten": [3, 0, 0] * 5},
        {"check": check, "punten": [0, 0, 3] * 5},
    ]
    gevallen += [
        {"check": check, "punten": [rng.randint(0, 3) for _ in range(15)]}
        for _ in range(5_000)
    ]
    assert _vergelijk(gevallen) == len(gevallen)


@vereist_node
def test_grenswaarden_leveren_in_beide_implementaties_dezelfde_categorie():
    gevallen = [
        {"check": "data", "punten": _vector(c)}
        for c in [(0, 0, 0, 8, 9), (0, 0, 0, 9, 9),
                  (0, 0, 8, 9, 9), (0, 0, 9, 9, 9),
                  (0, 8, 9, 9, 9), (0, 9, 9, 9, 9)]
    ]
    assert _vergelijk(gevallen) == 6


# ── Zelfstandig draaien, buiten pytest ────────────────────────────────────────

if __name__ == "__main__":
    print("Pariteit van inhoud")
    pad = harnas.sitemap() / CONFIGBESTAND
    gelijk = REGEL.search(pad.read_text(encoding="utf-8")).group(0) == configuratieregel()
    print(f"  {CONFIGBESTAND:<28s} {'byte-identiek' if gelijk else 'AFWIJKING'}")
    assert gelijk
    for pagina in PAGINAS:
        laadt = CONFIGBESTAND in (harnas.sitemap() / pagina).read_text(encoding="utf-8")
        print(f"  {pagina:<28s} {'laadt de configuratie' if laadt else 'LAADT NIET'}")
        assert laadt

    print("\nPariteit van scoring — browsercode uit de baseline tegen de server")
    ok, waarom = harnas.beschikbaar()
    if not ok:
        print(f"  overgeslagen: {waarom}")
        sys.exit(1)

    totaal = 0
    for check in ("data", "kikv"):
        gevallen = [{"check": check, "punten": _vector(c)}
                    for c in itertools.product(range(10), repeat=5)]
        totaal += _vergelijk(gevallen)
        print(f"  {check}: {len(gevallen):,} uitputtende combinaties — gelijk")

        rng = random.Random(20260921)
        steekproef = [{"check": check, "punten": [rng.randint(0, 3) for _ in range(15)]}
                      for _ in range(5_000)]
        totaal += _vergelijk(steekproef)
        print(f"  {check}: {len(steekproef):,} volledige antwoordreeksen — gelijk")

    print(f"\n  {totaal:,} vergelijkingen, geen enkel verschil.")
