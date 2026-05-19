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
    # ── Subscore kolommen voor directe aggregaties (zonder JSON-parsing) ──────
    op.add_column("validation_runs", sa.Column("structural_score", sa.Float(), nullable=True))
    op.add_column("validation_runs", sa.Column("relational_score", sa.Float(), nullable=True))
    op.add_column("validation_runs", sa.Column("use_case_score",   sa.Float(), nullable=True))
    op.add_column("validation_runs", sa.Column("source_system",    sa.String(255), nullable=True))

    # ── Indexen voor dashboard queries ────────────────────────────────────────
    op.create_index("ix_validation_runs_score",      "validation_runs", ["score"])
    op.create_index("ix_validation_runs_created_at", "validation_runs", ["created_at"])
    op.create_index("ix_validation_runs_standard",   "validation_runs", ["standard"])


def downgrade() -> None:
    op.drop_index("ix_validation_runs_standard",   "validation_runs")
    op.drop_index("ix_validation_runs_created_at", "validation_runs")
    op.drop_index("ix_validation_runs_score",      "validation_runs")

    op.drop_column("validation_runs", "source_system")
    op.drop_column("validation_runs", "use_case_score")
    op.drop_column("validation_runs", "relational_score")
    op.drop_column("validation_runs", "structural_score")
