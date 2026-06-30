"""Phase 5 — Auth-tokens + users.email_verified

Auth-flows via e-mail: wachtwoord-reset, uitnodiging, e-mailverificatie.
Idempotent (IF NOT EXISTS) zodat de migratie ook werkt als het startup-vangnet
de objecten al heeft aangemaakt.

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-30
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT true")
    op.execute("""
        CREATE TABLE IF NOT EXISTS auth_tokens (
            id          UUID PRIMARY KEY,
            user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            purpose     VARCHAR(20)  NOT NULL,
            token_hash  VARCHAR(64)  NOT NULL,
            expires_at  TIMESTAMPTZ  NOT NULL,
            used_at     TIMESTAMPTZ,
            created_at  TIMESTAMPTZ DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_auth_tokens_user_id    ON auth_tokens (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_auth_tokens_token_hash ON auth_tokens (token_hash)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS auth_tokens")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS email_verified")
