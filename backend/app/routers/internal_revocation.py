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

Het geheim alleen is niet genoeg: elk gebruik van het noodgeheim moet ook van
het **interne netwerk** komen (REVOCATION_BREAKGLASS_NETWORKS) en mag niet via
een proxy zijn binnengekomen. Publiek verkeer loopt via Cloudflare en nginx, die
altijd X-Real-IP (en Cloudflare CF-Connecting-IP) meegeven; wie de backendpoort
rechtstreeks benadert, heeft een extern bronadres. Beide worden geweigerd vóórdat
het geheim wordt bekeken. Gebruik: op de server, `curl` naar de backendpoort.
"""
import ipaddress
import logging
import os
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
_PROXYKOPPEN = ("x-forwarded-for", "x-real-ip", "cf-connecting-ip", "true-client-ip", "forwarded")
_STANDAARD_NETTEN = "127.0.0.0/8,::1/128,172.16.0.0/12"


def _ip(request: Request) -> str:
    # Bewust het directe bronadres: proxykoppen zijn hier niet te vertrouwen.
    return request.client.host if request.client else "unknown"


def _interne_netten() -> list:
    netten = []
    for deel in (os.getenv("REVOCATION_BREAKGLASS_NETWORKS") or _STANDAARD_NETTEN).split(","):
        deel = deel.strip()
        if not deel:
            continue
        try:
            netten.append(ipaddress.ip_network(deel, strict=False))
        except ValueError:
            log.error("REVOCATION_BREAKGLASS_NETWORKS bevat een onleesbaar net: %r", deel)
    return netten


def _bron_is_intern(request: Request) -> bool:
    try:
        adres = ipaddress.ip_address(_ip(request))
    except ValueError:
        return False
    return any(adres in net for net in _interne_netten())


def interne_bron(request: Request) -> bool:
    """Komt de verbinding zelf van het interne netwerk? Via nginx is dat de
    docker-gateway; rechtstreeks van internet op de backendpoort niet."""
    return _bron_is_intern(request)


def intern_verzoek(request: Request) -> bool:
    """Strenger: intern bronadres én niet via een proxy (dus niet van internet)."""
    if any(k in request.headers for k in _PROXYKOPPEN):
        return False
    return _bron_is_intern(request)


def _eis_interne_bron(request: Request) -> None:
    # Tweede laag naast de loopback-binding van de poort (B-24): blijft gelden als
    # de backendpoort ooit weer publiek wordt gezet.
    if not interne_bron(request):
        log.warning("intern endpoint rechtstreeks van buiten benaderd (%s) — geweigerd", _ip(request))
        raise HTTPException(status_code=403, detail="Uitsluitend via de interne route")


def _eis_geheim(request: Request) -> None:
    """403 buiten het interne netwerk, 503 als de noodprocedure niet is
    ingericht, 429 bij te veel pogingen, 401 bij een fout of ontbrekend geheim."""
    if not intern_verzoek(request):
        audit_log(ACCESS_DENIED, request, actie="revocation_breakglass_extern")
        log.warning("noodprocedure: verzoek van buiten het interne netwerk geweigerd (%s)",
                    _ip(request))
        raise HTTPException(status_code=403, detail="Uitsluitend vanaf het interne netwerk")
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
    _eis_interne_bron(request)
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
    _eis_interne_bron(request)
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
