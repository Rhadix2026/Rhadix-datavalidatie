"""
machine_models.py — machineaccounts voor machine-to-machine-toegang (B-28).

Een machineaccount staat bewust NIET in `users`: zo kan het per constructie niet
via /api/auth/login, het SSO-cookie, wachtwoord-vergeten of een uitnodiging
binnenkomen, en telt het niet mee in de licentie. Het krijgt alleen een kortlevend
token via /api/auth/machine-token (client_credentials).

`MachineAccount.id` is de `sub` van zijn tokens; centrale intrekking (B-16) werkt
dus op dezelfde manier als voor gebruikers.
"""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.database import Base


class MachineAccount(Base):
    __tablename__ = "machine_accounts"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    naam         = Column(String(120), nullable=False, unique=True)
    tenant_id    = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True)
    # Komma-gescheiden; één doelgroep per token (`aud`), alleen uit deze lijst.
    doelgroepen  = Column(String(500), nullable=False)
    scopes       = Column(String(500), nullable=False)
    is_active    = Column(Boolean, nullable=False, default=True)
    created_by   = Column(String(64), nullable=True)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    def doelgroep_lijst(self) -> list[str]:
        return [d.strip() for d in (self.doelgroepen or "").split(",") if d.strip()]

    def scope_lijst(self) -> list[str]:
        return [s.strip() for s in (self.scopes or "").split() if s.strip()]


class MachineSecret(Base):
    """Een geheim van een machineaccount. Alleen de SHA-256 wordt bewaard; het geheim
    zelf wordt één keer getoond. Maximaal twee tegelijk actief (rotatie)."""
    __tablename__ = "machine_secrets"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id   = Column(UUID(as_uuid=True), ForeignKey("machine_accounts.id", ondelete="CASCADE"),
                          nullable=False, index=True)
    hash         = Column(String(64), nullable=False, unique=True)
    prefix       = Column(String(16), nullable=False)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
    expires_at   = Column(DateTime(timezone=True), nullable=False)
    revoked_at   = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
