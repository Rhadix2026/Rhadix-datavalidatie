"""
revocation_receiver.py — de ontvangerskant van B-16: opslaan, beoordelen, noodmarge.

Dit is de kant die Uitvraag, Datastation en CRM in stap 4–6 krijgen; in
Datavalidatie staat hij er ook, omdat Datavalidatie uitgever én resource is.

De waarheid staat op schijf (`revoked_sessions`, `revocation_state`). Een
herstart laat controle A en B dus onmiddellijk werken, en laat `last_heard_at`
staan op wat het was — nooit op "nu". Een app die nog niets heeft gehoord, is muf.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from app.services import session_revocation as sr

log = logging.getLogger("rhadix.revocation")


def _nu() -> datetime:
    return datetime.now(timezone.utc)


def _utc(t: Optional[datetime]) -> Optional[datetime]:
    if t is not None and t.tzinfo is None:
        return t.replace(tzinfo=timezone.utc)
    return t


def _stand(db, voor_wijziging: bool = False):
    from app.models.revocation_models import RevocationState

    q = db.query(RevocationState).filter(RevocationState.id == 1)
    if voor_wijziging:
        q = q.with_for_update()
    stand = q.first()
    if stand is None and voor_wijziging:
        stand = RevocationState(id=1, grace_expiry_logged=False)
        db.add(stand)
        db.flush()
    return stand


# ── ontvangen ──────────────────────────────────────────────────────────────

class Verouderd(Exception):
    """Een lijst die ouder is dan wat we al hebben. Nooit toepassen: anders kan
    een opnieuw afgespeeld bericht nieuwere intrekkingen wissen."""


def ontvang(db, claims: dict[str, Any], nu: Optional[datetime] = None) -> dict:
    """Vervang de lokale lijst door de aangeleverde volledige lijst."""
    from app.models.revocation_models import RevokedSession

    nu = nu or _nu()
    gemaakt = sr.lees_tijd(claims.get("generated_at"))
    if gemaakt is None:
        raise ValueError("generated_at ontbreekt")
    if gemaakt > nu + sr.MAX_KLOKVERSCHIL:
        raise ValueError("generated_at ligt in de toekomst")

    stand = _stand(db, voor_wijziging=True)
    vorige = _utc(stand.last_generated_at)
    if vorige is not None and gemaakt < vorige:
        db.rollback()
        raise Verouderd(f"lijst van {gemaakt.isoformat()} is ouder dan {vorige.isoformat()}")

    rijen = []
    for item in claims.get("revocations") or []:
        if not isinstance(item, dict) or not item.get("sub"):
            raise ValueError("onleesbare intrekking in de lijst")
        verloopt = sr.lees_tijd(item.get("expires_at"))
        if verloopt is None or verloopt <= nu:
            continue
        jti = item.get("jti")
        rijen.append(RevokedSession(
            id=uuid.uuid4(),
            jti=str(jti)[:64] if jti else None,
            sub=str(item["sub"])[:64],
            not_before=sr.lees_tijd(item.get("not_before")),
            expires_at=verloopt,
        ))

    # Een intrekking die nog niet verlopen is, blijft staan, ook als de nieuwe lijst
    # haar niet meer bevat (bijv. een uitgever die van een oudere back-up draait).
    # Zo kan een ingetrokken token nooit opnieuw geldig worden; de lijst groeit
    # hooguit tot de vervaltijd van die rijen (tokenlevensduur + marge).
    nieuw = {(r.sub, r.jti, r.not_before) for r in rijen}
    behouden = 0
    for oud in db.query(RevokedSession).filter(RevokedSession.expires_at > nu).all():
        sleutel = (oud.sub, oud.jti, _utc(oud.not_before))
        if sleutel not in nieuw:
            rijen.append(RevokedSession(id=uuid.uuid4(), jti=oud.jti, sub=oud.sub,
                                        not_before=_utc(oud.not_before), expires_at=_utc(oud.expires_at)))
            behouden += 1
    if behouden:
        log.warning("%d nog geldige intrekking(en) ontbraken in de nieuwe lijst en blijven staan", behouden)
    db.query(RevokedSession).delete(synchronize_session=False)
    db.add_all(rijen)
    stand.last_generated_at = gemaakt
    # De uitgever wist op `generated_at` wat er in de lijst staat; daarop meten
    # we de versheid, niet op het moment van aankomst.
    stand.last_heard_at = min(gemaakt, nu)
    db.commit()
    return {"ontvangen": len(rijen), "generated_at": gemaakt.isoformat()}


# ── beoordelen (aangeroepen vanuit get_current_user) ───────────────────────

def _is_machine(payload: dict) -> bool:
    return payload.get("typ") == "client" or payload.get("scope") == "external"


def _meld_verlopen_noodmarge(db, stand, nu: datetime) -> None:
    tot = _utc(stand.grace_until)
    if tot is None or nu < tot or stand.grace_expiry_logged:
        return
    log.warning("noodprocedure verlopen om %s (was geactiveerd door %r: %s) — "
                "terug naar fail-closed", tot.isoformat(), stand.grace_by, stand.grace_reason)
    try:
        stand.grace_expiry_logged = True
        db.commit()
    except Exception:
        db.rollback()


def beoordeel(payload: dict, db, nu: Optional[datetime] = None) -> sr.Uitkomst:
    """A, B en C voor een menselijke sessie. Met SESSION_REVOCATION=off wordt
    er niets gelezen en niets geweigerd: gedrag als vandaag."""
    from sqlalchemy import or_
    from app.models.revocation_models import RevokedSession

    if not sr._aan() or _is_machine(payload):
        return sr.TOEGESTAAN
    nu = nu or _nu()
    jti = payload.get("jti")
    sub = str(payload.get("sub") or "")
    try:
        stand = _stand(db)
        voorwaarden = [RevokedSession.sub == sub]
        if jti:
            voorwaarden.append(RevokedSession.jti == str(jti))
        rijen = db.query(RevokedSession).filter(
            or_(*voorwaarden), RevokedSession.expires_at > nu).all()
    except Exception:
        log.exception("intrekkingsstatus niet leesbaar — sessie geweigerd")
        return sr.Uitkomst(False, "Intrekkingsstatus is niet actueel", "C")

    jtis = {r.jti for r in rijen if r.jti}
    momenten = [_utc(r.not_before) for r in rijen if r.sub == sub and r.not_before is not None]
    logout_at = max(momenten) if momenten else None

    if stand is not None:
        _meld_verlopen_noodmarge(db, stand, nu)
    return sr.controleer(
        payload,
        ingetrokken_jtis=jtis,
        logout_at_voor_sub=lambda s: logout_at,
        laatst_gehoord=_utc(stand.last_heard_at) if stand else None,
        noodmarge_tot=_utc(stand.grace_until) if stand else None,
        nu=nu,
    )


# ── noodprocedure ──────────────────────────────────────────────────────────

def activeer_noodmarge(db, duur_minuten: int, reden: str, door: str,
                       nu: Optional[datetime] = None) -> dict:
    """Versoepel uitsluitend controle C, tijdelijk. Een nieuwe aanroep vervangt
    de vorige, met een eigen reden en logregel; nooit langer dan het maximum."""
    if not 1 <= duur_minuten <= sr.MAX_NOODDUUR_MINUTEN:
        raise ValueError("duur buiten de grens")
    nu = nu or _nu()
    stand = _stand(db, voor_wijziging=True)
    stand.grace_until = nu + timedelta(minutes=duur_minuten)
    stand.grace_reason = reden
    stand.grace_by = door
    stand.grace_activated_at = nu
    stand.grace_expiry_logged = False
    db.commit()
    log.warning("NOODPROCEDURE GEACTIVEERD door %r tot %s — reden: %s. Controle C "
                "versoepeld; A en B blijven gelden.", door, stand.grace_until.isoformat(), reden)
    return status(db, nu=nu)


def status(db, nu: Optional[datetime] = None) -> dict:
    nu = nu or _nu()
    stand = _stand(db)
    if stand is not None:
        _meld_verlopen_noodmarge(db, stand, nu)
    gehoord = _utc(stand.last_heard_at) if stand else None
    leeftijd = (nu - gehoord).total_seconds() if gehoord else None
    tot = _utc(stand.grace_until) if stand else None
    from app.models.revocation_models import RevokedSession
    return {
        "session_revocation": "on" if sr._aan() else "off",
        "laatst_gehoord": gehoord.isoformat() if gehoord else None,
        "leeftijd_seconden": round(leeftijd, 1) if leeftijd is not None else None,
        "versheidsbudget_seconden": sr.versheidsbudget(),
        "vers": leeftijd is not None and leeftijd <= sr.versheidsbudget(),
        "aantal_intrekkingen": db.query(RevokedSession).filter(
            RevokedSession.expires_at > nu).count(),
        "noodprocedure": {
            "actief": tot is not None and nu < tot,
            "tot": tot.isoformat() if tot else None,
            "door": stand.grace_by if stand else None,
            "reden": stand.grace_reason if stand else None,
            "geactiveerd_op": _utc(stand.grace_activated_at).isoformat()
                              if stand and stand.grace_activated_at else None,
        },
    }
