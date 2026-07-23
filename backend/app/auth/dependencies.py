"""
dependencies.py — FastAPI dependencies for authentication and authorisation.

Usage in routers:

    # Any authenticated user
    @router.get("/")
    def my_endpoint(user: User = Depends(get_current_user)):
        ...

    # Only ORG_ADMIN or higher
    @router.post("/")
    def admin_only(user: User = Depends(require_role(UserRole.ORG_ADMIN, UserRole.RHADIX_ADMIN))):
        ...

    # Optional — returns None when no token is present (for backwards-compat endpoints)
    @router.post("/upload")
    def upload(user: Optional[User] = Depends(get_optional_user)):
        tenant_id = user.tenant_id if user else None

    # Require specific application access
    @router.post("/upload")
    def upload(user: Optional[User] = Depends(require_app_access("kikv-validator"))):
        ...  # None for anonymous demo users, User for authenticated+authorised callers
"""
import os
import uuid
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.auth.security import decode_access_token
from app.auth.token_blocklist import is_blocked as token_is_blocked
from app.database import get_db
from app.models.auth_models import Application, User, UserApplication, UserRole

_bearer = HTTPBearer(auto_error=False)

# Naam van het centrale SSO-cookie (env-gestuurd zodat staging en prod gescheiden zijn).
SSO_COOKIE_NAME = os.getenv("SSO_COOKIE_NAME", "rhadix_sso")


def _bearer_or_cookie(credentials, request):
    """Token uit de Authorization-header, anders uit het centrale rhadix_sso-cookie."""
    if credentials:
        return credentials.credentials
    if request is not None:
        return request.cookies.get(SSO_COOKIE_NAME)
    return None


# ---------------------------------------------------------------------------
# Core dependency
# ---------------------------------------------------------------------------

def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """Require a valid JWT (Bearer of centraal rhadix_sso-cookie).  Raises 401 if missing or invalid."""
    _tok = _bearer_or_cookie(credentials, request)
    if not _tok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload  = decode_access_token(_tok)
        user_id: str = payload.get("sub")
        if not user_id:
            raise ValueError("Missing sub claim")
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Controleer of het token ingetrokken is (logout)
    jti = payload.get("jti") or _tok
    if token_is_blocked(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_uuid = uuid.UUID(user_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")

    user = db.query(User).filter(User.id == user_uuid, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or deactivated")
    return user


def get_optional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Like get_current_user but returns None instead of raising when no token is provided."""
    _tok = _bearer_or_cookie(credentials, request)
    if not _tok:
        return None
    try:
        payload  = decode_access_token(_tok)
        user_id  = payload.get("sub")
        if not user_id:
            return None
        try:
            user_uuid = uuid.UUID(user_id)
        except (ValueError, AttributeError):
            return None
        return db.query(User).filter(User.id == user_uuid, User.is_active == True).first()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Role-based requirement factory
# ---------------------------------------------------------------------------

def require_role(*roles: UserRole):
    """Return a dependency that raises 403 unless the user has one of the given roles."""
    allowed = set(roles)

    def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return _check


# ---------------------------------------------------------------------------
# Application-access guard (Phase 2)
# ---------------------------------------------------------------------------

def require_app_access(app_slug: str):
    """
    Return a dependency that:
      - Returns None for unauthenticated callers (public demo flow unchanged).
      - Returns the User for RHADIX_ADMIN (unrestricted access).
      - Returns the User if they have a UserApplication for the given app slug.
      - Raises 403 if the user is authenticated but lacks access to the app.

    Usage:
        @router.post("/upload")
        async def upload(
            ...,
            current_user: Optional[User] = Depends(require_app_access("kikv-validator")),
        ):
            ...
    """
    def _check(
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
        db: Session = Depends(get_db),
    ) -> Optional[User]:
        # No token — public demo mode, let the request through
        _tok = _bearer_or_cookie(credentials, request)
        if not _tok:
            return None

        # Decode and look up user (reuse optional logic)
        try:
            payload  = decode_access_token(_tok)
            user_id  = payload.get("sub")
            if not user_id:
                return None
            user_uuid = uuid.UUID(user_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = db.query(User).filter(User.id == user_uuid, User.is_active == True).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or deactivated")

        # RHADIX_ADMIN bypasses all app-level checks
        if user.role == UserRole.RHADIX_ADMIN:
            return user

        # Look up the application by slug
        app = db.query(Application).filter(Application.slug == app_slug, Application.is_active == True).first()
        if not app:
            # App not in DB — deny access (misconfiguration)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Application '{app_slug}' not available")

        # Check UserApplication assignment
        has_access = db.query(UserApplication).filter(
            UserApplication.user_id == user.id,
            UserApplication.application_id == app.id,
        ).first()

        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You do not have access to '{app.name}'. Contact your organisation administrator.",
            )

        return user

    return _check
