"""
app_toegang.py — wie tot welke applicatie toegang heeft.

Eén plek voor de regel, omdat hij eerder op twee plekken stond (de claim in
`auth/router.py` en de uploadpoort in `routers/validate.py`) en daar uit elkaar was
gelopen.

Het model, in twee lagen:

    TenantApplication  — welke applicaties de ORGANISATIE beschikbaar heeft
    UserApplication    — tot welke daarvan een GEBRUIKER daadwerkelijk toegang heeft

De claim is de DOORSNEDE van die twee. Voorheen was het de vereniging, en omdat een
persoonlijke toewijzing per datamodel altijd onder een organisatietoewijzing hangt
(`UserApplication.tenant_application_id` is NOT NULL), was die vereniging altijd gelijk
aan de organisatietoewijzing. Persoonlijk intrekken had daardoor geen effect — bevinding
8 en 11 uit het bevindingenregister.

De doorsnede is strikt genomen overbodig: de foreign key garandeert de deelverzameling
al. Hij staat er expliciet om twee redenen. Hij maakt de regel leesbaar, en hij vangt
datadrift af — een persoonlijke toewijzing die om welke reden dan ook buiten de
organisatie zou vallen, geeft nooit toegang.

RHADIX_ADMIN blijft ongewijzigd: die krijgt alle ACTIEVE applicaties, ongeacht wat er is
toegewezen. Dat is de vastgelegde baseline (zie ~/Developer/CLAUDE.md): er is precies één
plek waar toegang wordt bepaald, en de resource-apps kennen bewust geen rol-bypass.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.auth_models import (
    Application,
    TenantApplication,
    User,
    UserApplication,
    UserRole,
)


def beschikbare_app_ids(db: Session, tenant_id) -> set:
    """Applicaties die aan de organisatie zijn toegewezen."""
    return {
        ta.application_id
        for ta in db.query(TenantApplication).filter(TenantApplication.tenant_id == tenant_id).all()
    }


def app_slugs_voor(user: User, db: Session) -> list[str]:
    """De apps-claim van deze gebruiker.

    RHADIX_ADMIN → alle actieve applicaties.
    Anders       → de persoonlijke toewijzingen, beperkt tot wat de organisatie heeft
                   en tot applicaties die actief zijn.
    """
    if user.role == UserRole.RHADIX_ADMIN:
        return [a.slug for a in db.query(Application).filter(Application.is_active == True).all()]

    beschikbaar = beschikbare_app_ids(db, user.tenant_id)
    if not beschikbaar:
        return []

    slugs = set()
    for ua in db.query(UserApplication).filter(UserApplication.user_id == user.id).all():
        if ua.application_id not in beschikbaar:
            continue          # buiten de organisatie: nooit toegang
        app = ua.application
        if app is not None and app.is_active:
            slugs.add(app.slug)
    return sorted(slugs)


def heeft_toegang(user: User, slugs: list[str], db: Session) -> bool:
    """Heeft deze gebruiker toegang tot minstens één van deze applicaties?

    Zelfde regel als `app_slugs_voor`, zodat de uploadpoort van Datavalidatie niet
    opnieuw uit de pas kan lopen met de claim.
    """
    if user.role == UserRole.RHADIX_ADMIN:
        return True
    return bool(set(slugs) & set(app_slugs_voor(user, db)))


def wijs_organisatie_apps_toe(db: Session, user: User) -> int:
    """Geef deze gebruiker de applicaties die zijn organisatie beschikbaar heeft.

    Gebruikt bij het aanmaken van een gebruiker en bij het toewijzen van een applicatie
    aan een organisatie. Bewust NIET als periodieke synchronisatie: een bewust
    ingetrokken persoonlijke toegang mag nooit vanzelf terugkomen. Deze functie wordt
    dan ook alleen aangeroepen op het moment dat een beheerder een gebruiker of een
    organisatietoewijzing aanmaakt.

    Geeft het aantal toegevoegde toewijzingen terug.
    """
    import uuid

    if user.role == UserRole.RHADIX_ADMIN:
        return 0                      # claim komt niet uit toewijzingen

    heeft = {
        ua.application_id
        for ua in db.query(UserApplication).filter(UserApplication.user_id == user.id).all()
    }
    aantal = 0
    for ta in db.query(TenantApplication).filter(TenantApplication.tenant_id == user.tenant_id).all():
        if ta.application_id in heeft:
            continue
        db.add(UserApplication(
            id=uuid.uuid4(),
            user_id=user.id,
            application_id=ta.application_id,
            tenant_application_id=ta.id,
        ))
        aantal += 1
    return aantal


def wijs_toe_aan_bestaande_gebruikers(db: Session, tenant_application: TenantApplication) -> int:
    """Kent een zojuist toegewezen applicatie toe aan de huidige gebruikers van de organisatie.

    Het standaardgedrag bij een nieuwe organisatietoewijzing: de applicatie wordt
    beschikbaar én meteen bruikbaar, zoals beheerders gewend zijn. De beheerder kan
    hiervan afwijken; daarna is intrekken per gebruiker mogelijk en heeft dat effect.
    """
    import uuid

    aantal = 0
    gebruikers = db.query(User).filter(User.tenant_id == tenant_application.tenant_id).all()
    for user in gebruikers:
        if user.role == UserRole.RHADIX_ADMIN:
            continue
        bestaat = db.query(UserApplication).filter(
            UserApplication.user_id == user.id,
            UserApplication.application_id == tenant_application.application_id,
        ).first()
        if bestaat:
            continue
        db.add(UserApplication(
            id=uuid.uuid4(),
            user_id=user.id,
            application_id=tenant_application.application_id,
            tenant_application_id=tenant_application.id,
        ))
        aantal += 1
    return aantal
