"""
contact.py — Publiek contactendpoint voor de Rhoderlanden-website.

    POST /api/contact

Bediende formulieren: het contactformulier op `contact.html` en de homepage, en
het blok "Bespreek mijn uitslag" onder de Readiness Check. Dat laatste stuurt
een samenvatting van de uitslag mee in het bericht.

Tot nu toe vingen die formulieren hun eigen verzending af met een melding dat
de site een prototype was; er ging dus nooit iets weg. Dit endpoint maakt er een
werkende route van.

Bewust geïsoleerd — dezelfde afbakening als `readiness.py`:

* **geen databasesessie van Datavalidatie** en geen model-import, dus geen
  toegang tot de productiegegevens van Datavalidatie, Rhadix of het CRM;
* **geen authenticatie en geen tenantcontext**;
* **eerst vastleggen, dan doorsturen** — het bericht wordt vastgelegd in de
  eigen website-opslag (`app.website`), daarna per e-mail doorgezet en in het
  CRM geregistreerd. Mislukt een van beide, dan probeert de herhaaltaak het
  later opnieuw; het bericht zelf gaat niet verloren.

Het antwoordadres van de mail is het adres van de afzender, zodat een reactie
rechtstreeks bij de bezoeker uitkomt.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, EmailStr, Field, field_validator

from app.services import readiness_limiet as limiet
from app.website import opslag as website_opslag
from app.website import verwerking as website
from app.website.velden import geldige_aanvraag_id

log = logging.getLogger("rhadix.contact")

router = APIRouter()


class ContactVerzoek(BaseModel):
    """Wat de website mag sturen — en niet meer dan dat."""
    model_config = {"extra": "forbid"}

    naam: str = Field(min_length=2, max_length=120)
    email: EmailStr
    organisatie: str = Field(default="", max_length=160)
    telefoon: str = Field(default="", max_length=40)
    bericht: str = Field(default="", max_length=4000)
    onderwerp: str = Field(default="", max_length=160)
    website: str = Field(default="", max_length=200,
                         description="honeypot — hoort leeg te blijven")

    # Waar vandaan en via welke knop. De site geeft ze mee als ?van= en ?cta=;
    # ontbreken ze, dan is het gewoon het algemene contactformulier.
    van: str = Field(default="", max_length=64)
    cta: str = Field(default="", max_length=64)

    # Campagneherkomst, dezelfde vijf als bij het Readiness-rapport.
    utm_source: str = Field(default="", max_length=120)
    utm_medium: str = Field(default="", max_length=120)
    utm_campaign: str = Field(default="", max_length=160)
    utm_content: str = Field(default="", max_length=160)
    utm_term: str = Field(default="", max_length=160)
    # Door de browser per formulier gemaakt; dezelfde id nog eens = dezelfde
    # inzending, geen tweede bericht.
    aanvraag_id: str = Field(default="", max_length=36)

    controleer_aanvraag_id = field_validator("aanvraag_id")(geldige_aanvraag_id)

    @field_validator("naam", "organisatie", "telefoon", "onderwerp")
    @classmethod
    def _normaliseer(cls, v: str) -> str:
        return " ".join(v.split())

    @field_validator("naam")
    @classmethod
    def _naam_niet_leeg(cls, v: str) -> str:
        if len(v) < 2:
            raise ValueError("te kort")
        return v

    @field_validator("bericht")
    @classmethod
    def _iets_te_melden(cls, v: str) -> str:
        return v.strip()


class ContactAntwoord(BaseModel):
    ok: bool
    verzonden: bool               # de melding aan ons is verstuurd
    herhaling: bool = False
    opgeslagen: bool = False      # het bericht is duurzaam vastgelegd
    aanvraag_id: str | None = None


@router.post("", response_model=ContactAntwoord,
             summary="Stuurt een bericht van de website door naar Rhoderlanden Groep")
def contact(verzoek: ContactVerzoek, response: Response) -> ContactAntwoord:
    # 1 — Honeypot. Bots vullen verborgen velden; mensen zien ze niet.
    if verzoek.website.strip():
        log.info("Contact: honeypot gevuld, verzoek genegeerd")
        response.status_code = status.HTTP_202_ACCEPTED
        return ContactAntwoord(ok=True, verzonden=False)

    # 2 — Een bericht zonder inhoud én zonder onderwerp is niets om door te sturen.
    if not verzoek.bericht and not verzoek.onderwerp:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "Laat een bericht achter, dan kunnen we er iets mee.")

    # 3 — Begrenzing. Dezelfde assen als bij het Readiness-rapport: een
    #     vingerafdruk van de aanvraag tegen dubbelklikken, en een teller per
    #     e-mailadres tegen herhaald misbruik. Niet op IP, omdat de site achter
    #     Cloudflare staat en de backend daar alleen Cloudflare-adressen ziet.
    afdruk = limiet.vingerafdruk(
        verzoek.email, "contact",
        [verzoek.naam, verzoek.organisatie, verzoek.onderwerp, verzoek.bericht],
    )
    if limiet.is_herhaling(afdruk):
        log.info("Contact: herhaald bericht binnen het venster, niet opnieuw verstuurd")
        return ContactAntwoord(ok=True, verzonden=False, herhaling=True)

    if limiet.te_veel_voor_adres(verzoek.email):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Er zijn kort na elkaar meerdere berichten vanaf dit e-mailadres verstuurd. "
            "Probeer het later opnieuw, of bel ons.",
        )

    # 4 — Vastleggen, dan doorsturen en in het CRM registreren. Spam komt hier
    #     niet: honeypot en herhaling keren hierboven al terug.
    ontvangst = website.ontvang(website.CONTACT, {
        "naam": verzoek.naam, "email": verzoek.email, "organisatie": verzoek.organisatie,
        "telefoon": verzoek.telefoon, "bericht": verzoek.bericht,
        "onderwerp": verzoek.onderwerp, "van": verzoek.van, "cta": verzoek.cta,
        "campagne": {s: getattr(verzoek, s) for s in
                     ("utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term")
                     if getattr(verzoek, s)} or None,
    }, aanvraag_id=verzoek.aanvraag_id or None)
    verzonden = ontvangst.gelukt(website_opslag.MAIL_INTERN)

    if not ontvangst.opgeslagen and not verzonden:
        log.error("Contact: bericht niet verstuurd en niet vastgelegd")
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Uw bericht kon nu niet worden verstuurd. Probeer het later opnieuw of "
            "mail ons rechtstreeks.",
        )

    if ontvangst.nieuw:
        limiet.leg_vast(afdruk, verzoek.email)

    return ContactAntwoord(ok=True, verzonden=verzonden, herhaling=not ontvangst.nieuw,
                           opgeslagen=ontvangst.opgeslagen, aanvraag_id=ontvangst.aanvraag_id)
