"""
auth/router.py — Authentication endpoints.

POST /api/auth/login        — email + password → JWT
GET  /api/auth/me           — current user profile
PATCH /api/auth/me/password — change own password
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.schemas import LoginRequest, PasswordChangeRequest, TokenResponse, UserResponse
from app.auth.security import create_access_token, hash_password, verify_password
from app.database import get_db
from app.models.auth_models import User, UserApplication, UserRole

router = APIRouter(tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate with email + password and receive a JWT access token."""
    user = db.query(User).filter(
        User.email == body.email.lower().strip(),
        User.is_active == True,
    ).first()

    if not user or not user.password_hash or not verify_password(body.password, user.password_hash):
        # Deliberate: same message for unknown user and wrong password (no enumeration)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # Record last login
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    token = create_access_token({
        "sub":       str(user.id),
        "role":      user.role.value,
        "tenant_id": str(user.tenant_id),
        "email":     user.email,
    })
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return the profile of the currently authenticated user."""
    # Phase 2: include assigned app slugs so the frontend can gate features
    if current_user.role == UserRole.RHADIX_ADMIN:
        # RHADIX_ADMIN sees everything — return all active app slugs
        from app.models.auth_models import Application
        all_apps = db.query(Application).filter(Application.is_active == True).all()
        app_slugs = [a.slug for a in all_apps]
    else:
        user_apps = db.query(UserApplication).filter(UserApplication.user_id == current_user.id).all()
        app_slugs = [ua.application.slug for ua in user_apps if ua.application]

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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change the current user's password."""
    if not current_user.password_hash or not verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if len(body.new_password) < 12:
        raise HTTPException(status_code=422, detail="Password must be at least 12 characters")
    current_user.password_hash = hash_password(body.new_password)
    db.commit()
