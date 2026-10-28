"""
opslag.py — Duurzame vastlegging van website-aanvragen.

Twee tabellen in het schema `website`:

    aanvragen         één rij per aanvraag: wat de bezoeker instuurde
    aanvraag_stappen  per aanvraag de verwerkingsstappen en hun status

Stappen en statussen
--------------------
    mail_bezoeker   het rapport aan de bezoeker (alleen bij een rapport)
    mail_intern     de melding aan ons
    crm             de registratie in het CRM

    wachtend     nog niet geprobeerd
    gelukt       afgerond
    mislukt      geprobeerd, wordt opnieuw geprobeerd
    geblokkeerd  kan nu niet (instelling ontbreekt), wordt opnieuw bekeken
    overgeslagen niet van toepassing (geen CRM-koppeling ingesteld)
    opgegeven    na het maximum aantal pogingen; vraagt handwerk

Eigen engine
------------
`WEBSITE_DATABASE_URL` wijst desgewenst naar een eigen databaserol die alleen
het schema `website` mag gebruiken. Zonder die instelling geldt `DATABASE_URL`.
Het schema staat dan wel in dezelfde database, maar deze code kent alleen zijn
eigen twee tabellen.

Schema
------
Alembic draait in deze repo niet betrouwbaar (B-23); daarom borgt `borg_schema()`
bij het opstarten het schema en de tabellen, idempotent, zoals de andere
vangnetten in `main.py`. Migratie 0008 doet hetzelfde voor wie Alembic wel
draait.
"""
from __future__ import annotations

import logging
import os
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from sqlalchemy import (
    JSON, Column, DateTime, ForeignKey, Integer, MetaData, String, create_engine,
    text,
)
from sqlalchemy.orm import declarative_base, sessionmaker

log = logging.getLogger("rhadix.website")

SCHEMA = "website"

MAIL_BEZOEKER = "mail_bezoeker"
MAIL_INTERN = "mail_intern"
CRM = "crm"

WACHTEND = "wachtend"
GELUKT = "gelukt"
MISLUKT = "mislukt"
GEBLOKKEERD = "geblokkeerd"
OVERGESLAGEN = "overgeslagen"
OPGEGEVEN = "opgegeven"

OPEN = (WACHTEND, MISLUKT, GEBLOKKEERD)
AFGEROND = (GELUKT, OVERGESLAGEN, OPGEGEVEN)

# Eigen metadata: deze Base deelt niets met app.database.Base.
Basis = declarative_base(metadata=MetaData(schema=SCHEMA))


def nu() -> datetime:
    return datetime.now(timezone.utc)


def _utc(moment: datetime | None) -> datetime | None:
    """SQLite geeft tijden zonder zone terug; behandel die als UTC."""
    if moment is not None and moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment


class Aanvraag(Basis):
    __tablename__ = "aanvragen"

    id            = Column(String(36), primary_key=True)
    soort         = Column(String(16), nullable=False)     # rapport | contact
    check_soort   = Column(String(8), nullable=True)       # data | kikv
    gegevens      = Column(JSON, nullable=False)
    aangemaakt_op = Column(DateTime(timezone=True), nullable=False, default=nu)
    bewaar_tot    = Column(DateTime(timezone=True), nullable=False, index=True)


class Stap(Basis):
    __tablename__ = "aanvraag_stappen"

    aanvraag_id        = Column(String(36), ForeignKey(f"{SCHEMA}.aanvragen.id", ondelete="CASCADE"),
                                primary_key=True)
    stap               = Column(String(24), primary_key=True)
    status             = Column(String(16), nullable=False, default=WACHTEND)
    pogingen           = Column(Integer, nullable=False, default=0)
    volgende_poging_op = Column(DateTime(timezone=True), nullable=True, index=True)
    laatste_fout       = Column(String(300), nullable=True)
    extern_id          = Column(String(64), nullable=True)
    bijgewerkt_op      = Column(DateTime(timezone=True), nullable=False, default=nu, onupdate=nu)


# ── Engine ────────────────────────────────────────────────────────────────────

_engine = None
_Sessie = None


def _zonder_schema_bij_sqlite(engine):
    # SQLite kent geen schema's; de tests draaien op SQLite.
    if engine.dialect.name == "sqlite":
        return engine.execution_options(schema_translate_map={SCHEMA: None})
    return engine


def gebruik_engine(engine) -> None:
    """Zet de engine expliciet (tests)."""
    global _engine, _Sessie
    _engine = _zonder_schema_bij_sqlite(engine)
    _Sessie = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)


def engine():
    if _engine is None:
        url = os.getenv("WEBSITE_DATABASE_URL") or os.getenv("DATABASE_URL")
        if not url:
            raise RuntimeError("geen WEBSITE_DATABASE_URL of DATABASE_URL ingesteld")
        gebruik_engine(create_engine(url, pool_pre_ping=True, pool_size=2, max_overflow=2))
    return _engine


@contextmanager
def sessie():
    engine()
    s = _Sessie()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def borg_schema() -> bool:
    """Schema en tabellen aanmaken als ze ontbreken. Werpt nooit."""
    try:
        e = engine()
        if e.dialect.name == "postgresql":
            with e.begin() as verbinding:
                # Eerst kijken: CREATE SCHEMA IF NOT EXISTS vraagt CREATE-recht
                # op de database, ook als het schema er al is. Een eigen rol met
                # alleen rechten op `website` heeft dat niet en hoeft het niet.
                bestaat = verbinding.execute(text(
                    "SELECT 1 FROM information_schema.schemata WHERE schema_name = :s"),
                    {"s": SCHEMA}).first()
                if not bestaat:
                    verbinding.execute(text(f"CREATE SCHEMA {SCHEMA}"))
        Basis.metadata.create_all(bind=e, checkfirst=True)
        log.info("Website-opslag geborgd (schema %s)", SCHEMA)
        return True
    except Exception:
        log.exception("Website-opslag kon niet worden geborgd — aanvragen worden "
                      "dan zonder opslag verwerkt")
        return False


# ── Vastleggen ────────────────────────────────────────────────────────────────

def bewaartermijn() -> timedelta:
    return timedelta(days=int(os.getenv("WEBSITE_BEWAARTERMIJN_DAGEN", "90")))


def leg_vast(soort: str, gegevens: dict, stappen: list[str], check_soort: str | None = None,
             aanvraag_id: str | None = None, uitstel: timedelta = timedelta(minutes=2),
             ) -> tuple[str, bool]:
    """Legt een aanvraag met haar stappen vast en commit.

    Geeft (id, nieuw) terug. Bestaat `aanvraag_id` al, dan is dit dezelfde
    inzending nog eens (dubbelklik, netwerkherhaling): er komt niets bij en
    `nieuw` is False.

    `uitstel` houdt de herhaaltaak even van deze stappen af, zodat de eerste
    poging in het verzoek zelf niet met de taak botst. Valt het proces tussen
    vastleggen en verwerken weg, dan pakt de taak ze na dat uitstel op.
    """
    sleutel = aanvraag_id or str(uuid.uuid4())
    moment = nu()
    with sessie() as s:
        if s.get(Aanvraag, sleutel) is not None:
            return sleutel, False
        s.add(Aanvraag(id=sleutel, soort=soort, check_soort=check_soort, gegevens=gegevens,
                       aangemaakt_op=moment, bewaar_tot=moment + bewaartermijn()))
        s.flush()
        for stap in stappen:
            s.add(Stap(aanvraag_id=sleutel, stap=stap, status=WACHTEND,
                       volgende_poging_op=moment + uitstel, bijgewerkt_op=moment))
    return sleutel, True


def haal(aanvraag_id: str) -> tuple[Aanvraag | None, dict[str, Stap]]:
    with sessie() as s:
        aanvraag = s.get(Aanvraag, aanvraag_id)
        stappen = {st.stap: st for st in
                   s.query(Stap).filter(Stap.aanvraag_id == aanvraag_id).all()}
    return aanvraag, stappen


def claim(aanvraag_id: str, stap: str, verwacht: datetime | None,
          duur: timedelta = timedelta(minutes=10)) -> bool:
    """Neemt een stap in behandeling: alleen als niemand anders hem intussen
    heeft gepakt (de geplande tijd is nog wat we lazen). Werkt op PostgreSQL en
    SQLite, zonder rijvergrendeling."""
    with sessie() as s:
        q = s.query(Stap).filter(Stap.aanvraag_id == aanvraag_id, Stap.stap == stap,
                                 Stap.status.in_(OPEN))
        q = q.filter(Stap.volgende_poging_op.is_(None) if verwacht is None
                     else Stap.volgende_poging_op == verwacht)
        return q.update({Stap.volgende_poging_op: nu() + duur},
                        synchronize_session=False) == 1


def werk_bij(aanvraag_id: str, stap: str, status: str, fout: str | None = None,
             extern_id: str | None = None, volgende: datetime | None = None,
             telt_als_poging: bool = True) -> None:
    with sessie() as s:
        rij = s.get(Stap, (aanvraag_id, stap))
        if rij is None:
            return
        rij.status = status
        if telt_als_poging:
            rij.pogingen = (rij.pogingen or 0) + 1
        rij.laatste_fout = (fout or None) and fout[:300]
        if extern_id:
            rij.extern_id = str(extern_id)[:64]
        rij.volgende_poging_op = volgende
        rij.bijgewerkt_op = nu()


def te_verwerken(limiet: int = 50) -> list[tuple[str, str, datetime | None]]:
    """Open stappen waarvan de geplande tijd is verstreken."""
    with sessie() as s:
        rijen = (s.query(Stap.aanvraag_id, Stap.stap, Stap.volgende_poging_op)
                 .filter(Stap.status.in_(OPEN))
                 .filter((Stap.volgende_poging_op.is_(None)) | (Stap.volgende_poging_op <= nu()))
                 .order_by(Stap.volgende_poging_op)
                 .limit(limiet).all())
    return [(a, st, v) for a, st, v in rijen]


def tellingen() -> dict[tuple[str, str], int]:
    """Aantal stappen per (stap, status) — alleen aantallen."""
    from sqlalchemy import func
    with sessie() as s:
        rijen = s.query(Stap.stap, Stap.status, func.count()).group_by(Stap.stap, Stap.status).all()
    return {(stap, status): aantal for stap, status, aantal in rijen}


def probleemgevallen(limiet: int = 50) -> list[dict]:
    """Stappen die niet vanzelf goedkomen of al lang openstaan, zonder
    persoonsgegevens: alleen id, stap, status, pogingen en leeftijd."""
    grens = nu() - timedelta(hours=1)
    with sessie() as s:
        rijen = (s.query(Stap, Aanvraag.soort, Aanvraag.aangemaakt_op)
                 .join(Aanvraag, Aanvraag.id == Stap.aanvraag_id)
                 .filter((Stap.status.in_((MISLUKT, GEBLOKKEERD, OPGEGEVEN)))
                         | ((Stap.status == WACHTEND) & (Aanvraag.aangemaakt_op < grens)))
                 .order_by(Aanvraag.aangemaakt_op).limit(limiet).all())
    return [{"aanvraag_id": st.aanvraag_id, "soort": soort, "stap": st.stap,
             "status": st.status, "pogingen": st.pogingen, "fout": st.laatste_fout,
             "aangemaakt_op": _utc(aangemaakt)} for st, soort, aangemaakt in rijen]


def ruim_op() -> int:
    """Verwijdert aanvragen voorbij hun bewaartermijn (stappen gaan mee)."""
    with sessie() as s:
        oud = [a for (a,) in s.query(Aanvraag.id).filter(Aanvraag.bewaar_tot < nu()).all()]
        if oud:
            s.query(Stap).filter(Stap.aanvraag_id.in_(oud)).delete(synchronize_session=False)
            s.query(Aanvraag).filter(Aanvraag.id.in_(oud)).delete(synchronize_session=False)
    return len(oud)
