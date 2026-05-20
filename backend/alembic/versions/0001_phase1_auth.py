"""Phase 1 — auth foundation: tenants, users, extend validation_runs

Revision ID: 0001
Revises:
Create Date: 2026-05-19

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Create tenants table ──────────────────────────────────────────────────
    op.create_table(
        "tenants",
        sa.Column("id",         postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug",       sa.String(63),  nullable=False),
        sa.Column("name",       sa.String(255), nullable=False),
        sa.Column("is_active",  sa.Boolean(),   nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"], unique=True)

    # ── Create users table ────────────────────────────────────────────────────
    # Use a DO block so the enum creation is idempotent even if a previous
    # migration attempt left it behind without completing.
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE userrole AS ENUM ('RHADIX_ADMIN', 'ORG_ADMIN', 'ORG_USER');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    op.create_table(
        "users",
        sa.Column("id",            postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id",     postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email",         sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("full_name",     sa.String(255), nullable=True),
        sa.Column("role",          postgresql.ENUM(
                                       "RHADIX_ADMIN", "ORG_ADMIN", "ORG_USER",
                                       name="userrole", create_type=False),
                  nullable=False, server_default="ORG_USER"),
        sa.Column("is_active",     sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at",    sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_users_email",     "users", ["email"],     unique=True)
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"], unique=False)

    # ── validation_runs — maak de basistabel aan als die nog niet bestaat ────────
    # Op bestaande servers (opgezet via create_all) bestaat de tabel al.
    # Op een verse productie-DB moet hij eerst aangemaakt worden.
    op.execute("""
        CREATE TABLE IF NOT EXISTS validation_runs (
            id          SERIAL PRIMARY KEY,
            created_at  TIMESTAMP WITH TIME ZONE DEFAULT now(),
            label       VARCHAR(255),
            files       JSON,
            results     JSON,
            total_rows  INTEGER DEFAULT 0,
            error_count INTEGER DEFAULT 0,
            warn_count  INTEGER DEFAULT 0,
            score       FLOAT DEFAULT 100.0,
            status      VARCHAR(32) DEFAULT 'completed'
        )
    """)

    # ── Extend validation_runs — gebruik IF NOT EXISTS voor idempotentie ──────
    op.execute("""
        ALTER TABLE validation_runs
            ADD COLUMN IF NOT EXISTS standard   VARCHAR(32),
            ADD COLUMN IF NOT EXISTS tenant_id  UUID REFERENCES tenants(id)  ON DELETE SET NULL,
            ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES users(id)    ON DELETE SET NULL
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_validation_runs_tenant_id ON validation_runs (tenant_id)")


def downgrade() -> None:
    op.drop_index("ix_validation_runs_tenant_id", "validation_runs")
    op.drop_column("validation_runs", "created_by")
    op.drop_column("validation_runs", "tenant_id")
    op.drop_column("validation_runs", "standard")

    op.drop_index("ix_users_tenant_id", "users")
    op.drop_index("ix_users_email",     "users")
    op.drop_table("users")

    op.drop_index("ix_tenants_slug", "tenants")
    op.drop_table("tenants")

    sa.Enum(name="userrole").drop(op.get_bind(), checkfirst=True)
