"""
readiness_crm.py — Registreert een rapportaanvraag in het CRM voor opvolging.

Waarom via de API en niet via de database
-----------------------------------------
Het Readiness-endpoint is bewust zonder databasesessie gebouwd. Die afbakening
blijft overeind: het CRM wordt benaderd als externe partij, over HTTPS, met een
eigen serviceaccount. Deze module is het enige punt dat naar buiten praat.

Authenticatie
-------------
Het CRM weigert lokale tokens met zoveel woorden — `beoordeel_toegang()` geeft
daar *"geen centraal SSO-token (lokaal token draagt geen apps-claim)"*. Er is
dus een **centraal** token nodig met `rhadix-crm` in de `apps`-claim. De module
logt daarvoor in bij de centrale uitgever (Datavalidatie) met een serviceaccount
en bewaart het token tot kort voor het verloopt.

Wat er wordt vastgelegd
-----------------------
Per aanvraag één activiteit bij het contact, met naam, organisatie, e-mailadres,
datum en tijd, de totaalscore, de vijf dimensiescores, de classificatie, de bron
en eventuele campagnegegevens. **Niet** de vijftien afzonderlijke antwoorden:
die staan al in het rapport dat de aanvrager ontvangt, en voor commerciële
opvolging voegen ze niets toe dat de dimensiescores niet al zeggen.

Elke aanvraag wordt een **nieuwe** activiteit, ook van hetzelfde contact. Zo
blijft de reeks checks van één organisatie zichtbaar als losse, gedateerde
interacties.

Nooit blokkerend
----------------
Geen enkele fout hier mag de bezoeker zijn rapport kosten. Alles is afgevangen;
bij een storing wordt gelogd wat er misging én de gegevens die nodig zijn om de
registratie later met de hand te herstellen.

Niet geconfigureerd is geen fout
--------------------------------
Zonder `CRM_SERVICE_EMAIL` en `CRM_SERVICE_WACHTWOORD` slaat de module over. Een
omgeving zonder CRM-koppeling draait dus gewoon door.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from datetime import date, datetime, timezone

import requests

log = logging.getLogger("rhadix.readiness.crm")

TIJDSLIMIET = 8          # seconden per aanroep; een traag CRM mag niemand laten wachten
TOKENMARGE = 60          # seconden vóór het verlopen alvast opnieuw inloggen

ACTIVITEIT_TITEL = "Data Readiness Check – rapport aangevraagd"
BRON = "Data Readiness Check"

_slot = threading.Lock()
_token: dict = {"waarde": None, "geldig_tot": 0.0}


# ── Instellingen ──────────────────────────────────────────────────────────────

def _env(sleutel: str, standaard: str = "") -> str:
    return (os.getenv(sleutel) or "").strip() or standaard


def basis_url() -> str:
    return _env("CRM_BASIS_URL").rstrip("/")


def login_url() -> str:
    """De centrale uitgever; standaard dezelfde applicatie als waarin dit draait."""
    return _env("CRM_LOGIN_URL", _env("PUBLIC_BASE_URL")).rstrip("/")


def ingeschakeld() -> bool:
    return bool(_env("CRM_SERVICE_EMAIL") and _env("CRM_SERVICE_WACHTWOORD")
                and basis_url() and login_url())


# ── Token ─────────────────────────────────────────────────────────────────────

def _vervaltijd(token: str) -> float:
    """Leest `exp` uit de payload zonder de handtekening te controleren.

    Dat mag hier: we gebruiken het alleen om te weten wanneer we opnieuw moeten
    inloggen. Het CRM controleert de handtekening zelf.
    """
    import base64
    import json
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return float(json.loads(base64.urlsafe_b64decode(payload)).get("exp", 0))
    except Exception:
        return 0.0


def _haal_token(vernieuw: bool = False) -> str | None:
    nu = time.time()
    with _slot:
        if not vernieuw and _token["waarde"] and nu < _token["geldig_tot"]:
            return _token["waarde"]
    try:
        antwoord = requests.post(
            f"{login_url()}/api/auth/login",
            json={"email": _env("CRM_SERVICE_EMAIL"), "password": _env("CRM_SERVICE_WACHTWOORD")},
            timeout=TIJDSLIMIET,
        )
        antwoord.raise_for_status()
        waarde = antwoord.json().get("access_token")
        if not waarde:
            log.error("CRM: login gaf geen token terug")
            return None
    except Exception as fout:
        log.error("CRM: inloggen met het serviceaccount mislukte: %s", fout)
        return None

    verloopt = _vervaltijd(waarde)
    with _slot:
        _token["waarde"] = waarde
        _token["geldig_tot"] = (verloopt - TOKENMARGE) if verloopt else (time.time() + 600)
    return waarde


def _aanroep(methode: str, pad: str, **kw):
    """Eén CRM-aanroep, met één hernieuwde poging na een 401."""
    for poging in (1, 2):
        token = _haal_token(vernieuw=(poging == 2))
        if not token:
            return None
        try:
            antwoord = requests.request(
                methode, f"{basis_url()}{pad}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=TIJDSLIMIET, **kw,
            )
        except Exception as fout:
            log.error("CRM: %s %s mislukte: %s", methode, pad, fout)
            return None
        if antwoord.status_code == 401 and poging == 1:
            log.info("CRM: token afgewezen, opnieuw inloggen")
            continue
        if antwoord.status_code >= 400:
            log.error("CRM: %s %s gaf %s — %s", methode, pad,
                      antwoord.status_code, antwoord.text[:300])
            return None
        return antwoord.json() if antwoord.content else {}
    return None


# ── Opzoeken en aanmaken ──────────────────────────────────────────────────────

def _gelijk(a: str | None, b: str | None) -> bool:
    return (a or "").strip().lower() == (b or "").strip().lower()


def zoek_contact(email: str) -> dict | None:
    """Zoekt een contactpersoon op e-mailadres.

    Het CRM kent geen filter op e-mailadres — `GET /crm/contactpersonen` zoekt
    alleen in naam, organisatie en functie. We halen de lijst op en vergelijken
    hier exact. Bij de huidige omvang (enkele honderden contacten) is dat prima;
    groeit dat, dan is een `?email=`-parameter in het CRM de nette oplossing.
    """
    lijst = _aanroep("GET", "/api/crm/contactpersonen")
    if not isinstance(lijst, list):
        return None
    for c in lijst:
        if _gelijk(c.get("email"), email):
            return c
    return None


def zoek_organisatie(naam: str) -> dict | None:
    if not naam:
        return None
    lijst = _aanroep("GET", "/api/crm/organisaties", params={"q": naam})
    if not isinstance(lijst, list):
        return None
    for o in lijst:
        if _gelijk(o.get("naam"), naam):
            return o
    return None


def _maak_organisatie(naam: str) -> dict | None:
    return _aanroep("POST", "/api/crm/organisaties", json={
        "naam": naam,
        "bron_opmerking": f"Automatisch aangemaakt vanuit de {BRON} op de website.",
        "betrouwbaarheid": "Laag",
    })


def _maak_contact(naam: str, email: str, organisatie: str, organisatie_id: str | None) -> dict | None:
    return _aanroep("POST", "/api/crm/contactpersonen", json={
        "naam": naam,
        "email": email,
        "organisatie_id": organisatie_id,
        "organisatie_naam": organisatie,
        "bron_type": BRON,
        "zekerheid": "Hoog",          # de bezoeker heeft het zelf ingevuld
        "opmerking": f"Aangemeld via de {BRON} op de website.",
    })


# ── Omschrijving van de activiteit ────────────────────────────────────────────

def _omschrijving(uitslag, naam: str, organisatie: str, email: str,
                  campagne: dict | None) -> str:
    moment = datetime.now(timezone.utc).astimezone().strftime("%d-%m-%Y %H:%M")
    # De naam staat ook op het contact zelf, maar hoort hier eveneens: een
    # bestaand contact kan onder een andere naam bekend zijn, en dan is dit de
    # naam die de aanvrager zelf heeft ingevuld.
    regels = [
        f"Bron: {BRON} (website)",
        f"Aangevraagd op: {moment}",
        f"Aangevraagd door: {naam}",
        f"Organisatie: {organisatie}",
        f"E-mailadres: {email}",
        "",
        f"Totaalscore: {uitslag.totaal} van 100 — {uitslag.categorie}",
        "",
        "Dimensiescores:",
    ]
    regels += [f"  {d.naam}: {d.score}" for d in uitslag.dimensies]
    zwak = uitslag.aandachtspunten
    regels += [
        "",
        f"Grootste aandachtspunten: {zwak[0].naam} ({zwak[0].score}) "
        f"en {zwak[1].naam} ({zwak[1].score}).",
    ]
    if campagne:
        regels += ["", "Campagne:"]
        regels += [f"  {sleutel}: {waarde}" for sleutel, waarde in sorted(campagne.items()) if waarde]
    regels += [
        "",
        "De vijftien afzonderlijke antwoorden worden niet vastgelegd; het volledige "
        "rapport is naar de aanvrager verstuurd.",
    ]
    return "\n".join(regels)


# ── Hoofdingang ───────────────────────────────────────────────────────────────

def registreer(uitslag, naam: str, organisatie: str, email: str,
               pdf: bytes | None = None, campagne: dict | None = None) -> dict | None:
    """Legt de aanvraag vast in het CRM. Geeft de aangemaakte activiteit terug,
    of None als het niet lukte of als er geen koppeling is ingesteld.

    Werpt nooit een uitzondering: de aanvraag van de bezoeker gaat voor.
    """
    if not ingeschakeld():
        log.debug("CRM: geen koppeling ingesteld, registratie overgeslagen")
        return None

    try:
        # 1 — Bestaat de organisatie al?
        org = zoek_organisatie(organisatie)
        if org is None and organisatie:
            org = _maak_organisatie(organisatie)
            if org:
                log.info("CRM: organisatie aangemaakt — %s", organisatie)
        org_id = (org or {}).get("id")

        # 2 — Bestaat het contact al? Zo ja, laten staan: niets overschrijven.
        contact = zoek_contact(email)
        if contact is None:
            contact = _maak_contact(naam, email, organisatie, org_id)
            if contact:
                log.info("CRM: contactpersoon aangemaakt — %s", email)
        else:
            log.info("CRM: bestaand contact gevonden — %s", email)
        contact_id = (contact or {}).get("id")

        if not contact_id and not org_id:
            log.error("CRM: geen contact en geen organisatie; activiteit niet vastgelegd "
                      "(naam=%s organisatie=%s email=%s)", naam, organisatie, email)
            return None

        # 3 — Altijd een nieuwe, gedateerde activiteit: meerdere checks van
        #     hetzelfde contact blijven daardoor als losse interacties zichtbaar.
        activiteit = _aanroep("POST", "/api/crm/activiteiten", json={
            "titel": ACTIVITEIT_TITEL,
            "soort": "notitie",
            "status": "open",
            "datum": date.today().isoformat(),
            "organisatie_id": org_id,
            "contactpersoon_id": contact_id,
            "omschrijving": _omschrijving(uitslag, naam, organisatie, email, campagne),
        })
        if not activiteit:
            log.error("CRM: activiteit niet vastgelegd voor %s (%s), score %s",
                      email, organisatie, uitslag.totaal)
            return None

        # 4 — Het rapport zelf. Het CRM kent geen documenten of bijlagen: er is
        #     geen tabel, geen endpoint en geen opslag voor bestanden. De PDF
        #     wordt daarom niet meegestuurd. De bytes komen hier al binnen, dus
        #     zodra het CRM bijlagen ondersteunt is dit één aanroep erbij — en
        #     nadrukkelijk dezelfde PDF als de aanvrager kreeg, niet een tweede.
        if pdf:
            log.info("CRM: activiteit %s vastgelegd; het rapport (%d bytes) is niet "
                     "meegestuurd omdat het CRM geen bijlagen ondersteunt",
                     activiteit.get("id"), len(pdf))

        return activiteit

    except Exception:
        log.exception("CRM: onverwachte fout bij het registreren van %s (%s)", email, organisatie)
        return None
