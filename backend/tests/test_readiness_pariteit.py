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
    PAGINAS, REGEL, configuratieregel,
)
from app.services import readiness_scoring as S            # noqa: E402

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
@pytest.mark.parametrize("pagina", PAGINAS)
def test_gegenereerde_configuratie_is_identiek_aan_de_baseline(pagina):
    """De kern van het centraliseren: genereren verandert niets aan de site."""
    pad = harnas.sitemap() / pagina
    treffer = REGEL.search(pad.read_text(encoding="utf-8"))
    assert treffer, f"{pagina} bevat geen configuratieregel"
    assert treffer.group(0) == configuratieregel(), (
        f"De uit readiness_content.py gegenereerde configuratie wijkt af van {pagina}."
    )


@vereist_baseline
def test_beide_paginas_dragen_dezelfde_configuratie():
    regels = {
        p: REGEL.search((harnas.sitemap() / p).read_text(encoding="utf-8")).group(0)
        for p in PAGINAS
    }
    assert len(set(regels.values())) == 1


@vereist_baseline
def test_baseline_bevat_de_verwachte_checks_en_vragen():
    """Vangt op dat de site stilletjes andere vragen zou gaan tonen."""
    ruwe = REGEL.search(
        (harnas.baseline_pagina()).read_text(encoding="utf-8")
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
    for pagina in PAGINAS:
        pad = harnas.sitemap() / pagina
        gelijk = REGEL.search(pad.read_text(encoding="utf-8")).group(0) == configuratieregel()
        print(f"  {pagina:<24s} {'byte-identiek' if gelijk else 'AFWIJKING'}")
        assert gelijk

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
