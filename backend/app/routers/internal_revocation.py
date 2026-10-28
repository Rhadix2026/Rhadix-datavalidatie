"""
internal_revocation.py — de drie interne endpoints van B-16.

    POST /api/internal/revocations        ontvangen; geautoriseerd door de handtekening
                                          van de uitgever op het lijstbericht
    POST /api/internal/revocation-grace   noodprocedure; uitsluitend met het eigen
                                          voorgedeelde geheim, nooit met een sessie
    GET  /api/internal/revocation-status  stand; met het geheim of als RHADIX_ADMIN

Geen van de drie gebruikt de gebruikersauthenticatie als voorwaarde. Dat is
nodig: juist als het beeld muf is, weigert controle C ook de sessie van de
beheerder, en moet de nooduitgang toch bereikbaar zijn.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.audit import ADMIN_ACTION, ACCESS_DENIED, audit_log
from app.auth import brute_force
from app.database import get_db
from app.services import revocation_issuer, revocation_receiver
from app.services import session_revocation as sr

log = logging.getLogger("rhadix.revocation")
router = APIRouter()
_bearer = HTTPBearer(auto_error=False)

GEHEIM_HEADER = "X-Revocation-Breakglass"


def _ip(request: Request) -> str:
    fwd = request.headers.get("X-Forwarded-For")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _eis_geheim(request: Request) -> None:
    """503 als de noodprocedure niet is ingericht, 429 bij te veel pogingen,
    401 bij een fout of ontbrekend geheim."""
    if sr.noodgeheim() is None:
        raise HTTPException(status_code=503, detail="Noodprocedure is niet ingericht")
    sleutel = f"breakglass:{_ip(request)}"
    if brute_force.is_blocked(sleutel):
        raise HTTPException(status_code=429, detail="Te veel mislukte pogingen")
    if not sr.geheim_klopt(request.headers.get(GEHEIM_HEADER)):
        brute_force.record_failure(sleutel)
        audit_log(ACCESS_DENIED, request, actie="revocation_breakglass")
        log.warning("noodprocedure: geweigerde poging vanaf %s", _ip(request))
        raise HTTPException(status_code=401, detail="Niet geautoriseerd")
    brute_force.record_success(sleutel)


@router.post("/revocations")
async def ontvang_intrekkingen(request: Request, db: Session = Depends(get_db)):
    try:
        body = await request.json()
        claims = sr.lees_lijst(str((body or {}).get("token") or ""))
    except Exception as exc:
        log.warning("intrekkingslijst geweigerd: %s", exc)
        raise HTTPException(status_code=401, detail="Ongeldig lijstbericht")
    try:
        return revocation_receiver.ontvang(db, claims)
    except revocation_receiver.Verouderd as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/revocation-grace")
async def noodprocedure(request: Request, db: Session = Depends(get_db)):
    _eis_geheim(request)
    try:
        body = await request.json()
    except Exception:
        body = None
    try:
        duur, reden, door = sr.toets_noodverzoek(body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    stand = revocation_receiver.activeer_noodmarge(db, duur, reden, door)
    audit_log(ADMIN_ACTION, request, actie="revocation_grace", uitgevoerd_door=door,
              reden=reden, tot=stand["noodprocedure"]["tot"])
    return stand


@router.get("/revocation-status")
def intrekkingsstatus(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
):
    if request.headers.get(GEHEIM_HEADER):
        _eis_geheim(request)
    else:
        from app.auth.dependencies import get_current_user
        from app.models.auth_models import UserRole
        gebruiker = get_current_user(request, credentials, db)
        if gebruiker.role != UserRole.RHADIX_ADMIN:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
    uit = revocation_receiver.status(db)
    uit["uitgever"] = {
        "hartslaginterval_seconden": sr.hartslaginterval(),
        "doelen": revocation_issuer.stand_per_doel(),
    }
    return uit
