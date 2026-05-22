import logging
import logging.config
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.router import router as auth_router
from app.routers import validate, history, reference, export, reports, profiles
from app.routers.admin import router as admin_router
from app.routers.org import router as org_router
from app.routers.dashboard import router as dashboard_router
from app.reconciliation.router import router as recon_router

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Logging configuratie
# ---------------------------------------------------------------------------
logging.config.dictConfig({
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "format": "%(message)s",
        },
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
        "audit_console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "loggers": {
        "rhadix.audit": {
            "handlers": ["audit_console"],
            "level": "INFO",
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console"],
        "level": os.getenv("LOG_LEVEL", "INFO"),
    },
})

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
        # Log at ERROR level so it is visible in `docker logs rhadix-staging-backend`.
        # We do NOT crash the process: if the DB is already up to date (e.g. the
        # migration was applied manually) the app can still serve requests.
        import traceback
        log.error(
            "Alembic migration FAILED — dashboard/history endpoints may return 500 "
            "until the schema is up to date.\n%s",
            traceback.format_exc(),
        )


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

# ── Dashboard (alle rollen, met per-endpoint autorisatie) ─────────────────────
app.include_router(dashboard_router)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "Rhadix Validator"}
