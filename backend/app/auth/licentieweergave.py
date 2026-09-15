"""
licentieweergave.py — alleen-lezen weergave van de licentie van een organisatie.

Licenties worden centraal beheerd door RHADIX_ADMIN. Een RSO-beheerder en een
organisatiebeheerder mogen ze wél zien maar niet wijzigen; daarvoor leveren de
RSO- en org-routers een beperktere weergave dan de beheerinterface.

Wat hier bewust NIET in zit:

  * `notes` en `created_by` — interne aantekeningen van Rhadix, niet bedoeld voor de klant;
  * een oordeel over de geldigheid ("Actief" / "Verlopen"). Wat een verlopen of ontbrekende
    licentie functioneel betekent is bevinding 6 en nog niet besloten. Deze module geeft
    `valid_from` en `valid_until` als feit terug en velt er geen oordeel over.

Een organisatie ZONDER licentie levert een volwaardige regel op met `heeft_licentie=False`.
Dat is met opzet: een organisatie die nergens voorkomt is in een overzicht niet te
onderscheiden van een organisatie die je nog moet inrichten.
"""
from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.auth_models import License, Tenant, User


def actieve_licentie(db: Session, tenant_id) -> License | None:
    """De actieve licentie van de organisatie, of None.

    Er kan er ten hoogste één zijn (afgedwongen bij aanmaken en activeren). Historische
    licenties blijven als inactief bestaan en komen hier dus niet uit.
    """
    return db.query(License).filter(
        License.tenant_id == tenant_id,
        License.is_active == True,   # noqa: E712
    ).order_by(License.created_at.desc()).first()


def aantal_actieve_gebruikers(db: Session, tenant_id) -> int:
    return db.query(func.count(User.id)).filter(
        User.tenant_id == tenant_id,
        User.is_active == True,   # noqa: E712
    ).scalar() or 0


def licentieregel(db: Session, tenant: Tenant) -> dict:
    """Eén regel voor een organisatie, met of zonder licentie."""
    lic = actieve_licentie(db, tenant.id)
    ouder = tenant.parent if getattr(tenant, "parent_tenant_id", None) else None

    regel = {
        "tenant_id":            str(tenant.id),
        "tenant_name":          tenant.name,
        "tenant_type":          (getattr(tenant, "tenant_type", "ORG") or "ORG"),
        "parent_tenant_id":     str(tenant.parent_tenant_id) if getattr(tenant, "parent_tenant_id", None) else None,
        "parent_tenant_name":   ouder.name if ouder else None,
        "actieve_gebruikers":   aantal_actieve_gebruikers(db, tenant.id),
        "heeft_licentie":       lic is not None,
        "licentie_id":          None,
        "licentie_naam":        None,
        "valid_from":           None,
        "valid_until":          None,
        "max_users":            None,
    }
    if lic:
        regel.update({
            "licentie_id":   str(lic.id),
            "licentie_naam": lic.name,
            "valid_from":    lic.valid_from.isoformat()  if lic.valid_from  else None,
            "valid_until":   lic.valid_until.isoformat() if lic.valid_until else None,
            "max_users":     lic.max_users,
        })
    return regel
