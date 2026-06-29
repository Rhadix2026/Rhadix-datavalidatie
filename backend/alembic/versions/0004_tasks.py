"""Phase 4 — Taken/workflow: tasks-tabel (generieke takenlijst per gebruiker)

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-26
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Idempotent: CREATE TABLE IF NOT EXISTS zodat de migratie ook werkt als de
    # tabel al via create_all() of een eerdere deploy is aangemaakt.
    op.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id            UUID PRIMARY KEY,
            tenant_id     UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            title         VARCHAR(255) NOT NULL,
            description   TEXT,
            status        VARCHAR(20)  NOT NULL DEFAULT 'OPEN',
            priority      VARCHAR(10)  NOT NULL DEFAULT 'NORMAAL',
            due_date      TIMESTAMPTZ,
            assignee_id   UUID REFERENCES users(id) ON DELETE SET NULL,
            created_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
            app_slug      VARCHAR(40),
            source_type   VARCHAR(40),
            source_ref    VARCHAR(255),
            source_label  VARCHAR(255),
            created_at    TIMESTAMPTZ DEFAULT now(),
            updated_at    TIMESTAMPTZ DEFAULT now(),
            completed_at  TIMESTAMPTZ
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_tasks_tenant_id       ON tasks (tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_tasks_assignee_id     ON tasks (assignee_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_tasks_tenant_status   ON tasks (tenant_id, status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_tasks_assignee_status ON tasks (assignee_id, status)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS tasks")
