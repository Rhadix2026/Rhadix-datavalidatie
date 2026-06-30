"""
schemas.py — Pydantic request/response models for auth and Phase 2 license/app endpoints.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, field_validator
from app.models.auth_models import UserRole


# ── Auth — Phase 1 ───────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    role: UserRole
    tenant_id: str
    tenant_name: str
    assigned_app_slugs: List[str] = []   # Phase 2: slugs the user may access

    model_config = {"from_attributes": True}


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class SetPasswordRequest(BaseModel):
    token: str
    password: str


class VerifyEmailRequest(BaseModel):
    token: str


# ── Application — Phase 2 ─────────────────────────────────────────────────────

class ApplicationResponse(BaseModel):
    id: str
    slug: str
    name: str
    description: Optional[str] = None
    is_active: bool
    sort_order: int
    created_at: str

    model_config = {"from_attributes": True}


class CreateApplicationRequest(BaseModel):
    slug: str
    name: str
    description: Optional[str] = None
    sort_order: int = 0


class UpdateApplicationRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


# ── License — Phase 2 ─────────────────────────────────────────────────────────

class CreateLicenseRequest(BaseModel):
    tenant_id: str
    name: str
    valid_from: Optional[datetime] = None      # defaults to now
    valid_until: Optional[datetime] = None     # null = no expiry
    max_users: Optional[int] = None            # null = unlimited
    notes: Optional[str] = None


class UpdateLicenseRequest(BaseModel):
    name: Optional[str] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    max_users: Optional[int] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class LicenseResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None
    max_users: Optional[int] = None
    notes: Optional[str] = None
    is_active: bool
    created_at: str
    app_slugs: List[str] = []    # slugs of applications attached via TenantApplication

    model_config = {"from_attributes": True}


# ── TenantApplication — Phase 2 ───────────────────────────────────────────────

class AssignTenantAppRequest(BaseModel):
    application_id: str
    license_id: Optional[str] = None   # null = no license requirement


class TenantApplicationResponse(BaseModel):
    id: str
    tenant_id: str
    application_id: str
    application_slug: str
    application_name: str
    license_id: Optional[str] = None
    assigned_at: str

    model_config = {"from_attributes": True}


# ── UserApplication — Phase 2 ─────────────────────────────────────────────────

class AssignUserAppRequest(BaseModel):
    user_id: str
    application_id: str


class RevokeUserAppRequest(BaseModel):
    user_id: str
    application_id: str


class UserApplicationResponse(BaseModel):
    id: str
    user_id: str
    application_id: str
    application_slug: str
    application_name: str
    tenant_application_id: str
    assigned_at: str

    model_config = {"from_attributes": True}
