"""Phase 2 — licenses, applications, tenant/user app assignments, extend validation_runs

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-19
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ── Built-in application definitions ─────────────────────────────────────────
# Seeded once at migration time so they exist immediately without a separate
# seed script.  Slugs are stable identifiers referenced by backend access checks.
BUILT_IN_APPS = [
    {
        "slug":        "kikv-validator",
        "name":        "KIK-V Validator",
        "description": "Validatie van zorgdata tegen de KIK-V gegevensstandaard.",
        "sort_order":  1,
    },
    {
        "slug":        "zib-validator",
        "name":        "ZIB Validator",
        "description": "Validatie van zorgdata tegen ZIB-definities.",
        "sort_order":  2,
    },
    {
        "slug":        "algemeen-validator",
        "name":        "Algemene Validator",
        "description": "Generieke CSV/Excel/XML validatie zonder domeinstandaard.",
        "sort_order":  3,
    },
    {
        "slug":        "reconciliation",
        "name":        "Reconciliation Engine",
        "description": "Vergelijking en afstemming van gegevensbronnen.",
        "sort_order":  4,
    },
]


def upgrade() -> None:
    # ── applications ──────────────────────────────────────────────────────────
    op.create_table(
        "applications",
        sa.Column("id",          postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug",        sa.String(63),  nullable=False),
        sa.Column("name",        sa.String(255), nullable=False),
        sa.Column("description", sa.Text(),      nullable=True),
        sa.Column("is_active",   sa.Boolean(),   nullable=False, server_default="true"),
        sa.Column("sort_order",  sa.Integer(),   nullable=False, server_default="0"),
        sa.Column("created_at",  sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_applications_slug", "applications", ["slug"], unique=True)

    # Seed built-in applications
    import uuid as _uuid
    apps_table = sa.table(
        "applications",
        sa.column("id",          postgresql.UUID(as_uuid=True)),
        sa.column("slug",        sa.String),
        sa.column("name",        sa.String),
        sa.column("description", sa.Text),
        sa.column("is_active",   sa.Boolean),
        sa.column("sort_order",  sa.Integer),
    )
    op.bulk_insert(
        apps_table,
        [
            {
                "id":          _uuid.uuid4(),
                "slug":        a["slug"],
                "name":        a["name"],
                "description": a["description"],
                "is_active":   True,
                "sort_order":  a["sort_order"],
            }
            for a in BUILT_IN_APPS
        ],
    )

    # ── licenses ──────────────────────────────────────────────────────────────
    op.create_table(
        "licenses",
        sa.Column("id",            postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id",     postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name",          sa.String(255), nullable=False),
        sa.Column("valid_from",    sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("valid_until",   sa.DateTime(timezone=True), nullable=True),
        sa.Column("max_users",     sa.Integer(),  nullable=True),
        sa.Column("notes",         sa.Text(),     nullable=True),
        sa.Column("is_active",     sa.Boolean(),  nullable=False, server_default="true"),
        sa.Column("created_at",    sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_licenses_tenant_id", "licenses", ["tenant_id"])

    # ── tenant_applications ───────────────────────────────────────────────────
    op.create_table(
        "tenant_applications",
        sa.Column("id",             postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id",      postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id",      ondelete="CASCADE"),  nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("applications.id", ondelete="CASCADE"),  nullable=False),
        sa.Column("license_id",     postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("licenses.id",     ondelete="SET NULL"), nullable=True),
        sa.Column("assigned_at",    sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("assigned_by_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_tenant_applications_tenant_id",      "tenant_applications", ["tenant_id"])
    op.create_index("ix_tenant_applications_application_id", "tenant_applications", ["application_id"])
    op.create_index("ix_tenant_applications_license_id",     "tenant_applications", ["license_id"])
    # A tenant should not have the same application assigned twice
    op.create_unique_constraint(
        "uq_tenant_application",
        "tenant_applications",
        ["tenant_id", "application_id"],
    )

    # ── user_applications ─────────────────────────────────────────────────────
    op.create_table(
        "user_applications",
        sa.Column("id",                    postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id",               postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id",               ondelete="CASCADE"), nullable=False),
        sa.Column("application_id",        postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("applications.id",        ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_application_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenant_applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assigned_at",           sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("assigned_by_id",        postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_user_applications_user_id",        "user_applications", ["user_id"])
    op.create_index("ix_user_applications_application_id", "user_applications", ["application_id"])
    op.create_unique_constraint(
        "uq_user_application",
        "user_applications",
        ["user_id", "application_id"],
    )

    # ── Extend validation_runs with Phase 2 columns ───────────────────────────
    op.add_column(
        "validation_runs",
        sa.Column("application_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("applications.id", ondelete="SET NULL"), nullable=True),
    )
    op.add_column(
        "validation_runs",
        sa.Column("license_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("licenses.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_validation_runs_application_id", "validation_runs", ["application_id"])


def downgrade() -> None:
    op.drop_index("ix_validation_runs_application_id", "validation_runs")
    op.drop_column("validation_runs", "license_id")
    op.drop_column("validation_runs", "application_id")

    op.drop_constraint("uq_user_application",   "user_applications",   type_="unique")
    op.drop_index("ix_user_applications_application_id", "user_applications")
    op.drop_index("ix_user_applications_user_id",        "user_applications")
    op.drop_table("user_applications")

    op.drop_constraint("uq_tenant_application",               "tenant_applications", type_="unique")
    op.drop_index("ix_tenant_applications_license_id",        "tenant_applications")
    op.drop_index("ix_tenant_applications_application_id",    "tenant_applications")
    op.drop_index("ix_tenant_applications_tenant_id",         "tenant_applications")
    op.drop_table("tenant_applications")

    op.drop_index("ix_licenses_tenant_id", "licenses")
    op.drop_table("licenses")

    op.drop_index("ix_applications_slug", "applications")
    op.drop_table("applications")
