"""
readiness.py — Publiek endpoint voor het Readiness-rapport van Rhoderlanden Groep.

    POST /api/readiness/report

Bewust geïsoleerd
-----------------
Deze router staat los van de rest van Datavalidatie:

* **geen databasesessie van Datavalidatie** — er is geen `Depends(get_db)` en er
  wordt geen model uit `app.models` geïmporteerd. Deze code kan dus niets lezen
  of schrijven in de tabellen van Datavalidatie of Rhadix;
* **geen authenticatie en geen tenantcontext** — geen `Depends(get_current_user)`,
  geen organisatie, geen rol, geen applicatietoegang.

Vastleggen vóór versturen
-------------------------
De aanvraag wordt eerst vastgelegd in de eigen website-opslag (`app.website`,
schema `website`, eigen engine), en pas daarna verwerkt: het rapport aan de
bezoeker, de melding aan ons en de registratie in het CRM. Mislukt een van die
stappen, dan gaat de aanvraag niet verloren: de herhaaltaak probeert het later
opnieuw. Is de opslag zelf niet beschikbaar, dan valt het endpoint terug op de
werkwijze van vóór deze wijziging.

Het antwoord zegt wat er werkelijk gebeurd is: `opgeslagen` (vastgelegd) en
`rapport` (`verzonden`, `in_wachtrij` of `mislukt`). De website baseert zijn
melding en zijn conversiemeting daarop.

Wat het endpoint wél doet, staat hieronder in `rapport()`, in die volgorde.

Vertrouwensgrens
----------------
De browser stuurt uitsluitend de vijftien antwoorden mee. Een meegestuurde
score wordt niet geaccepteerd: het verzoekmodel kent het veld niet, en
`readiness_scoring.bereken()` rekent alles opnieuw uit. Wie een hogere score in
het verzoek probeert te plakken, krijgt gewoon de score die bij zijn antwoorden
hoort.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, EmailStr, Field, field_validator

from app.services import readiness_limiet as limiet
from app.services.readiness_scoring import (
    AANTAL_VRAGEN, GELDIGE_CHECKS, bereken, controleer_antwoorden,
)
from app.website import opslag as website_opslag
from app.website import verwerking as website
from app.website.velden import geldige_aanvraag_id

log = logging.getLogger("rhadix.readiness")

router = APIRouter()


class RapportVerzoek(BaseModel):
    """Wat de website mag sturen — en niet meer dan dat.

    `model_config` staat geen onbekende velden toe. Zou de browser alsnog een
    `totaal` of `dimensies` meesturen, dan wordt het verzoek geweigerd in plaats
    van dat die waarden stilzwijgend ergens in terechtkomen.
    """
    model_config = {"extra": "forbid"}

    check: str = Field(description="'data' of 'kikv'")
    antwoorden: list[int] = Field(min_length=AANTAL_VRAGEN, max_length=AANTAL_VRAGEN)
    naam: str = Field(min_length=2, max_length=120)
    organisatie: str = Field(min_length=2, max_length=160)
    email: EmailStr
    website: str = Field(default="", max_length=200,
                         description="honeypot — hoort leeg te blijven")
    # Campagnegegevens uit de URL, voor de opvolging in het CRM. Puur
    # herkomstinformatie; ze raken de uitslag, het rapport of de mail niet.
    utm_source: str = Field(default="", max_length=120)
    utm_medium: str = Field(default="", max_length=120)
    utm_campaign: str = Field(default="", max_length=160)
    utm_content: str = Field(default="", max_length=160)
    utm_term: str = Field(default="", max_length=160)
    # Door de browser per formulier gemaakt; dezelfde id nog eens = dezelfde
    # inzending (dubbelklik, netwerkherhaling), geen tweede aanvraag.
    aanvraag_id: str = Field(default="", max_length=36)

    controleer_aanvraag_id = field_validator("aanvraag_id")(geldige_aanvraag_id)

    def campagne(self) -> dict:
        velden = {
            "utm_source": self.utm_source, "utm_medium": self.utm_medium,
            "utm_campaign": self.utm_campaign, "utm_content": self.utm_content,
            "utm_term": self.utm_term,
        }
        return {k: v.strip() for k, v in velden.items() if v.strip()}

    @field_validator("check")
    @classmethod
    def _bekende_check(cls, v: str) -> str:
        if v not in GELDIGE_CHECKS:
            raise ValueError(f"check moet een van {list(GELDIGE_CHECKS)} zijn")
        return v

    @field_validator("antwoorden")
    @classmethod
    def _geldige_antwoorden(cls, v: list[int]) -> list[int]:
        if any(a < 0 or a > 3 for a in v):
            raise ValueError("elk antwoord is 0, 1, 2 of 3")
        return v

    @field_validator("naam", "organisatie")
    @classmethod
    def _niet_alleen_spaties(cls, v: str) -> str:
        schoon = " ".join(v.split())
        if len(schoon) < 2:
            raise ValueError("te kort")
        return schoon


class RapportAntwoord(BaseModel):
    ok: bool
    totaal: int
    categorie: str
    dimensies: list[dict]
    verzonden: bool
    herhaling: bool = False
    opgeslagen: bool = False
    aanvraag_id: str | None = None
    rapport: str = ""              # verzonden | in_wachtrij | mislukt


@router.post("/report", response_model=RapportAntwoord,
             summary="Stuurt het indicatieve Readiness-rapport per e-mail")
def rapport(verzoek: RapportVerzoek, response: Response) -> RapportAntwoord:
    # 1 — Honeypot. Bots vullen verborgen velden; mensen zien ze niet. Stil
    #     weggooien, zonder te verklappen dat we het doorhebben.
    if verzoek.website.strip():
        log.info("Readiness: honeypot gevuld, verzoek genegeerd")
        response.status_code = status.HTTP_202_ACCEPTED
        return RapportAntwoord(ok=True, totaal=0, categorie="", dimensies=[],
                               verzonden=False)

    # 2 — Invoer nogmaals tegen de canonieke bron houden. Pydantic bewaakt de
    #     vorm; dit bewaakt de inhoud (aantal vragen, toegestane punten).
    try:
        controleer_antwoorden(verzoek.check, verzoek.antwoorden)
    except ValueError as fout:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(fout)) from fout

    # 3 — Begrenzing.
    afdruk = limiet.vingerafdruk(verzoek.email, verzoek.check, verzoek.antwoorden)
    uitslag = bereken(verzoek.check, verzoek.antwoorden)   # 4 — server rekent zelf

    if limiet.is_herhaling(afdruk):
        # Zelfde aanvraag, zelfde antwoorden: het rapport is al onderweg.
        # Geen fout — de bezoeker heeft gewoon twee keer geklikt.
        log.info("Readiness: herhaalde aanvraag binnen het venster, geen tweede mail")
        return RapportAntwoord(
            ok=True, totaal=uitslag.totaal, categorie=uitslag.categorie,
            dimensies=[{"naam": d.naam, "score": d.score} for d in uitslag.dimensies],
            verzonden=False, herhaling=True,
        )

    if limiet.te_veel_voor_adres(verzoek.email):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Er zijn kort na elkaar meerdere rapporten voor dit e-mailadres aangevraagd. "
            "Probeer het later opnieuw, of neem contact met ons op.",
        )

    # 5 — Eerst vastleggen, dan verwerken: rapport aan de bezoeker, melding aan
    #     ons, registratie in het CRM. Elke stap staat los van de andere.
    ontvangst = website.ontvang(
        website.RAPPORT,
        {"check": verzoek.check, "antwoorden": verzoek.antwoorden, "naam": verzoek.naam,
         "organisatie": verzoek.organisatie, "email": verzoek.email,
         "campagne": verzoek.campagne()},
        check_soort=verzoek.check, aanvraag_id=verzoek.aanvraag_id or None,
    )
    stap = website_opslag.MAIL_BEZOEKER
    rapportstand = ("verzonden" if ontvangst.gelukt(stap)
                    else "in_wachtrij" if ontvangst.opgeslagen and ontvangst.openstaand(stap)
                    else "mislukt")

    if not ontvangst.opgeslagen and rapportstand != "verzonden":
        # Niet vastgelegd én niet verstuurd: niets te beloven. De bezoeker moet
        # het opnieuw kunnen proberen.
        log.error("Readiness: rapport niet verzonden en aanvraag niet vastgelegd")
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Het rapport kon nu niet worden verstuurd. Probeer het later opnieuw.",
        )

    if ontvangst.nieuw:
        limiet.leg_vast(afdruk, verzoek.email)

    return RapportAntwoord(
        ok=True, totaal=uitslag.totaal, categorie=uitslag.categorie,
        dimensies=[{"naam": d.naam, "score": d.score} for d in uitslag.dimensies],
        verzonden=rapportstand == "verzonden", herhaling=not ontvangst.nieuw,
        opgeslagen=ontvangst.opgeslagen, aanvraag_id=ontvangst.aanvraag_id,
        rapport=rapportstand,
    )
