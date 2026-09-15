"""
licentieweergave.py — alleen-lezen weergave van de licentie van een organisatie.

Licenties worden centraal beheerd door RHADIX_ADMIN. Een RSO-beheerder en een
organisatiebeheerder mogen ze wél zien maar niet wijzigen; daarvoor leveren de
RSO- en org-routers een beperktere weergave dan de beheerinterface.

Hier staat ook de ENIGE bepaling van de licentiestatus (bevinding 6). Die stond eerder
los in `routers/dashboard.py`; dat riep twee definities van "verlopen" op. Alles wat een
oordeel over geldigheid nodig heeft, hoort `licentiestatus()` te gebruiken.

Wat hier bewust NIET in zit: `notes` en `created_by` — interne aantekeningen van Rhadix,
niet bedoeld voor de klant.

Een organisatie ZONDER licentie levert een volwaardige regel op met `heeft_licentie=False`.
Dat is met opzet: een organisatie die nergens voorkomt is in een overzicht niet te
onderscheiden van een organisatie die je nog moet inrichten.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.auth_models import License, Tenant, User

# De vier toestanden waarin een organisatie zich kan bevinden.
GEEN_LICENTIE = "geen_licentie"
TOEKOMSTIG    = "toekomstig"
ACTIEF        = "actief"
VERLOPEN      = "verlopen"

# Vanaf hoeveel dagen vóór de vervaldatum we waarschuwen.
WAARSCHUWING_DAGEN = 30


def _als_datum(waarde) -> date | None:
    """Een opgeslagen tijdstip terugbrengen tot een kalenderdatum.

    Geldigheid wordt op DAGNIVEAU beoordeeld, niet op het exacte tijdstip. Een beheerder
    die "geldig tot 31-12-2026" invult bedoelt die dag er nog bij; het invoerveld levert
    middernacht op, dus een vergelijking op tijdstip zou de licentie op de eerste seconde
    van zijn laatste dag al laten verlopen. Datzelfde geldt aan de voorkant: een licentie
    die vandaag ingaat, geldt vandaag.
    """
    if waarde is None:
        return None
    if isinstance(waarde, datetime):
        return waarde.date()
    return waarde


def licentiestatus(lic: License | None, vandaag: date | None = None) -> str:
    """De toestand van een licentie: geen / toekomstig / actief / verlopen.

    Een licentie op inactief telt als GEEN licentie — de beller geeft immers de actieve
    licentie mee, en `actieve_licentie()` levert die al gefilterd aan.
    """
    if lic is None or not lic.is_active:
        return GEEN_LICENTIE

    vandaag = vandaag or datetime.now(timezone.utc).date()
    start   = _als_datum(lic.valid_from)
    eind    = _als_datum(lic.valid_until)

    if start is not None and start > vandaag:
        return TOEKOMSTIG
    if eind is not None and eind < vandaag:
        return VERLOPEN
    return ACTIEF


def statuslabel(status: str, geen_einddatum: bool = False) -> str:
    """De status zoals hij in de schermen komt te staan."""
    if status == GEEN_LICENTIE:
        return "Geen licentie"
    if status == TOEKOMSTIG:
        return "Toekomstig"
    if status == VERLOPEN:
        return "Verlopen"
    return "Actief · geen einddatum" if geen_einddatum else "Actief"


def dagen_tot_verval(lic: License | None, vandaag: date | None = None) -> int | None:
    """Hoeveel dagen een licentie nog loopt; None bij geen einddatum of geen licentie.

    Negatief als hij al verlopen is.
    """
    if lic is None:
        return None
    eind = _als_datum(lic.valid_until)
    if eind is None:
        return None
    return (eind - (vandaag or datetime.now(timezone.utc).date())).days


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

    status = licentiestatus(lic)
    dagen  = dagen_tot_verval(lic)

    regel = {
        "tenant_id":            str(tenant.id),
        "tenant_name":          tenant.name,
        "tenant_type":          (getattr(tenant, "tenant_type", "ORG") or "ORG"),
        "parent_tenant_id":     str(tenant.parent_tenant_id) if getattr(tenant, "parent_tenant_id", None) else None,
        "parent_tenant_name":   ouder.name if ouder else None,
        "actieve_gebruikers":   aantal_actieve_gebruikers(db, tenant.id),
        "heeft_licentie":       lic is not None,
        "status":               status,
        "status_label":         statuslabel(status, geen_einddatum=bool(lic) and lic.valid_until is None),
        "geen_einddatum":       bool(lic) and lic.valid_until is None,
        "dagen_tot_verval":     dagen,
        # Waarschuwen vóórdat het misgaat; een verlopen licentie is geen verrassing meer.
        "verloopt_binnenkort":  status == ACTIEF and dagen is not None and 0 <= dagen <= WAARSCHUWING_DAGEN,
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
