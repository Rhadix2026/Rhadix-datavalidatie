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

    # ── Extend validation_runs ────────────────────────────────────────────────
    # All columns are nullable so existing rows are unaffected.
    op.add_column(
        "validation_runs",
        sa.Column("standard",   sa.String(32), nullable=True),
    )
    op.add_column(
        "validation_runs",
        sa.Column("tenant_id",  postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True),
    )
    op.add_column(
        "validation_runs",
        sa.Column("created_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id",   ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_validation_runs_tenant_id", "validation_runs", ["tenant_id"])


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
