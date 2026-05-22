"""
audit.py — Gestructureerde security audit logging voor Rhadix.

Alle security-relevante events worden als JSON naar de standaard logger
geschreven. In productie worden deze opgepikt door de container log driver
(Docker/Cloudwatch/Loki/etc.).

Gebruik:
    from app.audit import audit_log
    audit_log("login_success", request, user_id="abc", email="user@example.com")
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Optional

from fastapi import Request

logger = logging.getLogger("rhadix.audit")


# ---------------------------------------------------------------------------
# Event types — voeg hier nieuwe types toe als de applicatie groeit
# ---------------------------------------------------------------------------
LOGIN_SUCCESS          = "login_success"
LOGIN_FAILURE          = "login_failure"
LOGIN_BLOCKED          = "login_blocked"
LOGOUT                 = "logout"
PASSWORD_CHANGED       = "password_changed"
PASSWORD_CHANGE_FAILED = "password_change_failed"
USER_CREATED           = "user_created"
USER_UPDATED           = "user_updated"
USER_DELETED           = "user_deleted"
ADMIN_ACTION           = "admin_action"
ACCESS_DENIED          = "access_denied"
TOKEN_INVALID          = "token_invalid"


# ---------------------------------------------------------------------------
# Kern functie
# ---------------------------------------------------------------------------

def audit_log(
    event: str,
    request: Optional[Request] = None,
    user_id: Optional[str] = None,
    email: Optional[str] = None,
    tenant_id: Optional[str] = None,
    **extra: Any,
) -> None:
    """Schrijf een audit event naar de gestructureerde logger.

    Parameters
    ----------
    event:      Eén van de constanten bovenaan dit bestand.
    request:    FastAPI Request object (voor IP en path).
    user_id:    UUID van de betreffende gebruiker (indien bekend).
    email:      E-mailadres van de betreffende gebruiker (indien bekend).
    tenant_id:  UUID van de tenant (indien bekend).
    **extra:    Aanvullende velden die in het logrecord worden opgenomen.
    """
    record: dict[str, Any] = {
        "ts":       time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "event":    event,
    }

    if request is not None:
        record["method"] = request.method
        record["path"]   = request.url.path
        record["ip"]     = _get_ip(request)

    if user_id:
        record["user_id"]   = user_id
    if email:
        record["email"]     = email
    if tenant_id:
        record["tenant_id"] = tenant_id

    record.update(extra)

    # Stel logniveau in op WARNING voor mislukte/geblokkeerde events, anders INFO
    _warning_events = {LOGIN_FAILURE, LOGIN_BLOCKED, PASSWORD_CHANGE_FAILED, ACCESS_DENIED, TOKEN_INVALID}
    level = logging.WARNING if event in _warning_events else logging.INFO

    logger.log(level, json.dumps(record, ensure_ascii=False))


# ---------------------------------------------------------------------------
# Intern
# ---------------------------------------------------------------------------

def _get_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
