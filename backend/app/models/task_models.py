"""
task_models.py — Generieke takenlijst / workflow voor het Rhadix-platform.

Bewust app-onafhankelijk opgezet zodat dezelfde module in alle vier de
applicaties (Datavalidatie, Uitvraag, Datastation, CRM) kan worden hergebruikt:
één `tasks`-tabel per app, tenant-gescoped, toewijzen binnen de eigen organisatie.

Koppeling naar de bron (bijv. een AFAS-validatierun of een CRM-organisatie)
gebeurt los via source_type/source_ref/source_label, zonder harde FK — zo blijft
het model identiek over alle apps.
"""
import enum
import uuid

from sqlalchemy import Column, DateTime, Enum, ForeignKey, String, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class TaskStatus(str, enum.Enum):
    OPEN          = "OPEN"
    IN_BEHANDELING = "IN_BEHANDELING"
    KLAAR         = "KLAAR"
    GEANNULEERD   = "GEANNULEERD"


class TaskPriority(str, enum.Enum):
    LAAG    = "LAAG"
    NORMAAL = "NORMAAL"
    HOOG    = "HOOG"


class Task(Base):
    """Een taak op gebruikersniveau, altijd binnen één tenant (organisatie)."""
    __tablename__ = "tasks"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id   = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"),
                         nullable=False, index=True)

    title       = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    status      = Column(Enum(TaskStatus,    name="task_status"),   nullable=False, default=TaskStatus.OPEN)
    priority    = Column(Enum(TaskPriority,  name="task_priority"), nullable=False, default=TaskPriority.NORMAAL)
    due_date    = Column(DateTime(timezone=True), nullable=True)

    # Toewijzing — binnen dezelfde tenant (afgedwongen in de router)
    assignee_id   = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Generieke koppeling naar de bron (geen harde FK → portable over apps)
    app_slug     = Column(String(40),  nullable=True)   # bv. 'kikv-validator', 'rhadix-crm'
    source_type  = Column(String(40),  nullable=True)   # bv. 'afas_validatie', 'crm_organisatie', 'handmatig'
    source_ref   = Column(String(255), nullable=True)   # id van de bron (run-id, org-id, ...)
    source_label = Column(String(255), nullable=True)   # leesbare context / deeplink-tekst

    created_at   = Column(DateTime(timezone=True), server_default=func.now())
    updated_at   = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    assignee   = relationship("User", foreign_keys=[assignee_id])
    created_by = relationship("User", foreign_keys=[created_by_id])


Index("ix_tasks_tenant_status", Task.tenant_id, Task.status)
Index("ix_tasks_assignee_status", Task.assignee_id, Task.status)
