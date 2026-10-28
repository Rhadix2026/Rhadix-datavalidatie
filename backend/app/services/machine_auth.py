"""
machine_auth.py — uitgifte en beheer van machineaccounts (B-28).

Token (via /api/auth/machine-token, client_credentials):
    sub    = machine-id          typ = "machine"
    aud    = één doelgroep       scope = toegestane scopes (spatie-gescheiden)
    sid    = id van het gebruikte geheim
    apps   = []                  iat, jti, exp (max. 15 minuten)
Zelfde sleutel en issuer als gebruikerstokens; Datavalidatie zelf en de menselijke
routes van de resource-apps weigeren `typ=machine`.

Geheimen: `rmx_` + 43 tekens (256 bit), alleen de SHA-256 bewaard, max. twee actief,
max. 180 dagen geldig. Intrekken van een geheim of deactiveren van het account valt
onder de B-31-regel: audit + centrale intrekking op de sub.

Nooit wordt een geheim of token gelogd; alleen het prefix (eerste 8 tekens).
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.models.machine_models import MachineAccount, MachineSecret

PREFIX = "rmx_"
MAX_ACTIEF = 2
MAX_GELDIG_DAGEN = 180
TOEGESTANE_SCOPES = {"datastation:vragen", "datastation:resultaat"}


class Geweigerd(Exception):
    """Geen token. `reden` gaat naar de audit, nooit naar de aanvrager."""
    def __init__(self, reden: str):
        super().__init__(reden)
        self.reden = reden


def _nu() -> datetime:
    return datetime.now(timezone.utc)


def _utc(t: Optional[datetime]) -> Optional[datetime]:
    if t is not None and t.tzinfo is None:
        return t.replace(tzinfo=timezone.utc)
    return t


def token_minuten() -> int:
    try:
        m = int(os.getenv("MACHINE_TOKEN_MINUTES", "15"))
    except ValueError:
        m = 15
    return max(1, min(m, 15))


def _hash(geheim: str) -> str:
    return hashlib.sha256(geheim.encode()).hexdigest()


def nieuw_geheim(db, account: MachineAccount, geldig_dagen: int = MAX_GELDIG_DAGEN) -> tuple[MachineSecret, str]:
    """Maak een geheim. Geeft (rij, geheim) — het geheim alleen hier, één keer."""
    actief = [s for s in db.query(MachineSecret).filter(MachineSecret.account_id == account.id).all()
              if s.revoked_at is None and _utc(s.expires_at) > _nu()]
    if len(actief) >= MAX_ACTIEF:
        raise ValueError(f"Er zijn al {MAX_ACTIEF} actieve geheimen; trek er eerst één in")
    geheim = PREFIX + secrets.token_urlsafe(32)
    rij = MachineSecret(id=uuid.uuid4(), account_id=account.id, hash=_hash(geheim), prefix=geheim[:8],
                        expires_at=_nu() + timedelta(days=max(1, min(geldig_dagen, MAX_GELDIG_DAGEN))))
    db.add(rij)
    return rij, geheim


def controleer_scopes(scopes: list[str]) -> list[str]:
    onbekend = [s for s in scopes if s not in TOEGESTANE_SCOPES]
    if onbekend or not scopes:
        raise ValueError(f"Onbekende of lege scopes: {onbekend or scopes}")
    return scopes


def geef_token(db, client_id: str, client_secret: str, audience: Optional[str]) -> tuple[str, MachineAccount, MachineSecret, int]:
    """Controleer de credentials en geef (token, account, geheim, seconden). Gooit
    Geweigerd met een reden voor de audit; de aanvrager krijgt alleen 'ongeldig'."""
    from app.auth.security import create_access_token
    try:
        aid = uuid.UUID(str(client_id))
    except (ValueError, TypeError):
        raise Geweigerd("client_id ongeldig")
    account = db.get(MachineAccount, aid)
    if account is None:
        raise Geweigerd("onbekend account")
    if not account.is_active:
        raise Geweigerd("account gedeactiveerd")
    if not isinstance(client_secret, str) or not client_secret.startswith(PREFIX):
        raise Geweigerd("geheim heeft verkeerde vorm")
    gezocht = _hash(client_secret)
    geheim = None
    for s in db.query(MachineSecret).filter(MachineSecret.account_id == account.id).all():
        if hmac.compare_digest(s.hash, gezocht):
            geheim = s
    if geheim is None:
        raise Geweigerd("geheim onjuist")
    if geheim.revoked_at is not None:
        raise Geweigerd("geheim ingetrokken")
    if _utc(geheim.expires_at) <= _nu():
        raise Geweigerd("geheim verlopen")
    doelgroepen = account.doelgroep_lijst()
    aud = audience or (doelgroepen[0] if len(doelgroepen) == 1 else None)
    if aud is None or aud not in doelgroepen:
        raise Geweigerd(f"doelgroep niet toegestaan: {audience!r}")
    minuten = token_minuten()
    token = create_access_token({
        "sub":   str(account.id),
        "typ":   "machine",
        "aud":   aud,
        "scope": " ".join(account.scope_lijst()),
        "sid":   str(geheim.id),
        "apps":  [],
        "name":  account.naam,
    }, expires_delta=timedelta(minutes=minuten))
    geheim.last_used_at = account.last_used_at = _nu()
    db.commit()
    return token, account, geheim, minuten * 60


def waarschuw_verloop(db, dagen: int = 30) -> list[dict]:
    """Geheimen die binnen `dagen` verlopen (voor status en audit)."""
    grens = _nu() + timedelta(days=dagen)
    uit = []
    for s in db.query(MachineSecret).filter(MachineSecret.revoked_at.is_(None)).all():
        if _nu() < _utc(s.expires_at) <= grens:
            uit.append({"account_id": str(s.account_id), "sid": str(s.id), "prefix": s.prefix,
                        "verloopt": _utc(s.expires_at).isoformat()})
    return uit
