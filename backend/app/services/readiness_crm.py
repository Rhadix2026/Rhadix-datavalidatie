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

from app.services import website_cta as cta

log = logging.getLogger("rhadix.readiness.crm")

TIJDSLIMIET = 8          # seconden per aanroep; een traag CRM mag niemand laten wachten
TOKENMARGE = 60          # seconden vóór het verlopen alvast opnieuw inloggen

ACTIVITEIT_TITEL = "Data Readiness Check – rapport aangevraagd"
BRON = "Data Readiness Check"
# Herkomst: iedereen die via de website binnenkomt. Het relatietype (categorie)
# blijft leeg -- dat weten we niet en raden we niet.
HERKOMST = "Website"

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


def _maak_organisatie(naam: str, bron_opmerking: str) -> dict | None:
    return _aanroep("POST", "/api/crm/organisaties", json={
        "naam": naam,
        # Expliciet OVERIG. Laten we soort weg, dan zet het CRM er "VVT" op --
        # verpleeg- en verzorgingshuizen en thuiszorg. Van een organisatie die
        # zichzelf via de website aanmeldt weten we dat niet, en zo'n label komt
        # later terug als een indeling waar niemand op heeft gestuurd.
        "soort": "OVERIG",
        "bron_opmerking": bron_opmerking,
        "betrouwbaarheid": "Laag",
    })


def _maak_contact(naam: str, email: str, organisatie: str, organisatie_id: str | None,
                  status: str, bronpagina: str, opmerking: str,
                  telefoon: str = "") -> dict | None:
    return _aanroep("POST", "/api/crm/contactpersonen", json={
        "naam": naam,
        "email": email,
        "telefoon": telefoon,
        "organisatie_id": organisatie_id,
        "organisatie_naam": organisatie,
        # Herkomst en waar de eerste aanraking plaatsvond.
        "bron_type": HERKOMST,
        "bronpagina": bronpagina,
        "bron_url": cta.bron_url(bronpagina),
        # Waar deze persoon in het proces staat.
        "status": status,
        # Het relatietype blijft BEWUST leeg. We weten niet of dit een
        # zorgorganisatie, een leverancier of een adviesbureau is, en een keuze
        # uit een lijst is geen kennis. Leeg betekent onbekend, en dat is
        # bruikbare informatie.
        "zekerheid": "Hoog",          # de bezoeker heeft het zelf ingevuld
        "opmerking": opmerking,
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
            org = _maak_organisatie(
                organisatie,
                f"Automatisch aangemaakt vanuit de {BRON} op de website.")
            if org:
                log.info("CRM: organisatie aangemaakt — %s", organisatie)
        org_id = (org or {}).get("id")

        # 2 — Bestaat het contact al? Zo ja, laten staan: niets overschrijven.
        contact = zoek_contact(email)
        if contact is None:
            contact = _maak_contact(
                naam, email, organisatie, org_id,
                status=cta.STATUS_READINESS,
                bronpagina="data-readiness",
                opmerking=f"Aangemeld via de {BRON} op de website.")
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
            "kanaal": cta.KANAAL_READINESS,
            "interesse": cta.INTERESSE_READINESS,
            "bronpagina": "data-readiness",
            "campagne": cta.campagne_kort(campagne),
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


# ── Het contactformulier ──────────────────────────────────────────────────────

def _omschrijving_bericht(naam: str, organisatie: str, email: str, telefoon: str,
                          onderwerp: str, bericht: str, kanaal: str, interesse: str,
                          bronpagina: str, campagne: dict | None) -> str:
    moment = datetime.now(timezone.utc).astimezone().strftime("%d-%m-%Y %H:%M")
    regels = [
        "Bron: contactformulier (website)",
        f"Ontvangen op: {moment}",
        f"Kanaal: {kanaal}",
        f"Interesse: {interesse}",
        f"Vanaf pagina: {cta.bron_url(bronpagina)}",
        "",
        f"Naam: {naam}",
        f"Organisatie: {organisatie or '—'}",
        f"E-mailadres: {email}",
        f"Telefoon: {telefoon or '—'}",
    ]
    if onderwerp:
        regels.append(f"Onderwerp: {onderwerp}")
    if bericht:
        regels += ["", "Bericht:", bericht]
    if campagne:
        regels.append("")
        regels.append("Campagne:")
        for sleutel in sorted(campagne):
            if campagne[sleutel]:
                regels.append(f"  {sleutel}: {campagne[sleutel]}")
    return "\n".join(regels)


def registreer_bericht(naam: str, email: str, organisatie: str = "", telefoon: str = "",
                       onderwerp: str = "", bericht: str = "",
                       van: str = "", cta_code: str = "",
                       campagne: dict | None = None) -> dict | None:
    """Legt een inzending van het contactformulier vast in het CRM.

    Zelfde opzet als `registreer()`: organisatie en contact alleen als ze nog
    niet bestaan, en altijd een nieuwe activiteit. Een bestaand contact wordt
    nooit overschreven -- ook zijn status niet, ook niet als die al "Klant" is.
    Er komt alleen een moment bij.

    Werpt nooit een uitzondering: het bericht van de bezoeker gaat voor.
    """
    if not ingeschakeld():
        log.debug("CRM: geen koppeling ingesteld, bericht niet geregistreerd")
        return None

    kanaal, interesse, status, bronpagina = cta.duiding(van, cta_code)

    try:
        org = zoek_organisatie(organisatie) if organisatie else None
        if org is None and organisatie:
            org = _maak_organisatie(
                organisatie, "Automatisch aangemaakt vanuit het contactformulier "
                             "op de website.")
            if org:
                log.info("CRM: organisatie aangemaakt — %s", organisatie)
        org_id = (org or {}).get("id")

        contact = zoek_contact(email)
        if contact is None:
            contact = _maak_contact(
                naam, email, organisatie, org_id,
                status=status, bronpagina=bronpagina, telefoon=telefoon,
                opmerking="Aangemeld via het contactformulier op de website.")
            if contact:
                log.info("CRM: contactpersoon aangemaakt — %s (status %s)", email, status)
        else:
            log.info("CRM: bestaand contact gevonden — %s, status blijft ongewijzigd", email)
        contact_id = (contact or {}).get("id")

        if not contact_id and not org_id:
            log.error("CRM: geen contact en geen organisatie; bericht niet vastgelegd "
                      "(naam=%s organisatie=%s email=%s)", naam, organisatie, email)
            return None

        # Bij kanaal "Contactformulier" zou het voorvoegsel zichzelf herhalen.
        titel = ("Contactformulier" if kanaal == cta.STANDAARD_KANAAL
                 else f"Contactformulier – {kanaal.lower()}")
        if interesse and interesse != cta.STANDAARD_INTERESSE:
            titel = f"{titel} – {interesse}" if kanaal == cta.STANDAARD_KANAAL \
                else f"{titel} {interesse}"

        activiteit = _aanroep("POST", "/api/crm/activiteiten", json={
            "titel": titel[:255],
            "soort": "notitie",
            "status": "open",
            "datum": date.today().isoformat(),
            "organisatie_id": org_id,
            "contactpersoon_id": contact_id,
            "kanaal": kanaal,
            "interesse": interesse,
            "bronpagina": bronpagina,
            "campagne": cta.campagne_kort(campagne),
            "omschrijving": _omschrijving_bericht(
                naam, organisatie, email, telefoon, onderwerp, bericht,
                kanaal, interesse, bronpagina, campagne),
        })
        if activiteit:
            log.info("CRM: activiteit %s vastgelegd — %s", activiteit.get("id"), titel)
        return activiteit

    except Exception:
        log.exception("CRM: registratie van het bericht mislukte; het bericht zelf is wel verstuurd")
        return None
