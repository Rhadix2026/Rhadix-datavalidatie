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
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
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
from app.auth.security import hash_password
from app.database import get_db
from app.models.auth_models import (
    Application,
    License,
    Tenant,
    TenantApplication,
    User,
    UserRole,
)
from app.models.models import ValidationRun

router = APIRouter(tags=["Admin"])

# ─── helpers ──────────────────────────────────────────────────────────────────

def _parse_uuid(val: str, label: str = "ID") -> uuid.UUID:
    try:
        return uuid.UUID(val)
    except (ValueError, AttributeError):
        raise HTTPException(400, f"Invalid {label}: {val!r}")


# ═══════════════════════════════════════════════════════════════════════════════
# Tenant management  (Phase 1)
# ═══════════════════════════════════════════════════════════════════════════════

class CreateTenantRequest(BaseModel):
    name: str
    slug: str
    admin_email: str
    admin_password: str
    admin_full_name: Optional[str] = None


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

    tenant = Tenant(id=uuid.uuid4(), slug=body.slug, name=body.name, is_active=True)
    db.add(tenant)
    db.flush()   # get tenant.id before creating user

    user = User(
        id            = uuid.uuid4(),
        tenant_id     = tenant.id,
        email         = body.admin_email.lower().strip(),
        password_hash = hash_password(body.admin_password),
        full_name     = body.admin_full_name,
        role          = UserRole.ORG_ADMIN,
        is_active     = True,
    )
    db.add(user)
    db.commit()
    db.refresh(tenant)
    return {"id": str(tenant.id), "slug": tenant.slug, "name": tenant.name, "admin_user_id": str(user.id)}


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
