"""
org.py — ORG_ADMIN endpoints for managing users and app assignments within their own tenant.

GET    /api/org/me/apps                          — list apps available to the caller's tenant
GET    /api/org/users                            — list users in the caller's tenant
POST   /api/org/users                            — create a new user in the tenant
PATCH  /api/org/users/{user_id}/deactivate       — toggle is_active
DELETE /api/org/users/{user_id}                  — delete a user
POST   /api/org/users/{user_id}/reset-password   — admin sets new password for user
GET    /api/org/users/{user_id}/apps             — list app assignments for a user
POST   /api/org/users/{user_id}/apps             — assign an app to a user
DELETE /api/org/users/{user_id}/apps/{app_id}    — revoke an app from a user
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_role
from app.auth.schemas import AssignUserAppRequest
from app.auth.security import hash_password
from app.database import get_db
from app.models.auth_models import (
    Application,
    TenantApplication,
    User,
    UserApplication,
    UserRole,
)

router = APIRouter(tags=["Org"])

# ─── helpers ──────────────────────────────────────────────────────────────────

def _parse_uuid(val: str, label: str = "ID") -> uuid.UUID:
    try:
        return uuid.UUID(val)
    except (ValueError, AttributeError):
        raise HTTPException(400, f"Invalid {label}: {val!r}")

_org_roles = require_role(UserRole.ORG_ADMIN, UserRole.RHADIX_ADMIN)


# ═══════════════════════════════════════════════════════════════════════════════
# Apps available to the tenant (ORG_ADMIN + RHADIX_ADMIN)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/me/apps")
def list_my_tenant_apps(
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    """List all applications assigned to the current user's tenant (any role)."""
    rows = (
        db.query(TenantApplication)
        .filter(TenantApplication.tenant_id == current_user.tenant_id)
        .all()
    )
    return [
        {
            "id":               str(r.id),
            "application_id":   str(r.application_id),
            "application_slug": r.application.slug if r.application else None,
            "application_name": r.application.name if r.application else None,
            "license_id":       str(r.license_id) if r.license_id else None,
            "assigned_at":      r.assigned_at.isoformat(),
        }
        for r in rows
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# User management within the org (ORG_ADMIN)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/users")
def list_org_users(
    db:           Session = Depends(get_db),
    current_user: User    = Depends(_org_roles),
):
    """List all users in the current admin's tenant."""
    users = (
        db.query(User)
        .filter(User.tenant_id == current_user.tenant_id)
        .order_by(User.created_at)
        .all()
    )
    return [
        {
            "id":        str(u.id),
            "email":     u.email,
            "full_name": u.full_name,
            "role":      u.role.value,
            "is_active": u.is_active,
        }
        for u in users
    ]


# ─── request bodies ───────────────────────────────────────────────────────────

class CreateOrgUserRequest(BaseModel):
    email:     str
    full_name: Optional[str] = None
    password:  str
    role:      str = "ORG_USER"   # ORG_USER or ORG_ADMIN

class ResetPasswordRequest(BaseModel):
    new_password: str


# ═══════════════════════════════════════════════════════════════════════════════
# User CRUD within the org
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/users", status_code=201)
def create_org_user(
    body:         CreateOrgUserRequest,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(_org_roles),
):
    """Create a new user in the current admin's tenant."""
    email = body.email.lower().strip()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(400, f"E-mailadres '{body.email}' is al in gebruik")
    if len(body.password) < 12:
        raise HTTPException(422, "Wachtwoord moet minimaal 12 tekens bevatten")
    try:
        role = UserRole(body.role)
    except ValueError:
        raise HTTPException(422, f"Ongeldig rol: {body.role!r}")
    if role == UserRole.RHADIX_ADMIN:
        raise HTTPException(403, "Rhadix-beheerdersrol kan niet worden toegewezen")

    user = User(
        id            = uuid.uuid4(),
        tenant_id     = current_user.tenant_id,
        email         = email,
        full_name     = body.full_name,
        password_hash = hash_password(body.password),
        role          = role,
        is_active     = True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {
        "id":        str(user.id),
        "email":     user.email,
        "full_name": user.full_name,
        "role":      user.role.value,
        "is_active": user.is_active,
    }


@router.patch("/users/{user_id}/deactivate")
def toggle_user_active(
    user_id: str,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(_org_roles),
):
    """Toggle is_active for a user in the current admin's tenant."""
    uid  = _parse_uuid(user_id, "user_id")
    user = db.query(User).filter(User.id == uid, User.tenant_id == current_user.tenant_id).first()
    if not user:
        raise HTTPException(404, "Gebruiker niet gevonden in uw organisatie")
    if user.id == current_user.id:
        raise HTTPException(400, "U kunt uw eigen account niet deactiveren")

    user.is_active = not user.is_active
    db.commit()
    return {"id": str(user.id), "is_active": user.is_active}


@router.delete("/users/{user_id}", status_code=204)
def delete_org_user(
    user_id: str,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(_org_roles),
):
    """Delete a user from the current admin's tenant."""
    uid  = _parse_uuid(user_id, "user_id")
    user = db.query(User).filter(User.id == uid, User.tenant_id == current_user.tenant_id).first()
    if not user:
        raise HTTPException(404, "Gebruiker niet gevonden in uw organisatie")
    if user.id == current_user.id:
        raise HTTPException(400, "U kunt uw eigen account niet verwijderen")

    db.delete(user)
    db.commit()


@router.post("/users/{user_id}/reset-password", status_code=204)
def reset_user_password(
    user_id: str,
    body:         ResetPasswordRequest,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(_org_roles),
):
    """Admin sets a new password for a user in their tenant."""
    uid  = _parse_uuid(user_id, "user_id")
    user = db.query(User).filter(User.id == uid, User.tenant_id == current_user.tenant_id).first()
    if not user:
        raise HTTPException(404, "Gebruiker niet gevonden in uw organisatie")
    if len(body.new_password) < 12:
        raise HTTPException(422, "Wachtwoord moet minimaal 12 tekens bevatten")

    user.password_hash = hash_password(body.new_password)
    db.commit()


@router.get("/users/{user_id}/apps")
def list_user_app_assignments(
    user_id: str,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(_org_roles),
):
    """List applications assigned to a specific user within the org."""
    uid  = _parse_uuid(user_id, "user_id")
    user = db.query(User).filter(User.id == uid, User.tenant_id == current_user.tenant_id).first()
    if not user:
        raise HTTPException(404, "User not found in your organisation")

    rows = db.query(UserApplication).filter(UserApplication.user_id == uid).all()
    return [
        {
            "id":                    str(r.id),
            "user_id":               str(r.user_id),
            "application_id":        str(r.application_id),
            "application_slug":      r.application.slug if r.application else None,
            "application_name":      r.application.name if r.application else None,
            "tenant_application_id": str(r.tenant_application_id),
            "assigned_at":           r.assigned_at.isoformat(),
        }
        for r in rows
    ]


@router.post("/users/{user_id}/apps", status_code=201)
def assign_app_to_user(
    user_id: str,
    body:         AssignUserAppRequest,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(_org_roles),
):
    """
    Assign an application to a user in the current admin's tenant.
    The application must first be assigned to the tenant (TenantApplication).
    """
    uid = _parse_uuid(user_id, "user_id")
    aid = _parse_uuid(body.application_id, "application_id")

    # Verify user belongs to this tenant
    target_user = db.query(User).filter(User.id == uid, User.tenant_id == current_user.tenant_id).first()
    if not target_user:
        raise HTTPException(404, "User not found in your organisation")

    # Verify the tenant has this application
    ta = db.query(TenantApplication).filter(
        TenantApplication.tenant_id == current_user.tenant_id,
        TenantApplication.application_id == aid,
    ).first()
    if not ta:
        raise HTTPException(403, "Application is not available for your organisation. Contact Rhadix support.")

    # Check for duplicate
    existing = db.query(UserApplication).filter(
        UserApplication.user_id == uid,
        UserApplication.application_id == aid,
    ).first()
    if existing:
        raise HTTPException(400, "Application already assigned to this user")

    ua = UserApplication(
        id                    = uuid.uuid4(),
        user_id               = uid,
        application_id        = aid,
        tenant_application_id = ta.id,
        assigned_by_id        = current_user.id,
    )
    db.add(ua)
    db.commit()
    db.refresh(ua)
    return {
        "id":                    str(ua.id),
        "user_id":               str(ua.user_id),
        "application_id":        str(ua.application_id),
        "application_slug":      ua.application.slug if ua.application else None,
        "application_name":      ua.application.name if ua.application else None,
        "tenant_application_id": str(ua.tenant_application_id),
        "assigned_at":           ua.assigned_at.isoformat(),
    }


@router.delete("/users/{user_id}/apps/{app_id}", status_code=204)
def revoke_app_from_user(
    user_id: str,
    app_id:  str,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(_org_roles),
):
    """Revoke an application from a user in the current admin's tenant."""
    uid = _parse_uuid(user_id, "user_id")
    aid = _parse_uuid(app_id, "app_id")

    # Verify user belongs to this tenant
    target_user = db.query(User).filter(User.id == uid, User.tenant_id == current_user.tenant_id).first()
    if not target_user:
        raise HTTPException(404, "User not found in your organisation")

    ua = db.query(UserApplication).filter(
        UserApplication.user_id == uid,
        UserApplication.application_id == aid,
    ).first()
    if not ua:
        raise HTTPException(404, "Assignment not found")

    db.delete(ua)
    db.commit()
