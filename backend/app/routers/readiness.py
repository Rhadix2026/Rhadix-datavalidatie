"""
readiness.py — Publiek endpoint voor het Readiness-rapport van Rhoderlanden Groep.

    POST /api/readiness/report

Bewust geïsoleerd
-----------------
Deze router staat volledig los van de rest van Datavalidatie:

* **geen databasesessie** — er is geen `Depends(get_db)` en er wordt geen model
  geïmporteerd. Deze code kan dus niets lezen of schrijven in de
  productiegegevens van Datavalidatie, Rhadix of het CRM;
* **geen authenticatie en geen tenantcontext** — geen `Depends(get_current_user)`,
  geen organisatie, geen rol, geen applicatietoegang;
* **geen opslag** — naam, organisatie en e-mailadres worden gebruikt om twee
  mails te versturen en daarna losgelaten. De begrenzing bewaart alleen hashes
  in het geheugen van het proces.

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
from app.services import readiness_mail as mail
from app.services.readiness_pdf import bouw_pdf
from app.services.readiness_rapport import bouw
from app.services.readiness_scoring import (
    AANTAL_VRAGEN, GELDIGE_CHECKS, bereken, controleer_antwoorden,
)

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

    # 5 — Rapport opbouwen en versturen.
    opzet = bouw(uitslag, naam=verzoek.naam, organisatie=verzoek.organisatie)
    try:
        pdf = bouw_pdf(opzet)
    except Exception:
        log.exception("Readiness: PDF bouwen mislukt")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                            "Het rapport kon niet worden opgemaakt.")

    verzonden = mail.verstuur_rapport(opzet, verzoek.email, pdf)
    if not verzonden:
        # Niets vastleggen: de bezoeker moet het opnieuw kunnen proberen.
        log.error("Readiness: rapport kon niet worden verzonden")
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Het rapport kon nu niet worden verstuurd. Probeer het later opnieuw.",
        )

    # 6 — Signaalmail. Mislukt die, dan blijft het rapport van de bezoeker
    #     gewoon staan; dit mag zijn verzoek niet laten falen.
    if not mail.verstuur_signaal(opzet, verzoek.email):
        log.warning("Readiness: signaalmail naar Rhoderlanden mislukt")

    limiet.leg_vast(afdruk, verzoek.email)

    return RapportAntwoord(
        ok=True, totaal=uitslag.totaal, categorie=uitslag.categorie,
        dimensies=[{"naam": d.naam, "score": d.score} for d in uitslag.dimensies],
        verzonden=True,
    )
