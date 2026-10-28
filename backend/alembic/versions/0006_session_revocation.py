"""Phase 6 — centrale sessie-intrekking (B-16 stap 2)

Uitgever: users.logout_at + session_revocations.
Ontvanger: revoked_sessions + revocation_state (één rij).

Idempotent (IF NOT EXISTS) zodat de migratie ook werkt als het startup-vangnet
`_ensure_revocation_schema` de objecten al heeft aangemaakt. Alles is additief:
bij terugdraaien van de code mogen de tabellen en de kolom blijven staan.

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-28
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS logout_at TIMESTAMPTZ")
    for tabel in ("session_revocations", "revoked_sessions"):
        extra = ", created_at TIMESTAMPTZ DEFAULT now()" if tabel == "session_revocations" else ""
        op.execute(f"""
            CREATE TABLE IF NOT EXISTS {tabel} (
                id          UUID PRIMARY KEY,
                jti         VARCHAR(64),
                sub         VARCHAR(64) NOT NULL,
                not_before  TIMESTAMPTZ,
                expires_at  TIMESTAMPTZ NOT NULL{extra}
            )
        """)
        for kolom in ("jti", "sub", "expires_at"):
            op.execute(f"CREATE INDEX IF NOT EXISTS ix_{tabel}_{kolom} ON {tabel} ({kolom})")
    op.execute("""
        CREATE TABLE IF NOT EXISTS revocation_state (
            id                  INTEGER PRIMARY KEY,
            last_heard_at       TIMESTAMPTZ,
            last_generated_at   TIMESTAMPTZ,
            grace_until         TIMESTAMPTZ,
            grace_reason        TEXT,
            grace_by            VARCHAR(255),
            grace_activated_at  TIMESTAMPTZ,
            grace_expiry_logged BOOLEAN NOT NULL DEFAULT false
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS revocation_state")
    op.execute("DROP TABLE IF EXISTS revoked_sessions")
    op.execute("DROP TABLE IF EXISTS session_revocations")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS logout_at")
