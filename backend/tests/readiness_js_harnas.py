"""
readiness_js_harnas.py — Bouwt een Node-harnas uit de échte browsercode.

Waarom dit bestaat
------------------
`readiness_scoring.py` moet exact hetzelfde rekenen als de JavaScript die op
rhoderlanden.rhadix.nl in de browser draait. Een bewering daarover is niets
waard; dit harnas maakt er een controleerbaar feit van.

De aanpak: de relevante functies worden **letterlijk uit de vastgestelde
website-baseline geknipt** — niet overgetypt, niet nagebouwd — en onder Node
uitgevoerd op dezelfde invoer als de Python-implementatie. Wat hier draait is
dus per constructie de code die de bezoeker ook draait.

Geknipte fragmenten (met regelnummer in `site/data-readiness.html`):

    673  function band(score)   bandindeling 0-3
    674  function cat(score,top) categorienaam, bovenste band erft `top`
    681  var qs = [] ...        opbouw van de vijftien vragen
    686  function scores()      dimensiescores, totaal en rangschikking

Wordt het harnas niet gevonden (geen Node, of de baseline ontbreekt), dan slaat
de pariteitstest over met een duidelijke melding in plaats van stilletjes groen
te worden.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import shutil
import subprocess

# De vastgestelde website-baseline. Buiten de ontwikkelmachine niet aanwezig;
# via RHODERLANDEN_SITE te overschrijven.
STANDAARD_SITE = pathlib.Path.home() / "Developer" / "rhoderlanden-website" / "site"


def sitemap() -> pathlib.Path:
    return pathlib.Path(os.getenv("RHODERLANDEN_SITE", str(STANDAARD_SITE)))


def baseline_pagina() -> pathlib.Path:
    return sitemap() / "data-readiness.html"


def node_beschikbaar() -> bool:
    return shutil.which("node") is not None


def beschikbaar() -> tuple[bool, str]:
    if not node_beschikbaar():
        return False, "node is niet beschikbaar"
    if not baseline_pagina().exists():
        return False, f"website-baseline niet gevonden op {baseline_pagina()}"
    return True, ""


def _knip(bron: str, patroon: str, omschrijving: str, vlaggen: int = re.M | re.S) -> str:
    treffer = re.search(patroon, bron, vlaggen)
    if not treffer:
        raise AssertionError(
            f"Kon '{omschrijving}' niet uit de baseline knippen. De pagina is "
            f"kennelijk gewijzigd; werk het harnas bij voordat je verder gaat."
        )
    return treffer.group(0)


def bouw_harnas() -> str:
    """Stelt het Node-script samen uit de fragmenten van de baseline."""
    bron = baseline_pagina().read_text(encoding="utf-8")

    # Deze drie staan elk op één regel; zonder DOTALL, anders slokt de greedy
    # match de rest van het script op.
    config = _knip(bron, r"^window\.RG_READINESS = \{.*\};$", "window.RG_READINESS", re.M)
    f_band = _knip(bron, r"^\s*function band\(score\) \{.*\}$", "function band", re.M)
    f_cat = _knip(bron, r"^\s*function cat\(score, top\) \{.*\}$", "function cat", re.M)
    f_qs = _knip(bron, r"^\s*var qs = \[\]; check\.dims\.forEach.*\}\);$", "opbouw van qs", re.M)
    f_scores = _knip(bron, r"^\s*function scores\(\) \{.*?\n    \}$", "function scores")

    return f"""
// Samengesteld uit de vastgestelde website-baseline. Niet met de hand bewerken.
var window = {{}};   // in de browser bestaat dit; onder Node niet
{config}
var CFG = window.RG_READINESS;
{f_band}
{f_cat}

function uitslagVoor(checkSleutel, punten) {{
  var check = CFG.checks[checkSleutel];
{f_qs}
  var answers = punten.map(function (p) {{ return {{ v: p, label: '' }}; }});
{f_scores}
  var s = scores();
  return {{
    totaal: s.total,
    categorie: s.category,
    dimensies: s.dims.map(function (d) {{ return d.score; }}),
    rangschikking: s.ranked.map(function (d) {{ return d.i; }}),
    duiding: s.meaning
  }};
}}

var invoer = JSON.parse(require('fs').readFileSync(process.argv[2], 'utf8'));
var uit = invoer.map(function (g) {{ return uitslagVoor(g.check, g.punten); }});
process.stdout.write(JSON.stringify(uit));
"""


def draai(gevallen: list[dict], werkmap: pathlib.Path) -> list[dict]:
    """Voert de gevallen door de browsercode en geeft de uitslagen terug.

    `gevallen`: [{"check": "data"|"kikv", "punten": [15 × 0-3]}, ...]
    """
    werkmap.mkdir(parents=True, exist_ok=True)
    js = werkmap / "harnas.js"
    invoer = werkmap / "invoer.json"
    js.write_text(bouw_harnas(), encoding="utf-8")
    invoer.write_text(json.dumps(gevallen), encoding="utf-8")

    resultaat = subprocess.run(
        ["node", str(js), str(invoer)],
        capture_output=True, text=True, timeout=300,
    )
    if resultaat.returncode != 0:
        raise AssertionError(f"Node-harnas faalde:\n{resultaat.stderr[:2000]}")
    return json.loads(resultaat.stdout)
