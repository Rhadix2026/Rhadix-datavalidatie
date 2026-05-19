"""Phase 3 — Dashboard: add subscore columns to validation_runs

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-19
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Subscore kolommen — gebruik IF NOT EXISTS zodat de migratie idempotent
    #    is als staging al (deels) via create_all() was opgezet.
    op.execute("""
        ALTER TABLE validation_runs
            ADD COLUMN IF NOT EXISTS structural_score FLOAT,
            ADD COLUMN IF NOT EXISTS relational_score FLOAT,
            ADD COLUMN IF NOT EXISTS use_case_score   FLOAT,
            ADD COLUMN IF NOT EXISTS source_system    VARCHAR(255)
    """)

    # ── Indexen — CREATE INDEX IF NOT EXISTS zodat bestaande indexen geen fout geven
    op.execute("CREATE INDEX IF NOT EXISTS ix_validation_runs_score      ON validation_runs (score)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_validation_runs_created_at ON validation_runs (created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_validation_runs_standard   ON validation_runs (standard)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_validation_runs_standard")
    op.execute("DROP INDEX IF EXISTS ix_validation_runs_created_at")
    op.execute("DROP INDEX IF EXISTS ix_validation_runs_score")

    op.drop_column("validation_runs", "source_system")
    op.drop_column("validation_runs", "use_case_score")
    op.drop_column("validation_runs", "relational_score")
    op.drop_column("validation_runs", "structural_score")
