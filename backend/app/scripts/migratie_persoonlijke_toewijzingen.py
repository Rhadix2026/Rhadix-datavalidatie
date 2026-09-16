"""
migratie_persoonlijke_toewijzingen.py — eenmalige datamigratie voor bevinding 8 en 11.

De apps-claim was de VERENIGING van organisatie- en gebruikerstoewijzingen. Omdat een
persoonlijke toewijzing per datamodel altijd onder een organisatietoewijzing hangt, was
die vereniging altijd gelijk aan de organisatietoewijzing — en had persoonlijk intrekken
geen effect. De claim wordt de DOORSNEDE: persoonlijk bepaalt, binnen wat de organisatie
heeft.

Zonder migratie zou die omschakeling iedereen zonder persoonlijke toewijzing in één klap
alle toegang ontnemen. Op productie is dat 11 van de 12 niet-beheerders. Dit script
materialiseert daarom eerst de huidige effectieve toegang als persoonlijke toewijzingen,
zodat er bij de omschakeling voor niemand iets verandert.

DRAAI DIT VÓÓR het activeren van de nieuwe claimregel. Andersom ontstaat er een venster
waarin niemand ergens in kan.

Bewust GEEN startup-hook. Dit script mag precies één keer draaien en daarna op verzoek:
zou het bij elke herstart draaien, dan zou het een bewust ingetrokken persoonlijke
toegang telkens opnieuw toekennen — precies wat het nieuwe model verbiedt.

Gebruik (vanuit backend/):

    python -m app.scripts.migratie_persoonlijke_toewijzingen --dry-run
    python -m app.scripts.migratie_persoonlijke_toewijzingen

RHADIX_ADMIN blijft buiten beschouwing: die krijgt zijn claim niet uit toewijzingen maar
uit alle actieve applicaties, conform de vastgelegde baseline.
"""
from __future__ import annotations

import argparse
import sys
import uuid

from app.database import SessionLocal
from app.models.auth_models import (
    Application,
    TenantApplication,
    User,
    UserApplication,
    UserRole,
)


def claim_oud(db, user: User) -> set[str]:
    """De claim zoals _app_slugs_for hem vóór de wijziging opbouwde: de vereniging."""
    slugs: set[str] = set()
    for ta in db.query(TenantApplication).filter(TenantApplication.tenant_id == user.tenant_id):
        if ta.application:
            slugs.add(ta.application.slug)
    for ua in db.query(UserApplication).filter(UserApplication.user_id == user.id):
        if ua.application:
            slugs.add(ua.application.slug)
    return slugs


def claim_nieuw(db, user: User) -> set[str]:
    """De claim zoals hij ná de wijziging wordt: persoonlijk, binnen de organisatie."""
    beschikbaar = {
        ta.application_id
        for ta in db.query(TenantApplication).filter(TenantApplication.tenant_id == user.tenant_id)
    }
    slugs: set[str] = set()
    for ua in db.query(UserApplication).filter(UserApplication.user_id == user.id):
        if ua.application and ua.application_id in beschikbaar:
            slugs.add(ua.application.slug)
    return slugs


def _te_migreren_gebruikers(db) -> list[User]:
    return [
        u for u in db.query(User).order_by(User.email).all()
        if u.role != UserRole.RHADIX_ADMIN
    ]


def bepaal_plan(db) -> list[tuple[User, list[TenantApplication]]]:
    """Welke persoonlijke toewijzingen ontbreken om de huidige toegang te behouden?"""
    plan = []
    for user in _te_migreren_gebruikers(db):
        heeft = {
            ua.application_id
            for ua in db.query(UserApplication).filter(UserApplication.user_id == user.id)
        }
        ontbreekt = [
            ta for ta in db.query(TenantApplication)
                          .filter(TenantApplication.tenant_id == user.tenant_id).all()
            if ta.application_id not in heeft
        ]
        if ontbreekt:
            plan.append((user, ontbreekt))
    return plan


def voer_uit(db, plan) -> int:
    aantal = 0
    for user, ontbrekend in plan:
        for ta in ontbrekend:
            db.add(UserApplication(
                id=uuid.uuid4(),
                user_id=user.id,
                application_id=ta.application_id,
                tenant_application_id=ta.id,
            ))
            aantal += 1
    if aantal:
        db.commit()
    return aantal


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="toon het plan en de vergelijking, wijzig niets")
    args = parser.parse_args(argv)

    db = SessionLocal()
    try:
        gebruikers = _te_migreren_gebruikers(db)
        voor = {u.id: (u.email, claim_oud(db, u)) for u in gebruikers}

        plan = bepaal_plan(db)
        print(f"Gebruikers in scope (geen RHADIX_ADMIN): {len(gebruikers)}")
        print(f"Gebruikers met ontbrekende toewijzingen : {len(plan)}")
        for user, ontbrekend in plan:
            slugs = sorted(ta.application.slug for ta in ontbrekend if ta.application)
            print(f"   + {user.email:42} {', '.join(slugs)}")

        if args.dry_run:
            print("\n(dry-run: er is niets gewijzigd)")
            return 0

        aantal = voer_uit(db, plan)
        print(f"\nToegevoegde persoonlijke toewijzingen: {aantal}")

        # Vóór/ná-vergelijking: de effectieve claim moet voor iedereen identiek zijn.
        db.expire_all()
        afwijkingen = []
        for user in _te_migreren_gebruikers(db):
            email, oud = voor.get(user.id, (user.email, set()))
            nieuw = claim_nieuw(db, user)
            if oud != nieuw:
                afwijkingen.append((email, sorted(oud), sorted(nieuw)))

        print(f"Gecontroleerde gebruikers: {len(gebruikers)}")
        if afwijkingen:
            print("AFWIJKINGEN GEVONDEN — de migratie is NIET geslaagd:")
            for email, oud, nieuw in afwijkingen:
                print(f"   {email}: vóór {oud} -> ná {nieuw}")
            return 1

        print("Effectieve claim identiek vóór en ná de migratie voor alle gebruikers.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
