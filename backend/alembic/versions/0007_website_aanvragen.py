"""Phase 7 — website-aanvragen eerst vastleggen, dan verwerken

Eigen schema `website` met twee tabellen: `aanvragen` en `aanvraag_stappen`.
Raakt geen enkele tabel van Datavalidatie.

Idempotent (IF NOT EXISTS) zodat de migratie ook werkt als het startup-vangnet
`app.website.opslag.borg_schema` de objecten al heeft aangemaakt. Alles is
additief: bij terugdraaien van de code mag het schema blijven staan.

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
    op.execute("CREATE SCHEMA IF NOT EXISTS website")
    op.execute("""
        CREATE TABLE IF NOT EXISTS website.aanvragen (
            id            VARCHAR(36) PRIMARY KEY,
            soort         VARCHAR(16) NOT NULL,
            check_soort   VARCHAR(8),
            gegevens      JSON NOT NULL,
            aangemaakt_op TIMESTAMPTZ NOT NULL,
            bewaar_tot    TIMESTAMPTZ NOT NULL
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_website_aanvragen_bewaar_tot "
               "ON website.aanvragen (bewaar_tot)")
    op.execute("""
        CREATE TABLE IF NOT EXISTS website.aanvraag_stappen (
            aanvraag_id        VARCHAR(36) NOT NULL
                               REFERENCES website.aanvragen (id) ON DELETE CASCADE,
            stap               VARCHAR(24) NOT NULL,
            status             VARCHAR(16) NOT NULL,
            pogingen           INTEGER NOT NULL DEFAULT 0,
            volgende_poging_op TIMESTAMPTZ,
            laatste_fout       VARCHAR(300),
            extern_id          VARCHAR(64),
            bijgewerkt_op      TIMESTAMPTZ NOT NULL,
            PRIMARY KEY (aanvraag_id, stap)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_website_aanvraag_stappen_volgende_poging_op "
               "ON website.aanvraag_stappen (volgende_poging_op)")


def downgrade() -> None:
    # Bewust leeg: de aanvragen zijn gegevens van bezoekers, die gooien we niet
    # weg met een code-rollback. Opruimen gebeurt via de bewaartermijn.
    pass
