"""
Rhadix Licentieserver
=====================
Beheert en valideert licentiesleutels voor Rhadix-installaties.

Endpoints:
  POST /license/validate   — klantinstantie valideert sleutel bij opstart
  POST /license/create     — admin maakt nieuwe licentie aan
  GET  /license/list       — admin lijst alle licenties
  GET  /health             — uptime check (UptimeRobot)
"""

from __future__ import annotations
import os, secrets, hashlib
from datetime import date, datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3

# ── Config ────────────────────────────────────────────────────────────────────
DB_PATH    = os.getenv("LICENSE_DB", "/data/licenses.db")
ADMIN_KEY  = os.getenv("ADMIN_KEY", "change-this-admin-key")   # instellen via .env

app = FastAPI(title="Rhadix Licentieserver", version="1.0.0", docs_url=None, redoc_url=None)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["POST", "GET"])


# ── Database setup ────────────────────────────────────────────────────────────

def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
    finally:
        con.close()


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS licenses (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            key           TEXT UNIQUE NOT NULL,
            customer_name TEXT NOT NULL,
            customer_email TEXT NOT NULL,
            created_at    TEXT NOT NULL,
            expires_at    TEXT NOT NULL,
            active        INTEGER NOT NULL DEFAULT 1,
            last_seen     TEXT,
            last_version  TEXT,
            notes         TEXT
        )
    """)
    con.commit()
    con.close()


init_db()


# ── Admin authenticatie ───────────────────────────────────────────────────────

def require_admin(x_admin_key: str = Header(...)):
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Ongeldige admin-sleutel")


# ── Schemas ───────────────────────────────────────────────────────────────────

class ValidateRequest(BaseModel):
    license_key: str
    version:     Optional[str] = None


class CreateRequest(BaseModel):
    customer_name:  str
    customer_email: str
    expires_at:     str          # ISO-datum bijv. "2027-05-08"
    notes:          Optional[str] = None


# ── Hulpfunctie ───────────────────────────────────────────────────────────────

def generate_key() -> str:
    """Genereert een unieke licentiesleutel in formaat XXXX-XXXX-XXXX-XXXX."""
    raw = secrets.token_hex(8).upper()
    return f"{raw[0:4]}-{raw[4:8]}-{raw[8:12]}-{raw[12:16]}"


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.post("/license/validate")
def validate(req: ValidateRequest, db: sqlite3.Connection = Depends(get_db)):
    """
    Valideert een licentiesleutel.
    Wordt aangeroepen door de Rhadix-backend bij elke opstart.
    """
    row = db.execute(
        "SELECT * FROM licenses WHERE key = ?", (req.license_key,)
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Licentiesleutel niet gevonden")

    if not row["active"]:
        raise HTTPException(status_code=403, detail="Licentie is gedeactiveerd")

    expires = date.fromisoformat(row["expires_at"])
    if expires < date.today():
        raise HTTPException(status_code=403, detail=f"Licentie verlopen op {expires}")

    # Registreer laatste contact
    db.execute(
        "UPDATE licenses SET last_seen = ?, last_version = ? WHERE key = ?",
        (datetime.utcnow().isoformat(), req.version, req.license_key)
    )
    db.commit()

    return {
        "valid":         True,
        "customer_name": row["customer_name"],
        "expires_at":    row["expires_at"],
        "days_remaining": (expires - date.today()).days,
    }


@app.post("/license/create", dependencies=[Depends(require_admin)])
def create(req: CreateRequest, db: sqlite3.Connection = Depends(get_db)):
    """Maakt een nieuwe licentie aan (alleen voor admin)."""
    key = generate_key()
    db.execute(
        """INSERT INTO licenses (key, customer_name, customer_email, created_at, expires_at, notes)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (key, req.customer_name, req.customer_email,
         date.today().isoformat(), req.expires_at, req.notes)
    )
    db.commit()
    return {
        "license_key":    key,
        "customer_name":  req.customer_name,
        "customer_email": req.customer_email,
        "expires_at":     req.expires_at,
    }


@app.get("/license/list", dependencies=[Depends(require_admin)])
def list_licenses(db: sqlite3.Connection = Depends(get_db)):
    """Lijst alle licenties (alleen voor admin)."""
    rows = db.execute(
        "SELECT * FROM licenses ORDER BY created_at DESC"
    ).fetchall()
    return [dict(r) for r in rows]


@app.post("/license/deactivate/{license_id}", dependencies=[Depends(require_admin)])
def deactivate(license_id: int, db: sqlite3.Connection = Depends(get_db)):
    """Deactiveert een licentie."""
    db.execute("UPDATE licenses SET active = 0 WHERE id = ?", (license_id,))
    db.commit()
    return {"deactivated": license_id}
