"""
auth_models.py — Tenant, User, role, License and Application definitions for Rhadix SaaS.
Phase 1: core auth foundation.
Phase 2: License model, Application model, org-app and user-app assignments.
"""
import enum
import uuid

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import backref, relationship
from sqlalchemy.sql import func

from app.database import Base


# ── Roles ─────────────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    RHADIX_ADMIN = "RHADIX_ADMIN"   # Rhadix platform staff — sees everything
    RSO_ADMIN    = "RSO_ADMIN"      # Samenwerkingsorganisatie (bv. RSO) — beheert eigen RSO + onderliggende organisaties
    ORG_ADMIN    = "ORG_ADMIN"      # Organisation administrator
    ORG_USER     = "ORG_USER"       # Regular organisation user


# ── Tenant ────────────────────────────────────────────────────────────────────

class Tenant(Base):
    """An organisation (customer) on the Rhadix platform."""
    __tablename__ = "tenants"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug       = Column(String(63), unique=True, nullable=False, index=True)
    name       = Column(String(255), nullable=False)
    is_active  = Column(Boolean, default=True, nullable=False)
    # tenant_type: 'ORG' = zorgorganisatie (default), 'RSO' = samenwerkingsorganisatie, 'PLATFORM' = Rhadix
    tenant_type      = Column(String(16), nullable=False, server_default="ORG", default="ORG")
    # Ouder-tenant: een zorgorganisatie kan onder één RSO hangen (self-referential).
    parent_tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    users               = relationship("User", back_populates="tenant", cascade="all, delete-orphan",
                                        foreign_keys="[User.tenant_id]")
    licenses            = relationship("License", back_populates="tenant", cascade="all, delete-orphan")
    tenant_applications = relationship("TenantApplication", back_populates="tenant", cascade="all, delete-orphan")
    # Onderliggende organisaties (kinderen) van deze RSO; verwijderen van de RSO zet parent op NULL (geen cascade).
    children = relationship("Tenant", backref=backref("parent", remote_side=[id]))


# ── User ──────────────────────────────────────────────────────────────────────

class User(Base):
    """A user account, always belonging to exactly one tenant."""
    __tablename__ = "users"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id      = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    email          = Column(String(255), unique=True, nullable=False, index=True)
    password_hash  = Column(String(255), nullable=True)   # nullable for future SSO-only users
    full_name      = Column(String(255), nullable=True)
    role           = Column(Enum(UserRole), nullable=False, default=UserRole.ORG_USER)
    is_active      = Column(Boolean, default=True, nullable=False)
    email_verified = Column(Boolean, default=True, nullable=False)   # bestaande users gelden als geverifieerd
    last_login_at  = Column(DateTime(timezone=True), nullable=True)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())

    tenant           = relationship("Tenant", back_populates="users")
    user_applications = relationship("UserApplication", back_populates="user", cascade="all, delete-orphan",
                                     foreign_keys="[UserApplication.user_id]")


# ── Application ───────────────────────────────────────────────────────────────

class Application(Base):
    """A Rhadix product module that can be licensed and assigned to organisations/users."""
    __tablename__ = "applications"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug        = Column(String(63), unique=True, nullable=False, index=True)
    name        = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_active   = Column(Boolean, default=True, nullable=False)
    sort_order  = Column(Integer, default=0, nullable=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    tenant_applications = relationship("TenantApplication", back_populates="application")
    user_applications   = relationship("UserApplication",   back_populates="application")


# ── License ───────────────────────────────────────────────────────────────────

class License(Base):
    """A license granting a tenant access to one or more applications for a period."""
    __tablename__ = "licenses"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id      = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name           = Column(String(255), nullable=False)           # e.g. "2026 Jaarlicentie"
    valid_from     = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    valid_until    = Column(DateTime(timezone=True), nullable=True)  # NULL = no expiry
    max_users      = Column(Integer, nullable=True)                  # NULL = unlimited
    notes          = Column(Text, nullable=True)
    is_active      = Column(Boolean, default=True, nullable=False)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())
    created_by_id  = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    tenant              = relationship("Tenant", back_populates="licenses")
    created_by          = relationship("User", foreign_keys=[created_by_id])
    tenant_applications = relationship("TenantApplication", back_populates="license", cascade="all, delete-orphan")


# ── TenantApplication ─────────────────────────────────────────────────────────

class TenantApplication(Base):
    """
    Assignment of an Application to a Tenant, optionally tied to a License.
    Created by RHADIX_ADMIN.
    """
    __tablename__ = "tenant_applications"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id      = Column(UUID(as_uuid=True), ForeignKey("tenants.id",      ondelete="CASCADE"),  nullable=False, index=True)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"),  nullable=False, index=True)
    license_id     = Column(UUID(as_uuid=True), ForeignKey("licenses.id",     ondelete="SET NULL"), nullable=True,  index=True)
    assigned_at    = Column(DateTime(timezone=True), server_default=func.now())
    assigned_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    tenant      = relationship("Tenant",      back_populates="tenant_applications")
    application = relationship("Application", back_populates="tenant_applications")
    license     = relationship("License",     back_populates="tenant_applications")
    assigned_by = relationship("User", foreign_keys=[assigned_by_id])
    user_applications = relationship("UserApplication", back_populates="tenant_application",
                                     cascade="all, delete-orphan")


# ── UserApplication ───────────────────────────────────────────────────────────

class UserApplication(Base):
    """
    Assignment of an Application to a specific User within a Tenant.
    Created by ORG_ADMIN (or RHADIX_ADMIN).
    """
    __tablename__ = "user_applications"

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id               = Column(UUID(as_uuid=True), ForeignKey("users.id",               ondelete="CASCADE"), nullable=False, index=True)
    application_id        = Column(UUID(as_uuid=True), ForeignKey("applications.id",        ondelete="CASCADE"), nullable=False, index=True)
    tenant_application_id = Column(UUID(as_uuid=True), ForeignKey("tenant_applications.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_at           = Column(DateTime(timezone=True), server_default=func.now())
    assigned_by_id        = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    user               = relationship("User",              back_populates="user_applications", foreign_keys=[user_id])
    application        = relationship("Application",       back_populates="user_applications")
    tenant_application = relationship("TenantApplication", back_populates="user_applications")
    assigned_by        = relationship("User", foreign_keys=[assigned_by_id])


# ── Auth-tokens (wachtwoord-reset / uitnodiging / e-mailverificatie) ───────────

class AuthToken(Base):
    """Eenmalig, kortlevend token voor wachtwoord-reset, uitnodiging of e-mailverificatie.

    Alleen de SHA-256-hash van het token wordt opgeslagen (nooit het token zelf),
    zodat een database-lek geen bruikbare links oplevert. Eenmalig: used_at wordt
    gezet zodra het token is verzilverd.
    """
    __tablename__ = "auth_tokens"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    purpose    = Column(String(20), nullable=False)            # 'reset' | 'invite' | 'verify'
    token_hash = Column(String(64), nullable=False, index=True)  # sha256 hex
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at    = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")
