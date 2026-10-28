"""
machine.py — machineaccounts (B-28): tokenuitgifte en beheer.

  POST   /api/auth/machine-token                         client_credentials → kort token
  GET    /api/admin/machine-accounts                     overzicht (zonder geheimen)
  POST   /api/admin/machine-accounts                     aanmaken; geheim één keer terug
  POST   /api/admin/machine-accounts/{id}/secrets        extra geheim (rotatie)
  DELETE /api/admin/machine-accounts/{id}/secrets/{sid}  geheim intrekken
  PATCH  /api/admin/machine-accounts/{id}/active         (de)activeren

Beheer alleen voor RHADIX_ADMIN. Het token-endpoint is begrensd met dezelfde module
als de login (B-26): per client en per bron-IP, met blokkade na herhaald falen.
Elke uitgifte, weigering, aanmaak, rotatie en intrekking wordt geaudit; geheimen en
tokens nooit, alleen het prefix.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.audit import audit_log
from app.auth import brute_force
from app.auth.client_ip import client_ip, limiet_sleutel
from app.auth.dependencies import require_role
from app.database import get_db
from app.models.auth_models import Tenant, User, UserRole
from app.models.machine_models import MachineAccount, MachineSecret
from app.services import beveiligingsregel, machine_auth as ma

token_router = APIRouter()
beheer_router = APIRouter()
_beheerder = require_role(UserRole.RHADIX_ADMIN)

MACHINE_TOKEN_ISSUED       = "machine_token_issued"
MACHINE_TOKEN_DENIED       = "machine_token_denied"
MACHINE_ACCOUNT_CREATED    = "machine_account_created"
MACHINE_ACCOUNT_DEACTIVATED = "machine_account_deactivated"
MACHINE_ACCOUNT_REACTIVATED = "machine_account_reactivated"
MACHINE_SECRET_CREATED     = "machine_secret_created"
MACHINE_SECRET_REVOKED     = "machine_secret_revoked"


# ── tokenuitgifte ────────────────────────────────────────────────────────────
class TokenAanvraag(BaseModel):
    grant_type: str = "client_credentials"
    client_id: str = Field(max_length=64)
    client_secret: str = Field(max_length=128)
    audience: Optional[str] = Field(default=None, max_length=120)


def _ongeldig(retry: Optional[int] = None):
    headers = {"Retry-After": str(retry)} if retry else None
    raise HTTPException(429 if retry else 401, "Te veel pogingen" if retry else "Ongeldige client",
                        headers=headers)


@token_router.post("/machine-token")
def machine_token(body: TokenAanvraag, request: Request, db: Session = Depends(get_db)):
    ip = limiet_sleutel(client_ip(request))
    sleutels = (f"machine:{body.client_id}", f"machine-ip:{ip}")
    for k in sleutels:
        if brute_force.is_blocked(k):
            audit_log(MACHINE_TOKEN_DENIED, request, user_id=body.client_id, reden="geblokkeerd")
            _ongeldig(brute_force.seconds_until_unblocked(k))
    toegestaan, wacht = brute_force.verzoek_toegestaan(f"machine-ip:{ip}")
    if not toegestaan:
        audit_log(MACHINE_TOKEN_DENIED, request, user_id=body.client_id, reden="uurlimiet")
        _ongeldig(wacht)
    if body.grant_type != "client_credentials":
        raise HTTPException(400, "Alleen grant_type=client_credentials")
    try:
        token, account, geheim, seconden = ma.geef_token(db, body.client_id, body.client_secret, body.audience)
    except ma.Geweigerd as exc:
        db.rollback()
        for k in sleutels:
            brute_force.record_failure(k)
        audit_log(MACHINE_TOKEN_DENIED, request, user_id=body.client_id, reden=exc.reden)
        _ongeldig()
    for k in sleutels:
        brute_force.record_success(k)
    from jose import jwt
    claims = jwt.get_unverified_claims(token)      # net zelf uitgegeven; alleen voor de audit
    audit_log(MACHINE_TOKEN_ISSUED, request, user_id=str(account.id), naam=account.naam,
              jti=claims.get("jti"), aud=claims.get("aud"), exp=claims.get("exp"), sid_prefix=geheim.prefix)
    return {"access_token": token, "token_type": "bearer", "expires_in": seconden}


# ── beheer ───────────────────────────────────────────────────────────────────
class AccountAanmaak(BaseModel):
    naam: str = Field(min_length=3, max_length=120)
    tenant_id: Optional[str] = None
    doelgroepen: list[str] = Field(min_length=1)
    scopes: list[str] = Field(min_length=1)
    geldig_dagen: int = ma.MAX_GELDIG_DAGEN


def _account(db, account_id: str) -> MachineAccount:
    try:
        a = db.get(MachineAccount, uuid.UUID(account_id))
    except ValueError:
        a = None
    if a is None:
        raise HTTPException(404, "Machineaccount niet gevonden")
    return a


def _dict(db, a: MachineAccount) -> dict:
    geheimen = db.query(MachineSecret).filter(MachineSecret.account_id == a.id).all()
    return {
        "id": str(a.id), "naam": a.naam, "tenant_id": str(a.tenant_id) if a.tenant_id else None,
        "doelgroepen": a.doelgroep_lijst(), "scopes": a.scope_lijst(), "is_active": a.is_active,
        "last_used_at": a.last_used_at.isoformat() if a.last_used_at else None,
        "geheimen": [{"sid": str(s.id), "prefix": s.prefix,
                      "verloopt": ma._utc(s.expires_at).isoformat(),
                      "ingetrokken": s.revoked_at is not None,
                      "last_used_at": s.last_used_at.isoformat() if s.last_used_at else None}
                     for s in geheimen],
    }


@beheer_router.get("/machine-accounts")
def lijst(db: Session = Depends(get_db), _: User = Depends(_beheerder)):
    return {"accounts": [_dict(db, a) for a in db.query(MachineAccount).order_by(MachineAccount.naam).all()],
            "verloopt_binnenkort": ma.waarschuw_verloop(db)}


@beheer_router.post("/machine-accounts", status_code=201)
def aanmaken(body: AccountAanmaak, request: Request, db: Session = Depends(get_db),
             beheerder: User = Depends(_beheerder)):
    try:
        scopes = ma.controleer_scopes([s.strip() for s in body.scopes])
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    tid = None
    if body.tenant_id:
        try:
            tid = uuid.UUID(body.tenant_id)
        except ValueError:
            raise HTTPException(422, "tenant_id ongeldig")
        if db.get(Tenant, tid) is None:
            raise HTTPException(404, "Tenant niet gevonden")
    if db.query(MachineAccount).filter(MachineAccount.naam == body.naam).first():
        raise HTTPException(409, "Naam bestaat al")
    a = MachineAccount(id=uuid.uuid4(), naam=body.naam, tenant_id=tid,
                       doelgroepen=",".join(d.strip() for d in body.doelgroepen if d.strip()),
                       scopes=" ".join(scopes), is_active=True, created_by=str(beheerder.id))
    db.add(a); db.flush()
    rij, geheim = ma.nieuw_geheim(db, a, body.geldig_dagen)
    db.commit()
    audit_log(MACHINE_ACCOUNT_CREATED, request, user_id=str(a.id), naam=a.naam, door=str(beheerder.id),
              doelgroepen=a.doelgroep_lijst(), scopes=a.scope_lijst())
    audit_log(MACHINE_SECRET_CREATED, request, user_id=str(a.id), sid=str(rij.id), prefix=rij.prefix,
              door=str(beheerder.id))
    return {**_dict(db, a), "client_id": str(a.id), "client_secret": geheim,
            "let_op": "Het geheim wordt alleen nu getoond."}


@beheer_router.post("/machine-accounts/{account_id}/secrets", status_code=201)
def nieuw_geheim(account_id: str, request: Request, db: Session = Depends(get_db),
                 beheerder: User = Depends(_beheerder)):
    a = _account(db, account_id)
    try:
        rij, geheim = ma.nieuw_geheim(db, a)
    except ValueError as exc:
        raise HTTPException(409, str(exc))
    db.commit()
    audit_log(MACHINE_SECRET_CREATED, request, user_id=str(a.id), sid=str(rij.id), prefix=rij.prefix,
              door=str(beheerder.id))
    return {"sid": str(rij.id), "client_secret": geheim, "let_op": "Het geheim wordt alleen nu getoond."}


@beheer_router.delete("/machine-accounts/{account_id}/secrets/{sid}", status_code=204)
def geheim_intrekken(account_id: str, sid: str, request: Request, db: Session = Depends(get_db),
                     beheerder: User = Depends(_beheerder)):
    a = _account(db, account_id)
    try:
        s = db.get(MachineSecret, uuid.UUID(sid))
    except ValueError:
        s = None
    if s is None or s.account_id != a.id:
        raise HTTPException(404, "Geheim niet gevonden")
    if s.revoked_at is None:
        s.revoked_at = ma._nu()
        db.commit()
    # B-31: elk token van vóór dit moment vervalt (bij SESSION_REVOCATION=on).
    beveiligingsregel.toepassen(db, MACHINE_SECRET_REVOKED, a, request=request, door=beheerder,
                                sid=str(s.id), prefix=s.prefix)


class Actief(BaseModel):
    is_active: bool


@beheer_router.patch("/machine-accounts/{account_id}/active")
def actief_zetten(account_id: str, body: Actief, request: Request, db: Session = Depends(get_db),
                  beheerder: User = Depends(_beheerder)):
    a = _account(db, account_id)
    a.is_active = body.is_active
    db.commit()
    beveiligingsregel.toepassen(db, MACHINE_ACCOUNT_REACTIVATED if a.is_active else MACHINE_ACCOUNT_DEACTIVATED,
                                a, request=request, door=beheerder, intrekken=not a.is_active)
    return _dict(db, a)
