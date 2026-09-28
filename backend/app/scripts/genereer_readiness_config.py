"""
genereer_readiness_config.py — Schrijft de browserconfiguratie uit de canonieke bron.

De Readiness Checks op rhoderlanden.rhadix.nl halen hun vragen, adviezen en
grenswaarden uit één regel JavaScript in `assets/readiness-config.js`:

    window.RG_READINESS = {...};

Die regel hoort niet met de hand te worden onderhouden. Dit script leidt hem af
uit `app.services.readiness_content.INHOUD`, dezelfde bron waaruit de server het
rapport opbouwt. Daarmee kunnen scherm en rapport niet uiteenlopen.

Gebruik
-------
    # controleren of de pagina's overeenkomen met de canonieke bron (wijzigt niets)
    python -m app.scripts.genereer_readiness_config --controleer <site-map>

    # de regel afdrukken
    python -m app.scripts.genereer_readiness_config --toon

    # de pagina's bijwerken (alleen op expliciete opdracht)
    python -m app.scripts.genereer_readiness_config --schrijf <site-map>

Afsluitcode 0 als alles overeenkomt, 1 bij een verschil. Geschikt voor CI.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

from app.services.readiness_content import INHOUD

# Het bestand dat de configuratie draagt. Tot de scheiding van de gedeelde
# assets stond deze regel in elke checkpagina; nu staat hij één keer, en laden
# de twee checkpagina's hem als apart script.
CONFIGBESTAND = "assets/readiness-config.js"

# De pagina's die de configuratie gebruiken — gecontroleerd op hun verwijzing.
PAGINAS = ("data-readiness.html", "kik-v-readiness.html")

# Eén regel, exact zoals hij in de pagina staat.
REGEL = re.compile(r"^window\.RG_READINESS = (\{.*\});$", re.M)


def configuratieregel() -> str:
    """De volledige regel zoals die in de HTML hoort te staan.

    `ensure_ascii=False` is geen stijlkeuze: de baseline bevat 26 niet-ASCII
    tekens (é, ë) die daar als teken staan en niet als \\uXXXX-escape. Alleen
    met deze instelling is de uitvoer byte-identiek aan de vastgestelde baseline.
    """
    return "window.RG_READINESS = " + json.dumps(INHOUD, ensure_ascii=False) + ";"


def _huidige_regel(pad: pathlib.Path) -> str | None:
    treffer = REGEL.search(pad.read_text(encoding="utf-8"))
    return treffer.group(0) if treffer else None


def controleer(sitemap: pathlib.Path) -> int:
    verwacht = configuratieregel()
    afwijkingen = 0

    pad = sitemap / CONFIGBESTAND
    if not pad.exists():
        print(f"  ONTBREEKT  {CONFIGBESTAND}")
        afwijkingen += 1
    else:
        huidig = _huidige_regel(pad)
        if huidig is None:
            print(f"  GEEN CONFIGURATIE  {CONFIGBESTAND}")
            afwijkingen += 1
        elif huidig == verwacht:
            print(f"  gelijk     {CONFIGBESTAND}  ({len(verwacht)} tekens)")
        else:
            print(f"  VERSCHIL   {CONFIGBESTAND}  (bestand {len(huidig)} tekens, bron {len(verwacht)})")
            afwijkingen += 1

    # De checkpagina's moeten de configuratie ook werkelijk laden.
    for naam in PAGINAS:
        pagina = sitemap / naam
        if not pagina.exists():
            print(f"  ONTBREEKT  {naam}")
            afwijkingen += 1
        elif CONFIGBESTAND not in pagina.read_text(encoding="utf-8"):
            print(f"  LAADT DE CONFIGURATIE NIET  {naam}")
            afwijkingen += 1
        else:
            print(f"  laadt      {naam}")
    return afwijkingen


def schrijf(sitemap: pathlib.Path) -> int:
    verwacht = configuratieregel()
    pad = sitemap / CONFIGBESTAND
    tekst = pad.read_text(encoding="utf-8")
    if not REGEL.search(tekst):
        print(f"  OVERGESLAGEN  {CONFIGBESTAND}: geen configuratieregel gevonden")
        return 1
    nieuw = REGEL.sub(lambda _: verwacht, tekst, count=1)
    if nieuw == tekst:
        print(f"  ongewijzigd   {CONFIGBESTAND}")
    else:
        pad.write_text(nieuw, encoding="utf-8")
        print(f"  bijgewerkt    {CONFIGBESTAND}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--controleer", metavar="SITEMAP", help="vergelijk de pagina's met de canonieke bron")
    g.add_argument("--schrijf", metavar="SITEMAP", help="werk de pagina's bij")
    g.add_argument("--toon", action="store_true", help="druk de regel af")
    a = p.parse_args(argv)

    if a.toon:
        print(configuratieregel())
        return 0
    if a.controleer:
        n = controleer(pathlib.Path(a.controleer))
        print("  alles gelijk aan de canonieke bron" if n == 0 else f"  {n} afwijking(en)")
        return 0 if n == 0 else 1
    return schrijf(pathlib.Path(a.schrijf))


if __name__ == "__main__":
    sys.exit(main())
