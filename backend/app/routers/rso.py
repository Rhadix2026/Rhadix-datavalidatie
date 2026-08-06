"""
rso.py — endpoints voor de RSO-beheerder (samenwerkingsorganisatie).

Een RSO_ADMIN beheert uitsluitend de eigen RSO én de daaronder hangende
organisaties (parent_tenant_id == eigen tenant). Alles is strikt gescoped op die
boom; buiten de eigen boom is niets zichtbaar of wijzigbaar.

Rechten (conform besluit):
  - organisaties aanmaken onder de eigen RSO
  - gebruikers in die organisaties + eigen RSO beheren (aanmaken/bewerken/deactiveren/wachtwoord)
  - apps toewijzen/intrekken aan die organisaties
  - (de)activeren mag; DEFINITIEF verwijderen is voorbehouden aan de RHADIX_ADMIN.

  GET   /api/rso/organisations
  POST  /api/rso/organisations
  GET   /api/rso/organisations/{tid}/users
  POST  /api/rso/organisations/{tid}/users
  PATCH /api/rso/users/{uid}
  PATCH /api/rso/users/{uid}/deactivate
  POST  /api/rso/users/{uid}/reset-password
  GET   /api/rso/organisations/{tid}/applications
  POST  /api/rso/organisations/{tid}/applications
  DELETE/api/rso/organisations/{tid}/applications/{app_id}
"""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_role
from app.auth.security import hash_password, validate_password_strength
from app.database import get_db
from app.models.auth_models import (
    Application,
    Tenant,
    TenantApplication,
    User,
    UserRole,
)
from app.models.models import ValidationRun

router = APIRouter(tags=["RSO"])

# Toegang: RSO-beheerder, of RHADIX_ADMIN (mag alles testen/beheren).
_require_rso = require_role(UserRole.RSO_ADMIN, UserRole.RHADIX_ADMIN)


def _parse_uuid(val: str, label: str = "ID") -> uuid.UUID:
    try:
        return uuid.UUID(val)
    except (ValueError, AttributeError):
        raise HTTPException(400, f"Invalid {label}: {val!r}")


def _rso_root_id(user: User) -> uuid.UUID:
    """De RSO-tenant van de gebruiker (voor RSO_ADMIN = eigen tenant)."""
    return user.tenant_id


def _managed_tenant_ids(db: Session, user: User) -> List[uuid.UUID]:
    """Eigen RSO + alle onderliggende organisaties (kinderen)."""
    root = _rso_root_id(user)
    ids = [root]
    children = db.query(Tenant.id).filter(Tenant.parent_tenant_id == root).all()
    ids.extend(c[0] for c in children)
    return ids


def _require_managed_tenant(db: Session, user: User, tid: uuid.UUID) -> Tenant:
    if tid not in _managed_tenant_ids(db, user):
        raise HTTPException(404, "Organisatie niet gevonden binnen deze samenwerkingsorganisatie")
    t = db.query(Tenant).filter(Tenant.id == tid).first()
    if not t:
        raise HTTPException(404, "Organisatie niet gevonden")
    return t


def _require_managed_user(db: Session, user: User, uid: uuid.UUID) -> User:
    target = db.query(User).filter(User.id == uid).first()
    if not target or target.tenant_id not in _managed_tenant_ids(db, user):
        raise HTTPException(404, "Gebruiker niet gevonden binnen deze samenwerkingsorganisatie")
    return target


def _tenant_dict(db: Session, t: Tenant, root_id: uuid.UUID) -> dict:
    return {
        "id":          str(t.id),
        "slug":        t.slug,
        "name":        t.name,
        "is_active":   t.is_active,
        "tenant_type": getattr(t, "tenant_type", "ORG") or "ORG",
        "is_self":     t.id == root_id,
        "user_count":  db.query(func.count(User.id)).filter(User.tenant_id == t.id).scalar(),
        "scan_count":  db.query(func.count(ValidationRun.id)).filter(ValidationRun.tenant_id == t.id).scalar(),
        "created_at":  t.created_at.isoformat(),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Organisaties
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/organisations")
def list_rso_organisations(
    db: Session = Depends(get_db),
    user: User  = Depends(_require_rso),
):
    """Eigen RSO + onderliggende organisaties."""
    root = _rso_root_id(user)
    rows = (
        db.query(Tenant)
        .filter(Tenant.id.in_(_managed_tenant_ids(db, user)))
        .order_by(Tenant.created_at)
        .all()
    )
    # eigen RSO bovenaan
    rows.sort(key=lambda t: (t.id != root, t.name.lower()))
    return [_tenant_dict(db, t, root) for t in rows]


class CreateRsoOrgRequest(BaseModel):
    name: str
    slug: str
    admin_email: str
    admin_password: str
    admin_full_name: Optional[str] = None


@router.post("/organisations", status_code=201)
def create_rso_organisation(
    body: CreateRsoOrgRequest,
    db:   Session = Depends(get_db),
    user: User    = Depends(_require_rso),
):
    """Nieuwe zorgorganisatie onder de eigen RSO, met eerste ORG_ADMIN."""
    root = _rso_root_id(user)
    if db.query(Tenant).filter(Tenant.slug == body.slug).first():
        raise HTTPException(400, f"Slug '{body.slug}' is al in gebruik")
    if db.query(User).filter(User.email == body.admin_email.lower()).first():
        raise HTTPException(400, f"E-mailadres '{body.admin_email}' is al in gebruik")
    if len(body.admin_password) < 12:
        raise HTTPException(422, "Wachtwoord moet minimaal 12 tekens zijn")

    tenant = Tenant(id=uuid.uuid4(), slug=body.slug, name=body.name, is_active=True,
                    tenant_type="ORG", parent_tenant_id=root)
    db.add(tenant)
    db.flush()
    admin = User(
        id=uuid.uuid4(), tenant_id=tenant.id,
        email=body.admin_email.lower().strip(),
        password_hash=hash_password(body.admin_password),
        full_name=body.admin_full_name, role=UserRole.ORG_ADMIN, is_active=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(tenant)
    return {"id": str(tenant.id), "slug": tenant.slug, "name": tenant.name,
            "admin_user_id": str(admin.id)}


# ═══════════════════════════════════════════════════════════════════════════════
# Gebruikers (binnen de eigen boom)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/organisations/{tenant_id}/users")
def list_rso_org_users(
    tenant_id: str,
    db: Session = Depends(get_db),
    user: User  = Depends(_require_rso),
):
    tid = _parse_uuid(tenant_id, "tenant_id")
    _require_managed_tenant(db, user, tid)
    users = db.query(User).filter(User.tenant_id == tid).order_by(User.created_at).all()
    return [
        {"id": str(u.id), "email": u.email, "full_name": u.full_name,
         "role": u.role.value, "is_active": u.is_active,
         "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
         "created_at": u.created_at.isoformat()}
        for u in users
    ]


class CreateRsoUserRequest(BaseModel):
    email:     str
    password:  str
    full_name: Optional[str] = None
    role:      str = "ORG_USER"


@router.post("/organisations/{tenant_id}/users", status_code=201)
def create_rso_user(
    tenant_id: str,
    body: CreateRsoUserRequest,
    db: Session = Depends(get_db),
    user: User  = Depends(_require_rso),
):
    tid = _parse_uuid(tenant_id, "tenant_id")
    target_tenant = _require_managed_tenant(db, user, tid)
    if db.query(User).filter(User.email == body.email.lower()).first():
        raise HTTPException(400, f"E-mailadres '{body.email}' is al in gebruik")
    try:
        validate_password_strength(body.password)
    except ValueError as exc:
        raise HTTPException(422, str(exc))

    # Toegestane rollen die een RSO-beheerder mag uitdelen.
    is_rso = (getattr(target_tenant, "tenant_type", "ORG") or "ORG").upper() == "RSO"
    allowed = {UserRole.ORG_USER, UserRole.ORG_ADMIN}
    if is_rso:
        allowed.add(UserRole.RSO_ADMIN)   # extra RSO-beheerders binnen de eigen RSO
    try:
        role = UserRole(body.role)
    except ValueError:
        raise HTTPException(422, f"Ongeldige rol: {body.role}")
    if role not in allowed:
        raise HTTPException(403, "Deze rol mag je hier niet toekennen")

    u = User(id=uuid.uuid4(), tenant_id=tid, email=body.email.lower().strip(),
             password_hash=hash_password(body.password), full_name=body.full_name,
             role=role, is_active=True)
    db.add(u)
    db.commit()
    db.refresh(u)
    return {"id": str(u.id), "email": u.email, "role": u.role.value}


class UpdateRsoUserRequest(BaseModel):
    full_name: Optional[str] = None
    role:      Optional[str] = None


@router.patch("/users/{user_id}")
def update_rso_user(
    user_id: str,
    body: UpdateRsoUserRequest,
    db: Session = Depends(get_db),
    user: User  = Depends(_require_rso),
):
    uid = _parse_uuid(user_id, "user_id")
    target = _require_managed_user(db, user, uid)
    if body.full_name is not None:
        target.full_name = body.full_name
    if body.role is not None:
        target_is_rso = (getattr(target.tenant, "tenant_type", "ORG") or "ORG").upper() == "RSO"
        allowed = {UserRole.ORG_USER, UserRole.ORG_ADMIN}
        if target_is_rso:
            allowed.add(UserRole.RSO_ADMIN)
        try:
            new_role = UserRole(body.role)
        except ValueError:
            raise HTTPException(422, f"Ongeldige rol: {body.role}")
        if new_role not in allowed:
            raise HTTPException(403, "Deze rol mag je hier niet toekennen")
        target.role = new_role
    db.commit()
    db.refresh(target)
    return {"id": str(target.id), "email": target.email,
            "full_name": target.full_name, "role": target.role.value}


def _is_last_active_rso_admin(db: Session, root_id: uuid.UUID, target: User) -> bool:
    """True als target de laatste actieve RSO_ADMIN van deze RSO is."""
    if target.role != UserRole.RSO_ADMIN:
        return False
    others = (
        db.query(func.count(User.id))
        .filter(User.tenant_id == root_id, User.role == UserRole.RSO_ADMIN,
                User.is_active == True, User.id != target.id)  # noqa: E712
        .scalar()
    )
    return others == 0


@router.patch("/users/{user_id}/deactivate")
def toggle_rso_user_active(
    user_id: str,
    db: Session = Depends(get_db),
    user: User  = Depends(_require_rso),
):
    uid = _parse_uuid(user_id, "user_id")
    target = _require_managed_user(db, user, uid)
    if target.id == user.id:
        raise HTTPException(400, "Je kunt je eigen account niet deactiveren")
    if target.is_active and _is_last_active_rso_admin(db, _rso_root_id(user), target):
        raise HTTPException(400, "Dit is de laatste actieve RSO-beheerder; deactiveren is niet toegestaan")
    target.is_active = not target.is_active
    db.commit()
    return {"id": str(target.id), "email": target.email, "is_active": target.is_active}


class RsoResetPasswordRequest(BaseModel):
    new_password: str


@router.post("/users/{user_id}/reset-password", status_code=204)
def reset_rso_user_password(
    user_id: str,
    body: RsoResetPasswordRequest,
    db: Session = Depends(get_db),
    user: User  = Depends(_require_rso),
):
    uid = _parse_uuid(user_id, "user_id")
    target = _require_managed_user(db, user, uid)
    try:
        validate_password_strength(body.new_password)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    target.password_hash = hash_password(body.new_password)
    db.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# App-toewijzingen (binnen de eigen boom)
# ═══════════════════════════════════════════════════════════════════════════════

# Toewijsbare producten = de portaal-tegels (Datavalidatie/Uitvraag/Datastation/CRM/
# Reconciliation Engine). De validatie-sub-modules (KIK-V/ZIB/Algemeen Validator) zijn
# interne toegangschakelaars en horen niet in de toewijs-lijst.
PRODUCT_SLUGS = {"datavalidatie", "uitvraag", "datastation", "rhadix-crm",
                 "reconciliation-engine"}


@router.get("/applications")
def list_assignable_apps(
    db: Session = Depends(get_db),
    user: User  = Depends(_require_rso),
):
    """Actieve, toewijsbare producten (de portaal-tegels)."""
    apps = db.query(Application).filter(Application.is_active == True).order_by(  # noqa: E712
        Application.sort_order, Application.name).all()
    return [{"id": str(a.id), "slug": a.slug, "name": a.name}
            for a in apps if a.slug in PRODUCT_SLUGS]


@router.get("/organisations/{tenant_id}/applications")
def list_rso_org_apps(
    tenant_id: str,
    db: Session = Depends(get_db),
    user: User  = Depends(_require_rso),
):
    tid = _parse_uuid(tenant_id, "tenant_id")
    _require_managed_tenant(db, user, tid)
    rows = db.query(TenantApplication).filter(TenantApplication.tenant_id == tid).all()
    return [
        {"id": str(r.id), "tenant_id": str(r.tenant_id),
         "application_id": str(r.application_id),
         "application_slug": r.application.slug if r.application else None,
         "application_name": r.application.name if r.application else None,
         "assigned_at": r.assigned_at.isoformat()}
        for r in rows
    ]


class AssignRsoAppRequest(BaseModel):
    application_id: str


@router.post("/organisations/{tenant_id}/applications", status_code=201)
def assign_rso_app(
    tenant_id: str,
    body: AssignRsoAppRequest,
    db: Session = Depends(get_db),
    user: User  = Depends(_require_rso),
):
    tid = _parse_uuid(tenant_id, "tenant_id")
    _require_managed_tenant(db, user, tid)
    aid = _parse_uuid(body.application_id, "application_id")
    if not db.query(Application).filter(Application.id == aid, Application.is_active == True).first():  # noqa: E712
        raise HTTPException(404, "Applicatie niet gevonden")
    if db.query(TenantApplication).filter(
        TenantApplication.tenant_id == tid, TenantApplication.application_id == aid).first():
        raise HTTPException(400, "Applicatie is al toegewezen aan deze organisatie")
    ta = TenantApplication(id=uuid.uuid4(), tenant_id=tid, application_id=aid,
                           license_id=None, assigned_by_id=user.id)
    db.add(ta)
    db.commit()
    db.refresh(ta)
    return {"id": str(ta.id), "tenant_id": str(ta.tenant_id),
            "application_id": str(ta.application_id),
            "application_name": ta.application.name if ta.application else None}


@router.delete("/organisations/{tenant_id}/applications/{app_id}", status_code=204)
def revoke_rso_app(
    tenant_id: str,
    app_id: str,
    db: Session = Depends(get_db),
    user: User  = Depends(_require_rso),
):
    tid = _parse_uuid(tenant_id, "tenant_id")
    _require_managed_tenant(db, user, tid)
    aid = _parse_uuid(app_id, "app_id")
    ta = db.query(TenantApplication).filter(
        TenantApplication.tenant_id == tid, TenantApplication.application_id == aid).first()
    if not ta:
        raise HTTPException(404, "Toewijzing niet gevonden")
    db.delete(ta)
    db.commit()
