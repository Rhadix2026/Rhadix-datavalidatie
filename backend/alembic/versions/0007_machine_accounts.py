"""Phase 7 — machineaccounts voor machine-to-machine-toegang (B-28)

Additief en idempotent (IF NOT EXISTS), zodat ook het startup-vangnet
`_ensure_machine_schema` de objecten al aangemaakt kan hebben. Bij terugdraaien van
de code mogen de tabellen blijven staan.

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-28
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS machine_accounts (
            id           UUID PRIMARY KEY,
            naam         VARCHAR(120) NOT NULL UNIQUE,
            tenant_id    UUID REFERENCES tenants(id) ON DELETE SET NULL,
            doelgroepen  VARCHAR(500) NOT NULL,
            scopes       VARCHAR(500) NOT NULL,
            is_active    BOOLEAN NOT NULL DEFAULT true,
            created_by   VARCHAR(64),
            created_at   TIMESTAMPTZ DEFAULT now(),
            last_used_at TIMESTAMPTZ
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS machine_secrets (
            id           UUID PRIMARY KEY,
            account_id   UUID NOT NULL REFERENCES machine_accounts(id) ON DELETE CASCADE,
            hash         VARCHAR(64) NOT NULL UNIQUE,
            prefix       VARCHAR(16) NOT NULL,
            created_at   TIMESTAMPTZ DEFAULT now(),
            expires_at   TIMESTAMPTZ NOT NULL,
            revoked_at   TIMESTAMPTZ,
            last_used_at TIMESTAMPTZ
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_machine_secrets_account_id ON machine_secrets (account_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS machine_secrets")
    op.execute("DROP TABLE IF EXISTS machine_accounts")
