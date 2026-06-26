import logging
import logging.config
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.router import router as auth_router
from app.routers import validate, history, reference, export, reports, profiles, tasks
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
        # B10: geen hardcoded fallback — DATABASE_URL moet altijd zijn ingesteld
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            raise RuntimeError(
                "DATABASE_URL environment variable is not set. "
                "Set it in your .env file or deployment secrets."
            )
        cfg.set_main_option("sqlalchemy.url", db_url)
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
# Borg dat de vaste RHADIX_ADMIN in elke omgeving bestaat.
# Niet-destructief: bestaande gebruikers blijven onaangeroerd; de admin wordt
# alleen aangemaakt als die nog niet bestaat. Met AUTH_RESET=0 sla je dit over.
# ---------------------------------------------------------------------------
def _ensure_admin() -> None:
    if os.getenv("AUTH_RESET", "1").lower() in ("0", "false", "no"):
        return
    try:
        import uuid
        from app.database import SessionLocal
        from app.models.auth_models import Tenant, User, UserRole
        from app.auth.security import hash_password

        email = "admin@rhadix.nl"
        password = "Rhadixvoordezorg26!"
        db = SessionLocal()
        try:
            existing = db.query(User).filter(User.email == email).first()
            if existing:
                existing.password_hash = hash_password(password)
                existing.is_active = True
                existing.role = UserRole.RHADIX_ADMIN
                db.commit()
                return
            tenant = db.query(Tenant).filter(Tenant.slug == "rhadix-platform").first()
            if not tenant:
                tenant = Tenant(id=uuid.uuid4(), slug="rhadix-platform",
                                name="Rhadix Platform", is_active=True)
                db.add(tenant)
                db.flush()
            db.add(User(
                id=uuid.uuid4(), tenant_id=tenant.id, email=email,
                password_hash=hash_password(password), full_name="Rhadix Admin",
                role=UserRole.RHADIX_ADMIN, is_active=True,
            ))
            db.commit()
            log.info("Admin %s ensured.", email)
        finally:
            db.close()
    except Exception:
        import traceback
        log.error("Ensure admin failed:\n%s", traceback.format_exc())


_ensure_admin()


# ---------------------------------------------------------------------------
# Borg de product-Applications (centrale toegangssturing voor het hele platform).
# Idempotent; veilig op elke omgeving.
# ---------------------------------------------------------------------------
def _ensure_apps() -> None:
    try:
        import uuid
        from app.database import SessionLocal
        from app.models.auth_models import Application
        wanted = [
            ("datavalidatie", "Rhadix Datavalidatie", "Datakwaliteit & validatie (readiness scan).", 10),
            ("uitvraag",      "Rhadix Uitvraag",      "Afnemerskant: gevalideerde vragen uitzetten.", 11),
            ("datastation",   "Rhadix Datastation",   "Rekenhart: lokale SPARQL/Fuseki bij de bron.", 12),
        ]
        db = SessionLocal()
        try:
            for slug, name, desc, order in wanted:
                if not db.query(Application).filter(Application.slug == slug).first():
                    db.add(Application(id=uuid.uuid4(), slug=slug, name=name,
                                       description=desc, is_active=True, sort_order=order))
            db.commit()
        finally:
            db.close()
    except Exception:
        import traceback
        log.error("Ensure apps failed:\n%s", traceback.format_exc())


_ensure_apps()


# ---------------------------------------------------------------------------
# Borg een werkende demo-login (demo1@rhadix.nl) met app-toegang.
# Idempotent en niet-destructief; met AUTH_RESET=0 sla je dit over.
# ---------------------------------------------------------------------------
def _ensure_demo_user() -> None:
    # DEMO_SEED expliciet wint; anders standaard alleen op staging seeden.
    _demo = os.getenv("DEMO_SEED")
    if _demo is not None:
        if _demo.lower() in ("0", "false", "no"):
            return
    elif os.getenv("RHADIX_ENV", "").lower() != "staging":
        return
    try:
        import uuid
        from app.database import SessionLocal
        from app.models.auth_models import (Tenant, User, UserRole,
                                            Application, TenantApplication, UserApplication)
        from app.auth.security import hash_password

        email = "demo1@rhadix.nl"
        password = "Demogebruiker1!"
        db = SessionLocal()
        try:
            tenant = db.query(Tenant).filter(Tenant.slug == "rhadix-demo").first()
            if not tenant:
                tenant = Tenant(id=uuid.uuid4(), slug="rhadix-demo",
                                name="Rhadix Demo", is_active=True)
                db.add(tenant)
                db.flush()
            user = db.query(User).filter(User.email == email).first()
            if not user:
                user = User(id=uuid.uuid4(), tenant_id=tenant.id, email=email,
                            password_hash=hash_password(password),
                            full_name="Demo Gebruiker",
                            role=UserRole.ORG_ADMIN, is_active=True)
                db.add(user)
                db.flush()
            # App-toegang voor alle actieve applicaties (idempotent).
            for app_row in db.query(Application).filter(Application.is_active == True).all():
                ta = db.query(TenantApplication).filter(
                    TenantApplication.tenant_id == tenant.id,
                    TenantApplication.application_id == app_row.id).first()
                if not ta:
                    ta = TenantApplication(id=uuid.uuid4(), tenant_id=tenant.id,
                                           application_id=app_row.id)
                    db.add(ta)
                    db.flush()
                ua = db.query(UserApplication).filter(
                    UserApplication.user_id == user.id,
                    UserApplication.application_id == app_row.id).first()
                if not ua:
                    db.add(UserApplication(id=uuid.uuid4(), user_id=user.id,
                                           application_id=app_row.id,
                                           tenant_application_id=ta.id))
            db.commit()
            log.info("Demo-user %s geborgd met app-toegang.", email)
        finally:
            db.close()
    except Exception:
        import traceback
        log.error("Ensure demo user failed:\n%s", traceback.format_exc())


_ensure_demo_user()

# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
# B08: Swagger/ReDoc alleen beschikbaar als ENABLE_DOCS=true (nooit in productie)
_enable_docs = os.getenv("ENABLE_DOCS", "false").lower() == "true"
app = FastAPI(
    title="Rhadix Validator API",
    version="1.0.0",
    docs_url="/docs" if _enable_docs else None,
    redoc_url="/redoc" if _enable_docs else None,
    openapi_url="/openapi.json" if _enable_docs else None,
)

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
    # B09: expliciete methods en headers i.p.v. wildcard (BIO 13.1.3)
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Requested-With"],
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
app.include_router(tasks.router,      prefix="/api/tasks",         tags=["Tasks"])
app.include_router(dashboard_router)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "Rhadix Validator"}
