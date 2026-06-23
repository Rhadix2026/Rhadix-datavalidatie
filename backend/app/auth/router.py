"""
auth/router.py — Authentication endpoints.

POST /api/auth/login        — email + password → JWT
GET  /api/auth/me           — current user profile
PATCH /api/auth/me/password — change own password
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.audit import (
    LOGIN_BLOCKED, LOGIN_FAILURE, LOGIN_SUCCESS, LOGOUT,
    PASSWORD_CHANGED, PASSWORD_CHANGE_FAILED,
    audit_log,
)
from app.auth.brute_force import is_blocked, record_failure, record_success, seconds_until_unblocked
from app.auth.token_blocklist import block_token
from app.auth.dependencies import get_current_user
from app.auth.schemas import LoginRequest, PasswordChangeRequest, TokenResponse, UserResponse
from app.auth.security import create_access_token, hash_password, validate_password_strength, verify_password, get_jwks, ACCESS_TOKEN_EXPIRE_MINUTES
from app.database import get_db
from app.models.auth_models import User, UserApplication, UserRole

router = APIRouter(tags=["Auth"])
_bearer_scheme = HTTPBearer(auto_error=False)


def _app_slugs_for(user, db) -> list[str]:
    """Slugs van apps waartoe de gebruiker toegang heeft (RHADIX_ADMIN => alle actieve)."""
    if user.role == UserRole.RHADIX_ADMIN:
        from app.models.auth_models import Application
        return [a.slug for a in db.query(Application).filter(Application.is_active == True).all()]
    uas = db.query(UserApplication).filter(UserApplication.user_id == user.id).all()
    return [ua.application.slug for ua in uas if ua.application]


def _get_client_ip(request: Request) -> str:
    """Bepaal het echte IP-adres van de client (ook achter een proxy/Cloudflare)."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    """Authenticate with email + password and receive a JWT access token."""
    client_ip = _get_client_ip(request)

    # Brute-force check
    if is_blocked(client_ip):
        remaining = seconds_until_unblocked(client_ip)
        audit_log(LOGIN_BLOCKED, request, email=body.email, remaining_seconds=remaining)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed login attempts. Try again in {remaining} seconds.",
            headers={"Retry-After": str(remaining)},
        )

    user = db.query(User).filter(
        User.email == body.email.lower().strip(),
        User.is_active == True,
    ).first()

    if not user or not user.password_hash or not verify_password(body.password, user.password_hash):
        # Deliberate: same message for unknown user and wrong password (no enumeration)
        record_failure(client_ip)
        audit_log(LOGIN_FAILURE, request, email=body.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # Succesvolle login
    record_success(client_ip)
    audit_log(
        LOGIN_SUCCESS, request,
        user_id=str(user.id),
        email=user.email,
        tenant_id=str(user.tenant_id),
        role=user.role.value,
    )

    # Record last login
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    app_slugs = _app_slugs_for(user, db)
    token = create_access_token({
        "sub":         str(user.id),
        "role":        user.role.value,
        "tenant_id":   str(user.tenant_id),
        "tenant_name": user.tenant.name,
        "email":       user.email,
        "name":        user.full_name or user.email,
        "apps":        app_slugs,
    })
    # SSO-cookie op het gedeelde domein (alleen als SSO_COOKIE_DOMAIN gezet is,
    # bv. ".rhadix.nl"); maakt cross-app SSO mogelijk zonder opnieuw inloggen.
    import os as _os
    _dom = _os.getenv("SSO_COOKIE_DOMAIN")
    if _dom:
        response.set_cookie("rhadix_sso", token, domain=_dom, path="/",
                            httponly=True, secure=True, samesite="lax",
                            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return the profile of the currently authenticated user."""
    app_slugs = _app_slugs_for(current_user, db)

    return UserResponse(
        id                 = str(current_user.id),
        email              = current_user.email,
        full_name          = current_user.full_name,
        role               = current_user.role,
        tenant_id          = str(current_user.tenant_id),
        tenant_name        = current_user.tenant.name,
        assigned_app_slugs = app_slugs,
    )


@router.patch("/me/password", status_code=204)
def change_password(
    body: PasswordChangeRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change the current user's password."""
    if not current_user.password_hash or not verify_password(body.current_password, current_user.password_hash):
        audit_log(
            PASSWORD_CHANGE_FAILED, request,
            user_id=str(current_user.id),
            email=current_user.email,
            tenant_id=str(current_user.tenant_id),
        )
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    try:
        validate_password_strength(body.new_password)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    current_user.password_hash = hash_password(body.new_password)
    db.commit()

    audit_log(
        PASSWORD_CHANGED, request,
        user_id=str(current_user.id),
        email=current_user.email,
        tenant_id=str(current_user.tenant_id),
    )


@router.post("/logout", status_code=204)
def logout(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    current_user: User = Depends(get_current_user),
):
    """Invalideer het huidige JWT token (voeg toe aan blocklist)."""
    from app.auth.security import decode_access_token
    import time

    try:
        payload = decode_access_token(credentials.credentials)
        exp = payload.get("exp", time.time() + 3600)
        jti = payload.get("jti") or credentials.credentials
        block_token(jti, float(exp))
    except Exception:
        pass  # Token was al ongeldig — logout succesvol

    audit_log(LOGOUT, request, user_id=str(current_user.id), email=current_user.email,
              tenant_id=str(current_user.tenant_id))


@router.get("/jwks", include_in_schema=True)
def jwks():
    """Publieke sleutel(s) waarmee andere apps het centrale token kunnen verifiëren."""
    return get_jwks()
