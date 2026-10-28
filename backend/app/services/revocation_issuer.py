"""
revocation_issuer.py — de uitgeverskant van B-16: vastleggen en rondsturen.

Bij uitloggen wordt een intrekking in `session_revocations` geschreven en
`users.logout_at` gezet. Een achtergrondtaak stuurt elke
REVOCATION_HEARTBEAT_INTERVAL seconden de **volledige actuele lijst** naar elk
doel in REVOCATION_TARGETS; een logout wekt die taak direct, zodat de push en de
hartslag één mechanisme zijn.

Twee bewuste keuzes:

  * De hartslag hangt niet aan de database. Lukt het lezen niet, dan gaat de
    laatst bekende lijst rond. Een uitgever met een databasestoring blijft dus
    hartslagen sturen, in plaats van alle ontvangers muf te laten worden.
  * Is de lijst sinds het starten nog **nooit** gelezen, dan gaat er niets rond.
    Een lege lijst met een verse hartslag zou alle bekende intrekkingen wissen.
"""
from __future__ import annotations

import logging
import threading
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Optional

from app.services import session_revocation as sr

log = logging.getLogger("rhadix.revocation")

# Klokmarge bovenop de tokenlevensduur: een intrekking moet blijven bestaan tot
# elk token van vóór het uitlogmoment gegarandeerd verlopen is.
_MARGE = timedelta(minutes=5)

_lock = threading.Lock()
_laatst_bekend: Optional[list] = None      # None = sinds start nog nooit gelezen
_nog_op_te_slaan: list = []                # intrekkingen die de database niet haalden
_wek = threading.Event()
_stop = threading.Event()
_draad: Optional[threading.Thread] = None
_stand_per_doel: dict[str, dict] = {}


def _nu() -> datetime:
    return datetime.now(timezone.utc)


def _levensduur() -> timedelta:
    from app.auth.security import ACCESS_TOKEN_EXPIRE_MINUTES
    return timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES) + _MARGE


# ── vastleggen bij uitloggen ───────────────────────────────────────────────

def registreer_logout(db, sub: str, payload: Optional[dict]) -> None:
    """Leg een uitlogactie vast en wek de hartslag. Faalt nooit naar buiten:
    uitloggen moet altijd slagen, ook als de database dat niet doet."""
    from sqlalchemy import update
    from app.models.auth_models import User
    from app.models.revocation_models import SessionRevocation

    nu = _nu()
    rij = SimpleNamespace(
        jti=(payload or {}).get("jti"),
        sub=str(sub),
        not_before=nu,
        expires_at=nu + _levensduur(),
    )
    try:
        db.add(SessionRevocation(id=uuid.uuid4(), jti=rij.jti, sub=rij.sub,
                                 not_before=rij.not_before, expires_at=rij.expires_at))
        db.execute(update(User).where(User.id == uuid.UUID(rij.sub)).values(logout_at=nu))
        db.commit()
        log.info("intrekking vastgelegd (sub=%s, jti=%s)", rij.sub[:8], (rij.jti or "-")[:8])
    except Exception:
        db.rollback()
        log.exception("intrekking niet in de database — gaat mee in de hartslag "
                      "en wordt opnieuw opgeslagen (sub=%s)", rij.sub[:8])
        with _lock:
            _nog_op_te_slaan.append(rij)
    with _lock:
        if _laatst_bekend is not None:
            _laatst_bekend.append(rij)
    _wek.set()


def laatste_uitlog(db, sub: str) -> Optional[datetime]:
    """Meest recente uitlogmoment voor `sub` volgens de uitgever, of None."""
    from sqlalchemy import func
    from app.models.revocation_models import SessionRevocation

    t = db.query(func.max(SessionRevocation.not_before)).filter(
        SessionRevocation.sub == str(sub)).scalar()
    if t is not None and t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return t


# ── de actuele lijst ───────────────────────────────────────────────────────

def _sla_achterstand_op(db) -> None:
    from sqlalchemy import update
    from app.models.auth_models import User
    from app.models.revocation_models import SessionRevocation

    with _lock:
        achterstand = list(_nog_op_te_slaan)
    if not achterstand:
        return
    for r in achterstand:
        db.add(SessionRevocation(id=uuid.uuid4(), jti=r.jti, sub=r.sub,
                                 not_before=r.not_before, expires_at=r.expires_at))
        db.execute(update(User).where(User.id == uuid.UUID(r.sub)).values(logout_at=r.not_before))
    db.commit()
    with _lock:
        for r in achterstand:
            _nog_op_te_slaan.remove(r)
    log.info("%d achtergebleven intrekking(en) alsnog opgeslagen", len(achterstand))


def actuele_lijst(sessiemaker=None) -> Optional[dict]:
    """De hartslag-inhoud, of None als er nog nooit een lijst is gelezen."""
    global _laatst_bekend
    from app.models.revocation_models import SessionRevocation

    if sessiemaker is None:
        from app.database import SessionLocal as sessiemaker
    try:
        db = sessiemaker()
        try:
            _sla_achterstand_op(db)
            rijen = db.query(SessionRevocation).filter(
                SessionRevocation.expires_at > _nu()).all()
            gelezen = [SimpleNamespace(jti=r.jti, sub=r.sub, not_before=r.not_before,
                                       expires_at=r.expires_at) for r in rijen]
        finally:
            db.close()
        with _lock:
            _laatst_bekend = gelezen + list(_nog_op_te_slaan)
    except Exception:
        log.warning("intrekkingslijst niet leesbaar — laatst bekende lijst gaat rond",
                    exc_info=True)
    with _lock:
        if _laatst_bekend is None:
            return None
        return sr.bouw_lijst(list(_laatst_bekend))


# ── rondsturen ─────────────────────────────────────────────────────────────

def _verstuur(doel: str, bericht: str) -> bool:
    import httpx
    vorige = _stand_per_doel.get(doel, {})
    try:
        r = httpx.post(f"{doel}/api/internal/revocations", json={"token": bericht}, timeout=3.0)
        gelukt = r.status_code == 200
        fout = None if gelukt else f"HTTP {r.status_code}"
    except Exception as exc:
        gelukt, fout = False, type(exc).__name__
    # Alleen bij een wisseling loggen, anders vult elke 15 s de log.
    if gelukt and vorige.get("fout"):
        log.info("hartslag naar %s hersteld", doel)
    elif not gelukt and vorige.get("fout") != fout:
        log.error("hartslag naar %s mislukt: %s", doel, fout)
    _stand_per_doel[doel] = {
        "laatst_gelukt": _nu().isoformat() if gelukt else vorige.get("laatst_gelukt"),
        "laatste_poging": _nu().isoformat(),
        "fout": fout,
    }
    return gelukt


LOKAAL = "lokaal"


def _pas_lokaal_toe(lijst: dict, sessiemaker) -> bool:
    """Dezelfde `ontvang` als het endpoint, zonder netwerk en zonder handtekening:
    de lijst komt uit dit proces zelf."""
    from app.services import revocation_receiver
    if sessiemaker is None:
        from app.database import SessionLocal as sessiemaker
    vorige = _stand_per_doel.get(LOKAAL, {})
    try:
        db = sessiemaker()
        try:
            revocation_receiver.ontvang(db, lijst)
        finally:
            db.close()
        gelukt, fout = True, None
    except Exception as exc:
        gelukt, fout = False, type(exc).__name__
    if gelukt and vorige.get("fout"):
        log.info("lokale toepassing van de lijst hersteld")
    elif not gelukt and vorige.get("fout") != fout:
        log.error("lokale toepassing van de lijst mislukt: %s", fout)
    _stand_per_doel[LOKAAL] = {
        "laatst_gelukt": _nu().isoformat() if gelukt else vorige.get("laatst_gelukt"),
        "laatste_poging": _nu().isoformat(),
        "fout": fout,
    }
    return gelukt


def _heeft_werk() -> bool:
    return bool(sr.doelen()) or sr.lokaal_toepassen()


def stuur_hartslag(sessiemaker=None) -> int:
    """Eén ronde: lijst bouwen, lokaal toepassen en/of tekenen en naar elk doel
    sturen. Geeft het aantal geslaagde ontvangers."""
    if not _heeft_werk():
        return 0
    lijst = actuele_lijst(sessiemaker)
    if lijst is None:
        log.error("nog geen intrekkingslijst gelezen sinds de start — geen hartslag verstuurd")
        return 0
    geslaagd = 0
    if sr.lokaal_toepassen():
        geslaagd += _pas_lokaal_toe(lijst, sessiemaker)
    doelen = sr.doelen()
    if doelen:
        bericht = sr.teken_lijst(lijst)
        geslaagd += sum(_verstuur(d, bericht) for d in doelen)
    return geslaagd


def stand_per_doel() -> dict:
    namen = ([LOKAAL] if sr.lokaal_toepassen() else []) + sr.doelen()
    return {d: _stand_per_doel.get(d, {"laatst_gelukt": None, "fout": "nog niet geprobeerd"})
            for d in namen}


def wek() -> None:
    _wek.set()


def _lus() -> None:
    while not _stop.is_set():
        try:
            stuur_hartslag()
        except Exception:
            log.exception("hartslagronde mislukt")
        _wek.wait(sr.hartslaginterval())
        _wek.clear()


def start() -> bool:
    """Start de hartslag als er doelen zijn. Idempotent."""
    global _draad
    if sr._aan() and not sr.lokaal_toepassen():
        # Datavalidatie leest zijn eigen ontvangertabellen. Zonder lokale toepassing
        # (of het eigen adres in REVOCATION_TARGETS) worden die nooit vers, en
        # weigert controle C elke menselijke sessie — ook die van beheerders.
        log.error("SESSION_REVOCATION=on zonder REVOCATION_APPLY_LOCALLY=on: de eigen "
                  "intrekkingsstand wordt alleen vers als dit adres in REVOCATION_TARGETS staat")
    if not _heeft_werk():
        log.info("geen REVOCATION_TARGETS en geen lokale toepassing — geen hartslag")
        return False
    if _draad is not None and _draad.is_alive():
        return True
    _stop.clear()
    _draad = threading.Thread(target=_lus, name="revocation-heartbeat", daemon=True)
    _draad.start()
    log.info("hartslag gestart: elke %ss, lokaal=%s, %d extern(e) doel(en)",
             sr.hartslaginterval(), "aan" if sr.lokaal_toepassen() else "uit", len(sr.doelen()))
    return True


def stop() -> None:
    _stop.set()
    _wek.set()
