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
  * `valid_until` speelt hier bewust GEEN rol. Of een verlopen licentie toegang moet
    blokkeren is bevinding 6, en die keuze is nog niet gemaakt. Deze module kijkt
    uitsluitend naar `is_active` van de licentie. Wordt bevinding 6 later ingevoerd, dan
    is dit de plek om de datumvoorwaarde toe te voegen.
"""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

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


def controleer_ruimte(db: Session, tenant_id) -> None:
    """Blokkeer als er geen plaats meer is binnen de licentie.

    Aan te roepen vóórdat een gebruiker actief wordt: bij het aanmaken van een nieuwe
    gebruiker en bij het opnieuw activeren van een bestaande.

    De melding noemt het aantal en het maximum, en zegt wat er kan gebeuren — een
    blokkade zonder uitweg is voor een beheerder niet te gebruiken.
    """
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
