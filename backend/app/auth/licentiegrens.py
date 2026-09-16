"""
licentiegrens.py — het maximum aantal actieve gebruikers volgens de licentie.

`License.max_users` werd uitsluitend opgeslagen en teruggegeven: geen enkele plek telde
gebruikers of vergeleek ze met de limiet. Een licentie voor één gebruiker stond twee
gebruikers dus niet in de weg (bevinding 7).

Het is een HARDE grens. Een gebruiker wordt geweigerd zodra het aantal ACTIEVE gebruikers
van de organisatie het maximum zou overschrijden — zowel bij het aanmaken als bij het
opnieuw activeren van een bestaand account.

Drie keuzes die hier zijn vastgelegd:

  * Alleen ACTIEVE gebruikers tellen mee. Een gedeactiveerd account houdt geen plaats
    bezet; anders zou een oud account een nieuwe medewerker blokkeren.
  * Bij meerdere licenties geldt de SOM van hun max_users. Draagt één van die licenties
    geen maximum, dan is het geheel onbeperkt — de ruimste licentie wint.
  * De GELDIGHEIDSPERIODE telt mee (bevinding 6). Een licentie die is verlopen of nog niet
    is ingegaan, staat een nieuwe of opnieuw geactiveerde gebruiker in de weg — net als een
    volle licentie, en met een eigen melding. Bestaande actieve gebruikers houden hun
    toegang: deze module wordt alleen aangeroepen vóórdat iemand actief wordt, nooit bij
    inloggen. Deactiveren wordt nooit geblokkeerd.

Twee grenzen van de regel, zodat ze niet per ongeluk anders worden gelezen:

  * Een licentie geldt PER ORGANISATIE en wordt niet geërfd — vastgesteld besluit. Een
    organisatie onder een RSO valt dus niet onder de licentie van die RSO; heeft zij er
    zelf geen, dan is zij onbegrensd.
  * Het aanmaken van een nieuwe ORGANISATIE (`admin.create_tenant`,
    `rso.create_rso_organisation`) maakt meteen een eerste beheerder aan, maar een
    zojuist aangemaakte organisatie heeft nog geen licentie. De controle zou daar altijd
    doorlaten en is er daarom niet ingehaakt — niet vergeten, maar zinloos.
"""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.licentieweergave import (
    TOEKOMSTIG,
    VERLOPEN,
    actieve_licentie,
    licentiestatus,
)
from app.models.auth_models import License, User


def maximum_actieve_gebruikers(db: Session, tenant_id) -> int | None:
    """Het toegestane aantal actieve gebruikers, of None bij onbeperkt.

    Geen licenties, of een licentie zonder maximum, betekent onbeperkt.
    """
    licenties = db.query(License).filter(
        License.tenant_id == tenant_id,
        License.is_active == True,   # noqa: E712
    ).all()

    if not licenties:
        return None
    if any(lic.max_users is None for lic in licenties):
        return None
    return sum(lic.max_users for lic in licenties)


def aantal_actieve_gebruikers(db: Session, tenant_id) -> int:
    return db.query(func.count(User.id)).filter(
        User.tenant_id == tenant_id,
        User.is_active == True,   # noqa: E712
    ).scalar() or 0


def controleer_geldigheid(db: Session, tenant_id) -> None:
    """Blokkeer als de licentie verlopen is of nog niet is ingegaan (bevinding 6).

    Een organisatie ZONDER licentie wordt hier bewust niet geraakt: "geen licentie"
    betekent voorlopig onbeperkt, zonder blokkade. Dat is een besluit, geen omissie.
    """
    lic = actieve_licentie(db, tenant_id)
    if lic is None:
        return

    status = licentiestatus(lic)
    if status == VERLOPEN:
        tot = lic.valid_until.strftime("%d-%m-%Y") if lic.valid_until else ""
        raise HTTPException(
            400,
            f"De licentie van deze organisatie is verlopen op {tot}. Er kan geen gebruiker "
            f"worden toegevoegd of opnieuw geactiveerd totdat de licentie is verlengd. "
            f"Bestaande gebruikers houden gewoon toegang.",
        )
    if status == TOEKOMSTIG:
        vanaf = lic.valid_from.strftime("%d-%m-%Y") if lic.valid_from else ""
        raise HTTPException(
            400,
            f"De licentie van deze organisatie gaat pas in op {vanaf}. Er kan tot die datum "
            f"geen gebruiker worden toegevoegd of opnieuw geactiveerd.",
        )


def controleer_ruimte(db: Session, tenant_id) -> None:
    """Blokkeer als de licentie geen ruimte biedt voor nog een actieve gebruiker.

    Aan te roepen vóórdat een gebruiker actief wordt: bij het aanmaken van een nieuwe
    gebruiker en bij het opnieuw activeren van een bestaande. Twee voorwaarden:

      1. de licentie moet geldig zijn — niet verlopen, niet toekomstig (bevinding 6);
      2. het maximum aantal actieve gebruikers mag niet worden overschreden (bevinding 7).

    De geldigheid gaat voor: een verlopen licentie met ruimte is nog steeds verlopen, en
    die melding is voor een beheerder bruikbaarder dan een telling.

    Elke melding noemt wat er aan de hand is én wat de beheerder kan doen — een blokkade
    zonder uitweg is niet te gebruiken.
    """
    controleer_geldigheid(db, tenant_id)

    maximum = maximum_actieve_gebruikers(db, tenant_id)
    if maximum is None:
        return

    huidig = aantal_actieve_gebruikers(db, tenant_id)
    if huidig >= maximum:
        raise HTTPException(
            400,
            f"Het maximum aantal actieve gebruikers volgens de licentie is bereikt "
            f"({huidig} van {maximum}). Deactiveer eerst een andere gebruiker of vraag "
            f"een ruimere licentie aan.",
        )
