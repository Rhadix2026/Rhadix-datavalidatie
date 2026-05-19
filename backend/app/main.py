import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.router import router as auth_router
from app.routers import validate, history, reference, export, reports, profiles
from app.routers.admin import router as admin_router
from app.routers.org import router as org_router
from app.reconciliation.router import router as recon_router

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Alembic: run pending migrations on every startup.
# This is idempotent — already-applied migrations are skipped.
# ---------------------------------------------------------------------------
def _run_migrations() -> None:
    try:
        from alembic.config import Config
        from alembic import command

        ini_path = os.path.join(os.path.dirname(__file__), "..", "alembic.ini")
        cfg = Config(ini_path)
        # Override sqlalchemy.url from env so Docker credentials are always used
        cfg.set_main_option(
            "sqlalchemy.url",
            os.getenv("DATABASE_URL", "postgresql://kikv:kikv@localhost:5432/kikv_validator"),
        )
        command.upgrade(cfg, "head")
        log.info("Alembic migrations applied successfully.")
    except Exception as exc:
        # Log but don't crash: the DB may already be up to date or unavailable during
        # unit tests where there is no real Postgres instance.
        log.warning("Alembic migration skipped or failed: %s", exc)


_run_migrations()

# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(title="Rhadix Validator API", version="1.0.0")

# CORS — allow the frontend origins used in development and on the server
_allow_origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://localhost:3000",
]
_extra = os.getenv("CORS_ORIGINS", "")
if _extra:
    _allow_origins += [o.strip() for o in _extra.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Public ────────────────────────────────────────────────────────────────────
app.include_router(auth_router,       prefix="/api/auth",          tags=["Auth"])
app.include_router(reference.router,  prefix="/api/reference",     tags=["Reference"])

# ── Protected (require JWT) ───────────────────────────────────────────────────
app.include_router(validate.router,   prefix="/api/validate",      tags=["Validation"])
app.include_router(history.router,    prefix="/api/history",       tags=["History"])
app.include_router(export.router,     prefix="/api/export",        tags=["Export"])
app.include_router(reports.router,    prefix="/api/reports",       tags=["Reports"])
app.include_router(profiles.router,                                tags=["Profiles"])
app.include_router(recon_router,      prefix="/api/reconciliation", tags=["Reconciliation"])

# ── Admin (RHADIX_ADMIN only) ─────────────────────────────────────────────────
app.include_router(admin_router,      prefix="/api/admin",         tags=["Admin"])

# ── Org admin (ORG_ADMIN + RHADIX_ADMIN) ─────────────────────────────────────
app.include_router(org_router,        prefix="/api/org",           tags=["Org"])


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "Rhadix Validator"}
