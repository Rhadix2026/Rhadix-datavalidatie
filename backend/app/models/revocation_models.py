"""
revocation_models.py — tabellen voor centrale sessie-intrekking (B-16).

Twee kanten, bewust in aparte tabellen:

  uitgever   session_revocations   de bron: wat is er ingetrokken, tot wanneer
  ontvanger  revoked_sessions      de lokale kopie, bij elke hartslag volledig vervangen
             revocation_state      één rij: wanneer hoorden we de uitgever het laatst,
                                   en staat de noodprocedure aan

Datavalidatie is beide tegelijk. De lijst staat op schijf en niet in geheugen:
een herstart mag een ingetrokken sessie niet weer geldig maken.
"""
import uuid

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.database import Base


class SessionRevocation(Base):
    """Uitgever: één intrekking. Bij uitloggen zowel het aangeboden token (`jti`)
    als alle sessies van `sub` die vóór `not_before` zijn uitgegeven."""
    __tablename__ = "session_revocations"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    jti        = Column(String(64), nullable=True, index=True)
    sub        = Column(String(64), nullable=False, index=True)
    not_before = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RevokedSession(Base):
    """Ontvanger: lokale kopie van de lijst van de uitgever."""
    __tablename__ = "revoked_sessions"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    jti        = Column(String(64), nullable=True, index=True)
    sub        = Column(String(64), nullable=False, index=True)
    not_before = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)


class RevocationState(Base):
    """Ontvanger: altijd precies één rij (id = 1).

    `last_heard_at` wordt bij een koude start **niet** op "nu" gezet; leeg
    betekent: nog nooit iets gehoord, en dan geldt het beeld als muf.
    """
    __tablename__ = "revocation_state"

    id                  = Column(Integer, primary_key=True)
    last_heard_at       = Column(DateTime(timezone=True), nullable=True)
    last_generated_at   = Column(DateTime(timezone=True), nullable=True)
    grace_until         = Column(DateTime(timezone=True), nullable=True)
    grace_reason        = Column(Text, nullable=True)
    grace_by            = Column(String(255), nullable=True)
    grace_activated_at  = Column(DateTime(timezone=True), nullable=True)
    grace_expiry_logged = Column(Boolean, nullable=False, default=False)
