"""
rolbescherming.py — een organisatie mag niet zonder beheerder komen te zitten.

Rollen zijn op drie plekken te wijzigen:

    PATCH /api/org/users/{id}     door een ORG_ADMIN, binnen de eigen organisatie
    PATCH /api/rso/users/{id}     door een RSO_ADMIN, binnen de aangesloten organisaties
    PATCH /api/admin/users/{id}   door een RHADIX_ADMIN, platformbreed

De bescherming hoort bij de ORGANISATIE, niet bij degene die de knop indrukt. Zou hij
alleen op de eerste route gelden, dan is hij met twee klikken te omzeilen via een van de
andere twee. Daarom staat de regel hier, op één plek, en haken alle drie de routes erop
in.

Het patroon zelf bestond al twee keer — `_is_last_active_admin` in routers/admin.py en
`_is_last_active_rso_admin` in routers/rso.py — maar werd uitsluitend toegepast bij
DEACTIVEREN en VERWIJDEREN, niet bij het wijzigen van een rol. Dat gat wordt hiermee
gedicht.
"""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.auth_models import User, UserRole


def _aantal_andere_actieve(db: Session, rol: UserRole, target: User,
                           binnen_tenant: bool) -> int:
    """Hoeveel andere actieve gebruikers met deze rol zijn er nog?"""
    query = db.query(func.count(User.id)).filter(
        User.role == rol,
        User.is_active == True,   # noqa: E712
        User.id != target.id,
    )
    if binnen_tenant:
        query = query.filter(User.tenant_id == target.tenant_id)
    return query.scalar() or 0


def is_laatste_actieve_org_admin(db: Session, target: User) -> bool:
    """Is dit de enige actieve ORG_ADMIN van zijn organisatie?

    Een INACTIEVE beheerder telt niet mee: die is al geen actieve beheerder, dus zijn
    degradatie laat de organisatie niet zonder beheer achter.
    """
    if target.role != UserRole.ORG_ADMIN or not target.is_active:
        return False
    return _aantal_andere_actieve(db, UserRole.ORG_ADMIN, target, binnen_tenant=True) == 0


def is_laatste_actieve_rhadix_admin(db: Session, target: User) -> bool:
    """Is dit de enige actieve RHADIX_ADMIN op het platform?

    Zelfde regel, een niveau hoger. Degradeert iemand de laatste platformbeheerder, dan
    is er niemand meer die dat kan herstellen — ernstiger dan de organisatievariant.
    """
    if target.role != UserRole.RHADIX_ADMIN or not target.is_active:
        return False
    return _aantal_andere_actieve(db, UserRole.RHADIX_ADMIN, target, binnen_tenant=False) == 0


def controleer_rolwijziging(db: Session, target: User, nieuwe_rol: UserRole) -> None:
    """Blokkeer een rolwijziging die de laatste beheerder zou wegnemen.

    Roept HTTPException(400) op met een melding die zegt wát er eerst moet gebeuren —
    een blokkade zonder uitweg is voor een beheerder niet te gebruiken.

    Wordt de rol niet verlaagd (of blijft hij gelijk), dan gebeurt er niets.
    """
    if nieuwe_rol == target.role:
        return

    if is_laatste_actieve_org_admin(db, target):
        raise HTTPException(
            400,
            "Dit is de laatste actieve beheerder van deze organisatie. Wijs eerst een "
            "andere gebruiker als beheerder aan.",
        )

    if is_laatste_actieve_rhadix_admin(db, target):
        raise HTTPException(
            400,
            "Dit is de laatste actieve Rhadix-beheerder. Wijs eerst een andere gebruiker "
            "als Rhadix-beheerder aan.",
        )
