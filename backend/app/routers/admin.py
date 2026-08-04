"""
admin.py — RHADIX_ADMIN-only endpoints.

Phase 1:
  GET  /api/admin/tenants/              — list all tenants
  POST /api/admin/tenants/              — create tenant + initial admin user
  GET  /api/admin/tenants/{id}/users    — list users for a tenant
  GET  /api/admin/stats                 — platform statistics

Phase 2:
  GET    /api/admin/applications/                      — list all applications
  POST   /api/admin/applications/                      — create application
  PATCH  /api/admin/applications/{id}                  — update application
  GET    /api/admin/licenses/                          — list all licenses
  GET    /api/admin/licenses/{tenant_id}               — licenses for a tenant
  POST   /api/admin/licenses/                          — create license
  PATCH  /api/admin/licenses/{id}                      — update license
  GET    /api/admin/tenants/{id}/applications          — list apps assigned to tenant
  POST   /api/admin/tenants/{id}/applications          — assign app to tenant
  DELETE /api/admin/tenants/{id}/applications/{app_id} — revoke app from tenant

User management (Phase 3+):
  PATCH  /api/admin/users/{user_id}/deactivate       — toggle is_active
  DELETE /api/admin/users/{user_id}                  — delete user
  POST   /api/admin/users/{user_id}/reset-password   — admin resets user password
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_role
from app.auth.schemas import (
    AssignTenantAppRequest,
    CreateApplicationRequest,
    CreateLicenseRequest,
    TenantApplicationResponse,
    UpdateApplicationRequest,
    UpdateLicenseRequest,
)
from app.audit import ADMIN_ACTION, USER_CREATED, USER_UPDATED, audit_log
from app.auth.security import hash_password, validate_password_strength
from app.database import get_db
from app.models.auth_models import (
    Application,
    License,
    Tenant,
    TenantApplication,
    TenantBranding,
    User,
    UserRole,
)
from app.models.models import ValidationRun
from app.models.task_models import Task

router = APIRouter(tags=["Admin"])

# ─── helpers ──────────────────────────────────────────────────────────────────

def _parse_uuid(val: str, label: str = "ID") -> uuid.UUID:
    try:
        return uuid.UUID(val)
    except (ValueError, AttributeError):
        raise HTTPException(400, f"Invalid {label}: {val!r}")


def _is_last_active_admin(db: Session, user: User) -> bool:
    """True als deze gebruiker de laatste actieve RHADIX_ADMIN op het platform is."""
    if user.role != UserRole.RHADIX_ADMIN:
        return False
    others = (
        db.query(func.count(User.id))
        .filter(
            User.role == UserRole.RHADIX_ADMIN,
            User.is_active == True,   # noqa: E712
            User.id != user.id,
        )
        .scalar()
    )
    return others == 0


def _tenant_impact(db: Session, tid: uuid.UUID) -> dict:
    """Tel wat er aan een organisatie hangt (voor impact-overzicht/verwijderen)."""
    return {
        "user_count":    db.query(func.count(User.id)).filter(User.tenant_id == tid).scalar(),
        "active_users":  db.query(func.count(User.id)).filter(User.tenant_id == tid, User.is_active == True).scalar(),  # noqa: E712
        "license_count": db.query(func.count(License.id)).filter(License.tenant_id == tid).scalar(),
        "app_count":     db.query(func.count(TenantApplication.id)).filter(TenantApplication.tenant_id == tid).scalar(),
        "task_count":    db.query(func.count(Task.id)).filter(Task.tenant_id == tid).scalar(),
        "scan_count":    db.query(func.count(ValidationRun.id)).filter(ValidationRun.tenant_id == tid).scalar(),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Tenant management  (Phase 1)
# ═══════════════════════════════════════════════════════════════════════════════

class CreateTenantRequest(BaseModel):
    name: str
    slug: str
    admin_email: str
    admin_password: str
    admin_full_name: Optional[str] = None
    tenant_type: str = "ORG"                 # 'ORG' of 'RSO'
    parent_tenant_id: Optional[str] = None   # optioneel: onder welke RSO valt deze organisatie


@router.get("/tenants/")
def list_tenants(
    db: Session = Depends(get_db),
    _: User     = Depends(require_role(UserRole.RHADIX_ADMIN)),
):
    """Return all tenants with basic stats."""
    tenants = db.query(Tenant).order_by(Tenant.created_at.desc()).all()
    result  = []
    for t in tenants:
        user_count = db.query(func.count(User.id)).filter(User.tenant_id == t.id).scalar()
        scan_count = db.query(func.count(ValidationRun.id)).filter(ValidationRun.tenant_id == t.id).scalar()
        result.append({
            "id":         str(t.id),
            "slug":       t.slug,
            "name":       t.name,
            "is_active":  t.is_active,
            "tenant_type":      getattr(t, "tenant_type", "ORG") or "ORG",
            "parent_tenant_id": str(t.parent_tenant_id) if getattr(t, "parent_tenant_id", None) else None,
            "created_at": t.created_at.isoformat(),
            "user_count": user_count,
            "scan_count": scan_count,
        })
    return result


@router.post("/tenants/", status_code=201)
def create_tenant(
    body: CreateTenantRequest,
    db:   Session = Depends(get_db),
    _:    User    = Depends(require_role(UserRole.RHADIX_ADMIN)),
):
    """Create a new tenant and its first ORG_ADMIN user."""
    if db.query(Tenant).filter(Tenant.slug == body.slug).first():
        raise HTTPException(400, f"Slug '{body.slug}' is already taken")
    if db.query(User).filter(User.email == body.admin_email.lower()).first():
        raise HTTPException(400, f"Email '{body.admin_email}' is already in use")
    if len(body.admin_password) < 12:
        raise HTTPException(422, "Password must be at least 12 characters")

    ttype = (body.tenant_type or "ORG").upper()
    if ttype not in ("ORG", "RSO"):
        raise HTTPException(422, f"Invalid tenant_type: {body.tenant_type}")

    parent_id = None
    if body.parent_tenant_id:
        parent_id = _parse_uuid(body.parent_tenant_id, "parent_tenant_id")
        parent = db.query(Tenant).filter(Tenant.id == parent_id).first()
        if not parent:
            raise HTTPException(404, "Parent (RSO) not found")
        if (getattr(parent, "tenant_type", "ORG") or "ORG").upper() != "RSO":
            raise HTTPException(422, "Parent must be a samenwerkingsorganisatie (RSO)")

    tenant = Tenant(id=uuid.uuid4(), slug=body.slug, name=body.name, is_active=True,
                    tenant_type=ttype, parent_tenant_id=parent_id)
    db.add(tenant)
    db.flush()   # get tenant.id before creating user

    # Een RSO krijgt een RSO_ADMIN als eerste beheerder; een organisatie een ORG_ADMIN.
    admin_role = UserRole.RSO_ADMIN if ttype == "RSO" else UserRole.ORG_ADMIN
    user = User(
        id            = uuid.uuid4(),
        tenant_id     = tenant.id,
        email         = body.admin_email.lower().strip(),
        password_hash = hash_password(body.admin_password),
        full_name     = body.admin_full_name,
        role          = admin_role,
        is_active     = True,
    )
    db.add(user)
    db.commit()
    db.refresh(tenant)
    return {"id": str(tenant.id), "slug": tenant.slug, "name": tenant.name,
            "tenant_type": ttype, "admin_user_id": str(user.id), "admin_role": admin_role.value}


@router.get("/tenants/{tenant_id}/users")
def list_tenant_users(
    tenant_id: str,
    db: Session  = Depends(get_db),
    _: User      = Depends(require_role(UserRole.RHADIX_ADMIN)),
):
    tid   = _parse_uuid(tenant_id, "tenant_id")
    users = db.query(User).filter(User.tenant_id == tid).order_by(User.created_at).all()
    return [
        {
            "id":           str(u.id),
            "email":        u.email,
            "full_name":    u.full_name,
            "role":         u.role.value,
            "is_active":    u.is_active,
            "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
            "created_at":   u.created_at.isoformat(),
        }
        for u in users
    ]


@router.get("/tenants/{tenant_id}/impact")
def tenant_impact(
    tenant_id: str,
    db: Session  = Depends(get_db),
    _: User      = Depends(require_role(UserRole.RHADIX_ADMIN)),
):
    """Wat hangt er aan deze organisatie — te tonen vóór deactiveren/verwijderen."""
    tid = _parse_uuid(tenant_id, "tenant_id")
    tenant = db.query(Tenant).filter(Tenant.id == tid).first()
    if not tenant:
        raise HTTPException(404, "Tenant not found")
    return {"id": str(tenant.id), "name": tenant.name, "slug": tenant.slug,
            "is_active": tenant.is_active, **_tenant_impact(db, tid)}


class TenantDeactivateRequest(BaseModel):
    is_active: bool


@router.patch("/tenants/{tenant_id}/deactivate")
def admin_toggle_tenant_active(
    tenant_id: str,
    body:         TenantDeactivateRequest,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(require_role(UserRole.RHADIX_ADMIN)),
):
    """Organisatie (de)activeren — omkeerbaar. Zet ook alle gebruikers mee op dezelfde status."""
    tid = _parse_uuid(tenant_id, "tenant_id")
    tenant = db.query(Tenant).filter(Tenant.id == tid).first()
    if not tenant:
        raise HTTPException(404, "Tenant not found")
    if current_user.tenant_id == tid:
        raise HTTPException(400, "Je kunt je eigen organisatie niet deactiveren")

    tenant.is_active = body.is_active
    db.query(User).filter(User.tenant_id == tid).update(
        {User.is_active: body.is_active}, synchronize_session=False
    )
    db.commit()
    audit_log(ADMIN_ACTION, action="tenant_deactivate", tenant_id=str(tid),
              tenant_name=tenant.name, is_active=body.is_active, by=str(current_user.id))
    return {"id": str(tenant.id), "name": tenant.name, "is_active": tenant.is_active}


class TenantDeleteRequest(BaseModel):
    confirm_name: str


@router.delete("/tenants/{tenant_id}")
def admin_delete_tenant(
    tenant_id: str,
    body:         TenantDeleteRequest,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(require_role(UserRole.RHADIX_ADMIN)),
):
    """
    Organisatie definitief verwijderen, inclusief gebruikers, licenties,
    app-toewijzingen en taken (cascade). Scans (ValidationRun) blijven bewaard
    maar worden losgekoppeld (audittrail). Vereist bevestiging via organisatienaam.
    """
    tid = _parse_uuid(tenant_id, "tenant_id")
    tenant = db.query(Tenant).filter(Tenant.id == tid).first()
    if not tenant:
        raise HTTPException(404, "Tenant not found")
    if current_user.tenant_id == tid:
        raise HTTPException(400, "Je kunt je eigen organisatie niet verwijderen")
    if (body.confirm_name or "").strip() != tenant.name:
        raise HTTPException(400, "Bevestiging komt niet overeen met de organisatienaam")

    impact = _tenant_impact(db, tid)
    name   = tenant.name
    db.delete(tenant)   # ORM-cascade: users, licenties, app-toewijzingen; DB-cascade: taken
    db.commit()
    audit_log(ADMIN_ACTION, action="tenant_delete", tenant_id=str(tid),
              tenant_name=name, deleted=impact, by=str(current_user.id))
    return {"deleted": True, "id": str(tid), "name": name, "removed": impact}


# ═══════════════════════════════════════════════════════════════════════════════
# Look-and-feel / branding per tenant  (RHADIX_ADMIN)
# ═══════════════════════════════════════════════════════════════════════════════

import re as _re
_HEX = _re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
_MAX_LOGO_BYTES = 512 * 1024   # 512 KB
_ALLOWED_LOGO_MIME = {"image/png", "image/jpeg", "image/svg+xml", "image/webp", "image/gif"}


class BrandingRequest(BaseModel):
    preset:        Optional[str] = None
    primary_color: Optional[str] = None
    accent_color:  Optional[str] = None
    wordmark:      Optional[str] = None


def _branding_dict(b: TenantBranding) -> dict:
    has_logo = b.logo_data is not None
    return {
        "tenant_id":     str(b.tenant_id),
        "preset":        b.preset,
        "primary_color": b.primary_color,
        "accent_color":  b.accent_color,
        "wordmark":      b.wordmark,
        "has_logo":      has_logo,
        "logo_version":  int(b.updated_at.timestamp()) if (has_logo and b.updated_at) else None,
        "updated_at":    b.updated_at.isoformat() if b.updated_at else None,
    }


@router.get("/tenants/{tenant_id}/branding")
def get_tenant_branding(
    tenant_id: str,
    db: Session = Depends(get_db),
    _: User     = Depends(require_role(UserRole.RHADIX_ADMIN)),
):
    tid = _parse_uuid(tenant_id, "tenant_id")
    if not db.query(Tenant).filter(Tenant.id == tid).first():
        raise HTTPException(404, "Tenant not found")
    b = db.query(TenantBranding).filter(TenantBranding.tenant_id == tid).first()
    if not b:
        return {"tenant_id": str(tid), "preset": None, "primary_color": None,
                "accent_color": None, "wordmark": None, "has_logo": False,
                "logo_version": None, "updated_at": None}
    return _branding_dict(b)


@router.put("/tenants/{tenant_id}/branding")
def put_tenant_branding(
    tenant_id: str,
    body: BrandingRequest,
    db: Session = Depends(get_db),
    _: User     = Depends(require_role(UserRole.RHADIX_ADMIN)),
):
    tid = _parse_uuid(tenant_id, "tenant_id")
    if not db.query(Tenant).filter(Tenant.id == tid).first():
        raise HTTPException(404, "Tenant not found")
    for col in (body.primary_color, body.accent_color):
        if col and not _HEX.match(col):
            raise HTTPException(422, f"Ongeldige kleurcode: {col}")

    b = db.query(TenantBranding).filter(TenantBranding.tenant_id == tid).first()
    if not b:
        b = TenantBranding(tenant_id=tid)
        db.add(b)
    b.preset        = body.preset
    b.primary_color = body.primary_color
    b.accent_color  = body.accent_color
    b.wordmark      = (body.wordmark or None)
    db.commit()
    db.refresh(b)
    return _branding_dict(b)


@router.delete("/tenants/{tenant_id}/branding", status_code=204)
def delete_tenant_branding(
    tenant_id: str,
    db: Session = Depends(get_db),
    _: User     = Depends(require_role(UserRole.RHADIX_ADMIN)),
):
    """Branding volledig wissen → tenant erft weer van RSO/platform."""
    tid = _parse_uuid(tenant_id, "tenant_id")
    b = db.query(TenantBranding).filter(TenantBranding.tenant_id == tid).first()
    if b:
        db.delete(b)
        db.commit()


@router.post("/tenants/{tenant_id}/branding/logo")
def upload_tenant_logo(
    tenant_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: User     = Depends(require_role(UserRole.RHADIX_ADMIN)),
):
    tid = _parse_uuid(tenant_id, "tenant_id")
    if not db.query(Tenant).filter(Tenant.id == tid).first():
        raise HTTPException(404, "Tenant not found")
    mime = (file.content_type or "").lower()
    if mime not in _ALLOWED_LOGO_MIME:
        raise HTTPException(422, f"Bestandstype niet toegestaan: {mime or 'onbekend'}")
    data = file.file.read(_MAX_LOGO_BYTES + 1)
    if len(data) > _MAX_LOGO_BYTES:
        raise HTTPException(422, "Logo is te groot (max. 512 KB)")
    if not data:
        raise HTTPException(422, "Leeg bestand")

    b = db.query(TenantBranding).filter(TenantBranding.tenant_id == tid).first()
    if not b:
        b = TenantBranding(tenant_id=tid)
        db.add(b)
    b.logo_data = data
    b.logo_mime = mime
    db.commit()
    db.refresh(b)
    return _branding_dict(b)


@router.delete("/tenants/{tenant_id}/branding/logo", status_code=204)
def delete_tenant_logo(
    tenant_id: str,
    db: Session = Depends(get_db),
    _: User     = Depends(require_role(UserRole.RHADIX_ADMIN)),
):
    tid = _parse_uuid(tenant_id, "tenant_id")
    b = db.query(TenantBranding).filter(TenantBranding.tenant_id == tid).first()
    if b and b.logo_data is not None:
        b.logo_data = None
        b.logo_mime = None
        db.commit()


class AdminCreateUserRequest(BaseModel):
    email:     str
    password:  str
    full_name: Optional[str] = None
    role:      str = "ORG_USER"


@router.post("/tenants/{tenant_id}/users", status_code=201)
def admin_create_user(
    tenant_id: str,
    body:      AdminCreateUserRequest,
    db:        Session = Depends(get_db),
    _:         User    = Depends(require_role(UserRole.RHADIX_ADMIN)),
):
    """RHADIX_ADMIN maakt een nieuwe gebruiker aan voor willekeurige tenant."""
    tid = _parse_uuid(tenant_id, "tenant_id")
    if not db.query(Tenant).filter(Tenant.id == tid).first():
        raise HTTPException(404, "Tenant not found")
    if db.query(User).filter(User.email == body.email.lower()).first():
        raise HTTPException(400, f"Email '{body.email}' is already in use")
    try:
        validate_password_strength(body.password)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    try:
        role = UserRole(body.role)
    except ValueError:
        raise HTTPException(422, f"Invalid role: {body.role}")

    user = User(
        id            = uuid.uuid4(),
        tenant_id     = tid,
        email         = body.email.lower().strip(),
        password_hash = hash_password(body.password),
        full_name     = body.full_name,
        role          = role,
        is_active     = True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    audit_log(USER_CREATED, user_id=str(user.id), email=user.email,
              tenant_id=str(tid), role=role.value, created_by="RHADIX_ADMIN")
    return {"id": str(user.id), "email": user.email, "role": user.role.value}


class AdminUpdateUserRequest(BaseModel):
    full_name: Optional[str] = None
    role:      Optional[str] = None


@router.patch("/users/{user_id}")
def admin_update_user(
    user_id: str,
    body:    AdminUpdateUserRequest,
    db:      Session = Depends(get_db),
    _:       User    = Depends(require_role(UserRole.RHADIX_ADMIN)),
):
    """RHADIX_ADMIN wijzigt naam en/of rol van een gebruiker."""
    uid  = _parse_uuid(user_id, "user_id")
    user = db.query(User).filter(User.id == uid).first()
    if not user:
        raise HTTPException(404, "User not found")
    if body.full_name is not None:
        user.full_name = body.full_name
    if body.role is not None:
        try:
            user.role = UserRole(body.role)
        except ValueError:
            raise HTTPException(422, f"Invalid role: {body.role}")
    db.commit()
    db.refresh(user)
    audit_log(USER_UPDATED, user_id=str(user.id), email=user.email,
              changes={"full_name": body.full_name, "role": body.role})
    return {"id": str(user.id), "email": user.email, "full_name": user.full_name, "role": user.role.value}


@router.get("/stats")
def platform_stats(
    db: Session = Depends(get_db),
    _: User     = Depends(require_role(UserRole.RHADIX_ADMIN)),
):
    """High-level platform statistics for the admin dashboard."""
    total_tenants  = db.query(func.count(Tenant.id)).scalar()
    active_tenants = db.query(func.count(Tenant.id)).filter(Tenant.is_active == True).scalar()
    total_users    = db.query(func.count(User.id)).scalar()
    total_scans    = db.query(func.count(ValidationRun.id)).scalar()
    avg_score      = db.query(func.avg(ValidationRun.score)).scalar()
    tenants_recent = (
        db.query(Tenant)
        .filter(Tenant.is_active == True)
        .order_by(Tenant.created_at.desc())
        .limit(10)
        .all()
    )
    return {
        "total_tenants":  total_tenants,
        "active_tenants": active_tenants,
        "total_users":    total_users,
        "total_scans":    total_scans,
        "avg_score":      round(float(avg_score), 1) if avg_score else 0.0,
        "recent_tenants": [
            {"id": str(t.id), "name": t.name, "slug": t.slug, "created_at": t.created_at.isoformat()}
            for t in tenants_recent
        ],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Applications  (Phase 2)
# ═══════════════════════════════════════════════════════════════════════════════

def _app_to_dict(app: Application) -> dict:
    return {
        "id":          str(app.id),
        "slug":        app.slug,
        "name":        app.name,
        "description": app.description,
        "is_active":   app.is_active,
        "sort_order":  app.sort_order,
        "created_at":  app.created_at.isoformat(),
    }


@router.get("/applications/")
def list_applications(
    db: Session = Depends(get_db),
    _: User     = Depends(require_role(UserRole.RHADIX_ADMIN)),
):
    apps = db.query(Application).order_by(Application.sort_order, Application.name).all()
    return [_app_to_dict(a) for a in apps]


@router.post("/applications/", status_code=201)
def create_application(
    body: CreateApplicationRequest,
    db:   Session = Depends(get_db),
    _:    User    = Depends(require_role(UserRole.RHADIX_ADMIN)),
):
    if db.query(Application).filter(Application.slug == body.slug).first():
        raise HTTPException(400, f"Application slug '{body.slug}' already exists")
    app = Application(
        id          = uuid.uuid4(),
        slug        = body.slug,
        name        = body.name,
        description = body.description,
        sort_order  = body.sort_order,
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    return _app_to_dict(app)


@router.patch("/applications/{app_id}")
def update_application(
    app_id: str,
    body:   UpdateApplicationRequest,
    db:     Session = Depends(get_db),
    _:      User    = Depends(require_role(UserRole.RHADIX_ADMIN)),
):
    aid = _parse_uuid(app_id, "app_id")
    app = db.query(Application).filter(Application.id == aid).first()
    if not app:
        raise HTTPException(404, "Application not found")
    if body.name        is not None: app.name        = body.name
    if body.description is not None: app.description = body.description
    if body.is_active   is not None: app.is_active   = body.is_active
    if body.sort_order  is not None: app.sort_order  = body.sort_order
    db.commit()
    db.refresh(app)
    return _app_to_dict(app)


# ═══════════════════════════════════════════════════════════════════════════════
# Licenses  (Phase 2)
# ═══════════════════════════════════════════════════════════════════════════════

def _license_to_dict(lic: License, db: Session) -> dict:
    app_slugs = [
        ta.application.slug
        for ta in db.query(TenantApplication)
            .filter(TenantApplication.license_id == lic.id)
            .all()
        if ta.application
    ]
    return {
        "id":          str(lic.id),
        "tenant_id":   str(lic.tenant_id),
        "name":        lic.name,
        "valid_from":  lic.valid_from.isoformat()  if lic.valid_from  else None,
        "valid_until": lic.valid_until.isoformat() if lic.valid_until else None,
        "max_users":   lic.max_users,
        "notes":       lic.notes,
        "is_active":   lic.is_active,
        "created_at":  lic.created_at.isoformat(),
        "app_slugs":   app_slugs,
    }


@router.get("/licenses/")
def list_all_licenses(
    db: Session = Depends(get_db),
    _: User     = Depends(require_role(UserRole.RHADIX_ADMIN)),
):
    licenses = db.query(License).order_by(License.created_at.desc()).all()
    return [_license_to_dict(l, db) for l in licenses]


@router.get("/licenses/tenant/{tenant_id}")
def list_tenant_licenses(
    tenant_id: str,
    db:  Session = Depends(get_db),
    _:   User    = Depends(require_role(UserRole.RHADIX_ADMIN)),
):
    tid = _parse_uuid(tenant_id, "tenant_id")
    licenses = db.query(License).filter(License.tenant_id == tid).order_by(License.created_at.desc()).all()
    return [_license_to_dict(l, db) for l in licenses]


@router.post("/licenses/", status_code=201)
def create_license(
    body:         CreateLicenseRequest,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(require_role(UserRole.RHADIX_ADMIN)),
):
    tid = _parse_uuid(body.tenant_id, "tenant_id")
    if not db.query(Tenant).filter(Tenant.id == tid).first():
        raise HTTPException(404, "Tenant not found")

    kwargs = dict(
        id            = uuid.uuid4(),
        tenant_id     = tid,
        name          = body.name,
        valid_until   = body.valid_until,
        max_users     = body.max_users,
        notes         = body.notes,
        created_by_id = current_user.id,
    )
    if body.valid_from:
        kwargs["valid_from"] = body.valid_from

    lic = License(**kwargs)
    db.add(lic)
    db.commit()
    db.refresh(lic)
    return _license_to_dict(lic, db)


@router.patch("/licenses/{license_id}")
def update_license(
    license_id: str,
    body:       UpdateLicenseRequest,
    db:         Session = Depends(get_db),
    _:          User    = Depends(require_role(UserRole.RHADIX_ADMIN)),
):
    lid = _parse_uuid(license_id, "license_id")
    lic = db.query(License).filter(License.id == lid).first()
    if not lic:
        raise HTTPException(404, "License not found")
    if body.name        is not None: lic.name        = body.name
    if body.valid_from  is not None: lic.valid_from  = body.valid_from
    if body.valid_until is not None: lic.valid_until = body.valid_until
    if body.max_users   is not None: lic.max_users   = body.max_users
    if body.notes       is not None: lic.notes       = body.notes
    if body.is_active   is not None: lic.is_active   = body.is_active
    db.commit()
    db.refresh(lic)
    return _license_to_dict(lic, db)


# ═══════════════════════════════════════════════════════════════════════════════
# Tenant ↔ Application assignments  (Phase 2)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/tenants/{tenant_id}/applications")
def list_tenant_app_assignments(
    tenant_id: str,
    db:  Session = Depends(get_db),
    _:   User    = Depends(require_role(UserRole.RHADIX_ADMIN)),
):
    tid = _parse_uuid(tenant_id, "tenant_id")
    rows = (
        db.query(TenantApplication)
        .filter(TenantApplication.tenant_id == tid)
        .all()
    )
    return [
        {
            "id":               str(r.id),
            "tenant_id":        str(r.tenant_id),
            "application_id":   str(r.application_id),
            "application_slug": r.application.slug  if r.application else None,
            "application_name": r.application.name  if r.application else None,
            "license_id":       str(r.license_id) if r.license_id else None,
            "assigned_at":      r.assigned_at.isoformat(),
        }
        for r in rows
    ]


@router.post("/tenants/{tenant_id}/applications", status_code=201)
def assign_app_to_tenant(
    tenant_id:    str,
    body:         AssignTenantAppRequest,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(require_role(UserRole.RHADIX_ADMIN)),
):
    tid = _parse_uuid(tenant_id, "tenant_id")
    aid = _parse_uuid(body.application_id, "application_id")
    lid = _parse_uuid(body.license_id, "license_id") if body.license_id else None

    if not db.query(Tenant).filter(Tenant.id == tid).first():
        raise HTTPException(404, "Tenant not found")
    if not db.query(Application).filter(Application.id == aid).first():
        raise HTTPException(404, "Application not found")
    if lid and not db.query(License).filter(License.id == lid, License.tenant_id == tid).first():
        raise HTTPException(404, "License not found or does not belong to this tenant")

    existing = db.query(TenantApplication).filter(
        TenantApplication.tenant_id == tid,
        TenantApplication.application_id == aid,
    ).first()
    if existing:
        raise HTTPException(400, "Application already assigned to this tenant")

    ta = TenantApplication(
        id             = uuid.uuid4(),
        tenant_id      = tid,
        application_id = aid,
        license_id     = lid,
        assigned_by_id = current_user.id,
    )
    db.add(ta)
    db.commit()
    db.refresh(ta)
    return {
        "id":               str(ta.id),
        "tenant_id":        str(ta.tenant_id),
        "application_id":   str(ta.application_id),
        "application_slug": ta.application.slug if ta.application else None,
        "application_name": ta.application.name if ta.application else None,
        "license_id":       str(ta.license_id) if ta.license_id else None,
        "assigned_at":      ta.assigned_at.isoformat(),
    }


@router.delete("/tenants/{tenant_id}/applications/{app_id}", status_code=204)
def revoke_app_from_tenant(
    tenant_id: str,
    app_id:    str,
    db:  Session = Depends(get_db),
    _:   User    = Depends(require_role(UserRole.RHADIX_ADMIN)),
):
    tid = _parse_uuid(tenant_id, "tenant_id")
    aid = _parse_uuid(app_id, "app_id")

    ta = db.query(TenantApplication).filter(
        TenantApplication.tenant_id == tid,
        TenantApplication.application_id == aid,
    ).first()
    if not ta:
        raise HTTPException(404, "Assignment not found")
    db.delete(ta)
    db.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# User management  (RHADIX_ADMIN — cross-tenant)
# ═══════════════════════════════════════════════════════════════════════════════

class AdminResetPasswordRequest(BaseModel):
    new_password: str


@router.patch("/users/{user_id}/deactivate")
def admin_toggle_user_active(
    user_id: str,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(require_role(UserRole.RHADIX_ADMIN)),
):
    """Toggle is_active for any user on the platform."""
    uid  = _parse_uuid(user_id, "user_id")
    user = db.query(User).filter(User.id == uid).first()
    if not user:
        raise HTTPException(404, "User not found")
    if user.id == current_user.id:
        raise HTTPException(400, "You cannot deactivate your own account")
    # Alleen bij deactiveren (van actief -> inactief) de laatste-admin-check
    if user.is_active and _is_last_active_admin(db, user):
        raise HTTPException(400, "Dit is de laatste actieve Rhadix-beheerder; deactiveren is niet toegestaan")

    user.is_active = not user.is_active
    db.commit()
    return {"id": str(user.id), "email": user.email, "is_active": user.is_active}


@router.delete("/users/{user_id}", status_code=204)
def admin_delete_user(
    user_id: str,
    db:      Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.RHADIX_ADMIN)),
):
    """Delete any user from the platform."""
    uid  = _parse_uuid(user_id, "user_id")
    user = db.query(User).filter(User.id == uid).first()
    if not user:
        raise HTTPException(404, "User not found")
    if user.id == current_user.id:
        raise HTTPException(400, "You cannot delete your own account")
    if _is_last_active_admin(db, user):
        raise HTTPException(400, "Dit is de laatste actieve Rhadix-beheerder; verwijderen is niet toegestaan")

    db.delete(user)
    db.commit()


@router.post("/users/{user_id}/reset-password", status_code=204)
def admin_reset_user_password(
    user_id: str,
    body:    AdminResetPasswordRequest,
    db:      Session = Depends(get_db),
    _:       User    = Depends(require_role(UserRole.RHADIX_ADMIN)),
):
    """Admin sets a new password for any user."""
    uid  = _parse_uuid(user_id, "user_id")
    user = db.query(User).filter(User.id == uid).first()
    if not user:
        raise HTTPException(404, "User not found")
    try:
        validate_password_strength(body.new_password)
    except ValueError as exc:
        raise HTTPException(422, str(exc))

    user.password_hash = hash_password(body.new_password)
    db.commit()
