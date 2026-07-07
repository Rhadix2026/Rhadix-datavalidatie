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

# ---------------------------------------------------------------------------
# RS256 (optioneel) — centrale identiteit (SureSync ID) tekent asymmetrisch, zodat
# andere apps met de PUBLIEKE sleutel kunnen verifiëren zonder gedeeld geheim.
# Niet gezet => HS256 (huidig gedrag blijft werken).
# ---------------------------------------------------------------------------
def _load_key(name: str):
    """Lees een PEM-sleutel uit env; accepteert raw PEM óf base64 (1 regel)."""
    v = os.getenv(name)
    if not v:
        return None
    v = v.strip()
    if "BEGIN" in v:
        return v
    try:
        import base64
        return base64.b64decode(v).decode("utf-8")
    except Exception:
        return v


PRIVATE_KEY = _load_key("JWT_PRIVATE_KEY")   # PEM (RSA private) of base64
PUBLIC_KEY  = _load_key("JWT_PUBLIC_KEY")    # PEM (RSA public) of base64
KID         = os.getenv("JWT_KID", "suresync-id-1")
ISSUER      = os.getenv("JWT_ISSUER", "suresync-id")
USE_RS256   = bool(PRIVATE_KEY and PUBLIC_KEY)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT access token (RS256 als sleutels gezet zijn, anders HS256)."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode["exp"] = expire
    to_encode.setdefault("iss", ISSUER)
    if USE_RS256:
        return jwt.encode(to_encode, PRIVATE_KEY, algorithm="RS256", headers={"kid": KID})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode/valideer een JWT; ondersteunt RS256 (centrale sleutel) én HS256."""
    try:
        alg = jwt.get_unverified_header(token).get("alg")
    except Exception:
        alg = ALGORITHM
    if alg == "RS256" and PUBLIC_KEY:
        return jwt.decode(token, PUBLIC_KEY, algorithms=["RS256"], options={"verify_aud": False})
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_aud": False})


def get_jwks() -> dict:
    """JWKS met de publieke sleutel (leeg als RS256 niet geconfigureerd is)."""
    if not PUBLIC_KEY:
        return {"keys": []}
    from jose import jwk
    k = jwk.construct(PUBLIC_KEY, "RS256").to_dict()
    k.update({"use": "sig", "alg": "RS256", "kid": KID})
    return {"keys": [k]}
