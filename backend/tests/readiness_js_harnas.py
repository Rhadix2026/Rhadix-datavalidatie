"""
readiness_js_harnas.py — Bouwt een Node-harnas uit de échte browsercode.

Waarom dit bestaat
------------------
`readiness_scoring.py` moet exact hetzelfde rekenen als de JavaScript die op
rhoderlanden.rhadix.nl in de browser draait. Een bewering daarover is niets
waard; dit harnas maakt er een controleerbaar feit van.

De aanpak: de relevante functies worden **letterlijk uit de gedeelde
website-assets geknipt** — niet overgetypt, niet nagebouwd — en onder Node
uitgevoerd op dezelfde invoer als de Python-implementatie. Wat hier draait is
dus per constructie de code die de bezoeker ook draait.

Twee bronbestanden:

    site/assets/readiness-config.js   window.RG_READINESS
    site/assets/site.js               band(), cat(), de opbouw van qs, scores()
                                      en de opbouw van de antwoordknoppen

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


def configbestand() -> pathlib.Path:
    return sitemap() / "assets" / "readiness-config.js"


def scriptbestand() -> pathlib.Path:
    return sitemap() / "assets" / "site.js"


def baseline_pagina() -> pathlib.Path:
    """Behouden onder de oude naam: het bestand waaruit de rekenfuncties komen."""
    return scriptbestand()


def node_beschikbaar() -> bool:
    return shutil.which("node") is not None


def beschikbaar() -> tuple[bool, str]:
    if not node_beschikbaar():
        return False, "node is niet beschikbaar"
    for pad in (configbestand(), scriptbestand()):
        if not pad.exists():
            return False, f"website-baseline niet gevonden op {pad}"
    return True, ""


def _knip(bron: str, patroon: str, omschrijving: str, vlaggen: int = re.M | re.S) -> str:
    treffer = re.search(patroon, bron, vlaggen)
    if not treffer:
        raise AssertionError(
            f"Kon '{omschrijving}' niet uit de website-assets knippen. Het script is "
            f"kennelijk gewijzigd; werk het harnas bij voordat je verder gaat."
        )
    return treffer.group(0)


def bouw_harnas() -> str:
    """Stelt het Node-script samen uit de fragmenten van de baseline."""
    bron = scriptbestand().read_text(encoding="utf-8")

    # Deze staan elk op één regel; zonder DOTALL, anders slokt de greedy match
    # de rest van het script op.
    config = _knip(configbestand().read_text(encoding="utf-8"),
                   r"^window\.RG_READINESS = \{.*\};$", "window.RG_READINESS", re.M)
    f_band = _knip(bron, r"^\s*function band\(score\) \{.*\}$", "function band", re.M)
    f_cat = _knip(bron, r"^\s*function cat\(score, top\) \{.*\}$", "function cat", re.M)
    f_qs = _knip(bron, r"^\s*var qs = \[\]; check\.dims\.forEach.*\}\);$", "opbouw van qs", re.M)
    f_scores = _knip(bron, r"^\s*function scores\(\) \{.*?\n    \}$", "function scores")
    f_lijst = _knip(bron, r"^      var list = q\.qa\n.*?CFG\.answers\.map\(function \(a\) \{ return \{ label: a\[0\], v: a\[1\] \}; \}\);$",
                    "opbouw van de antwoordlijst")

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

// De antwoordknoppen zoals de bezoeker ze per vraag te zien krijgt.
function antwoordenVoor(checkSleutel) {{
  var check = CFG.checks[checkSleutel];
{f_qs}
  return qs.map(function (q) {{
{f_lijst}
    if (q.extra) list.push({{ label: q.extra, v: 0, extra: true }});
    return list.map(function (a) {{ return [a.label, a.v]; }});
  }});
}}

var invoer = JSON.parse(require('fs').readFileSync(process.argv[2], 'utf8'));
if (invoer.opdracht === 'antwoorden') {{
  process.stdout.write(JSON.stringify(invoer.checks.map(antwoordenVoor)));
}} else {{
  var uit = invoer.map(function (g) {{ return uitslagVoor(g.check, g.punten); }});
  process.stdout.write(JSON.stringify(uit));
}}
"""


def draai_antwoorden(checks: list[str], werkmap: pathlib.Path) -> list[list[list]]:
    """Geeft per check de vijftien antwoordlijsten terug zoals de browser ze toont.

    Elke lijst is [[label, punten], ...] in schermvolgorde.
    """
    return _voer_uit({"opdracht": "antwoorden", "checks": checks}, werkmap)


def draai(gevallen: list[dict], werkmap: pathlib.Path) -> list[dict]:
    """Voert de gevallen door de browsercode en geeft de uitslagen terug.

    `gevallen`: [{"check": "data"|"kikv", "punten": [15 × 0-3]}, ...]
    """
    return _voer_uit(gevallen, werkmap)


def _voer_uit(invoerdata, werkmap: pathlib.Path):
    werkmap.mkdir(parents=True, exist_ok=True)
    js = werkmap / "harnas.js"
    invoer = werkmap / "invoer.json"
    js.write_text(bouw_harnas(), encoding="utf-8")
    invoer.write_text(json.dumps(invoerdata), encoding="utf-8")

    resultaat = subprocess.run(
        ["node", str(js), str(invoer)],
        capture_output=True, text=True, timeout=300,
    )
    if resultaat.returncode != 0:
        raise AssertionError(f"Node-harnas faalde:\n{resultaat.stderr[:2000]}")
    return json.loads(resultaat.stdout)
