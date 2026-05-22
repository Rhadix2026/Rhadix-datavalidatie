"""
security.py — JWT creation/validation and password hashing utilities.
"""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

# ---------------------------------------------------------------------------
# Configuration (override via environment variables)
# ---------------------------------------------------------------------------

# JWT_SECRET_KEY must be set explicitly — no insecure fallback allowed.
# Generate a secure key with:
#   python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "JWT_SECRET_KEY environment variable is not set. "
        "Generate a secure key with: "
        "python -c \"import secrets; print(secrets.token_hex(32))\" "
        "and set it in your .env file or deployment secrets."
    )

ALGORITHM  = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ---------------------------------------------------------------------------
# Wachtwoordsterkte validatie
# ---------------------------------------------------------------------------

def validate_password_strength(password: str) -> None:
    """Valideer wachtwoordcomplexiteit conform BIO 9.4.3.

    Eisen:
    - Minimaal 12 tekens
    - Minimaal 1 hoofdletter
    - Minimaal 1 kleine letter
    - Minimaal 1 cijfer
    - Minimaal 1 speciaal teken (!@#$%^&*()_+-=[]{}|;:,.<>?)

    Gooit ValueError met een duidelijke melding als niet aan de eisen voldaan.
    """
    import re
    errors = []
    if len(password) < 12:
        errors.append("minimaal 12 tekens")
    if not re.search(r"[A-Z]", password):
        errors.append("minimaal 1 hoofdletter")
    if not re.search(r"[a-z]", password):
        errors.append("minimaal 1 kleine letter")
    if not re.search(r"[0-9]", password):
        errors.append("minimaal 1 cijfer")
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]", password):
        errors.append("minimaal 1 speciaal teken (!@#$%^&* etc.)")
    if errors:
        raise ValueError("Wachtwoord voldoet niet: " + ", ".join(errors) + ".")




# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT access token.

    The ``data`` dict is copied and an ``exp`` claim is added.
    Caller should pass at least ``{"sub": str(user.id), "role": user.role, "tenant_id": str(user.tenant_id)}``.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT; raises JWTError on failure."""
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
