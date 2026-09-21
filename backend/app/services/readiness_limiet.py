"""
readiness_limiet.py — Misbruikbegrenzing voor het publieke Readiness-endpoint.

Het endpoint is publiek en verstuurt e-mail; zonder rem is dat een instrument
om iemand anders' postbus mee te vullen. De begrenzing werkt op twee assen:

1. **Vingerafdruk** — e-mailadres plus de vijftien antwoorden plus het type
   check. Twee keer exact dezelfde aanvraag binnen het venster levert géén
   tweede mail op. Dat vangt het gewone geval af: de bezoeker die twee keer op
   de knop drukt of de pagina herlaadt.
2. **E-mailadres** — hoeveel verschillende aanvragen één adres binnen het
   venster mag doen. Dat vangt het minder gewone geval af: iemand die met
   wisselende antwoorden hetzelfde adres blijft bestoken.

Waarom niet op IP-adres
-----------------------
De site staat achter Cloudflare en nginx heeft op dit moment geen
`real_ip`-configuratie; de backend ziet dus uitsluitend Cloudflare-adressen.
Begrenzen op IP zou alle bezoekers in één emmer gooien — één bot sluit dan
iedereen buiten. Een meegestuurde `CF-Connecting-IP` is evenmin te vertrouwen
zolang de origin ook rechtstreeks bereikbaar is. Zodra de origin op de
Cloudflare-ranges is afgesloten én `set_real_ip_from` is ingesteld, kan een
IP-as hier zonder herontwerp bij.

In het geheugen van het proces, net als `auth/brute_force.py`. Bij een herstart
is de teller leeg; dat is aanvaardbaar voor dit doel en scheelt een tabel.
"""
from __future__ import annotations

import hashlib
import os
import threading
import time

# Twee keer exact dezelfde aanvraag binnen dit venster → geen tweede mail.
HERHAALVENSTER_SECONDEN = int(os.getenv("READINESS_HERHAALVENSTER", "900"))      # 15 minuten
# Aantal verschillende aanvragen per e-mailadres binnen het venster.
MAX_PER_ADRES = int(os.getenv("READINESS_MAX_PER_ADRES", "5"))
ADRESVENSTER_SECONDEN = int(os.getenv("READINESS_ADRESVENSTER", "3600"))         # 1 uur

_slot = threading.Lock()
_vingerafdrukken: dict[str, float] = {}
_per_adres: dict[str, list[float]] = {}


def vingerafdruk(email: str, check: str, antwoorden: list[int]) -> str:
    """Stabiele sleutel voor 'dezelfde aanvraag'.

    Het e-mailadres wordt genormaliseerd en gehasht; we bewaren het adres dus
    niet in leesbare vorm in het geheugen van het proces.
    """
    ruw = "|".join([email.strip().lower(), check, ",".join(str(a) for a in antwoorden)])
    return hashlib.sha256(ruw.encode("utf-8")).hexdigest()


def _adressleutel(email: str) -> str:
    return hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()


def _opschonen(nu: float) -> None:
    """Oude sporen wissen. Wordt bij elke aanvraag aangeroepen, zodat het
    geheugengebruik niet meegroeit met het aantal bezoekers."""
    for sleutel, gezien in list(_vingerafdrukken.items()):
        if nu - gezien > HERHAALVENSTER_SECONDEN:
            del _vingerafdrukken[sleutel]
    for sleutel, tijden in list(_per_adres.items()):
        recent = [t for t in tijden if nu - t <= ADRESVENSTER_SECONDEN]
        if recent:
            _per_adres[sleutel] = recent
        else:
            del _per_adres[sleutel]


def is_herhaling(afdruk: str) -> bool:
    """Is deze exacte aanvraag al eerder binnen het venster gedaan?"""
    nu = time.time()
    with _slot:
        _opschonen(nu)
        gezien = _vingerafdrukken.get(afdruk)
        return gezien is not None and nu - gezien <= HERHAALVENSTER_SECONDEN


def te_veel_voor_adres(email: str) -> bool:
    """Heeft dit adres zijn aantal aanvragen binnen het venster opgebruikt?"""
    nu = time.time()
    with _slot:
        _opschonen(nu)
        return len(_per_adres.get(_adressleutel(email), [])) >= MAX_PER_ADRES


def leg_vast(afdruk: str, email: str) -> None:
    """Noteert een geslaagde aanvraag voor beide assen."""
    nu = time.time()
    with _slot:
        _vingerafdrukken[afdruk] = nu
        _per_adres.setdefault(_adressleutel(email), []).append(nu)


def wis_alles() -> None:
    """Alleen voor tests."""
    with _slot:
        _vingerafdrukken.clear()
        _per_adres.clear()
