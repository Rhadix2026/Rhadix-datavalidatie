"""
conftest.py — Shared pytest fixtures for Phase 1 + Phase 2 auth tests.

Uses an in-memory SQLite database with StaticPool so all sessions share one
connection and therefore one schema.  Tables are created once per session and
rows are deleted between tests via the autouse `clean_db` fixture.
"""
import uuid
import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.models.auth_models import (   # noqa: registers auth tables
    Tenant, User, UserRole,
    Application, License, TenantApplication, UserApplication,
)
from app.models.models import ValidationRun                # noqa: registers validation_runs
from app.models.task_models import Task                    # noqa: registers tasks
from app.auth.security import hash_password

# ---------------------------------------------------------------------------
# Engine — StaticPool keeps a single DBAPI connection alive so the in-memory
# database is visible to every session created by the app and by fixtures.
# ---------------------------------------------------------------------------
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(engine, "connect")
def _fk_pragma(conn, _):
    conn.execute("PRAGMA foreign_keys=ON")


TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Schema bootstrap (once per test session)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
def create_tables():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


# ---------------------------------------------------------------------------
# Seed built-in applications (once per test session)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
def seed_applications(create_tables):
    session = TestingSessionLocal()
    slugs = ["kikv-validator", "zib-validator", "algemeen-validator", "reconciliation"]
    names = ["KIK-V Validator", "ZIB Validator", "Algemene Validator", "Reconciliation Engine"]
    for i, (slug, name) in enumerate(zip(slugs, names)):
        if not session.query(Application).filter(Application.slug == slug).first():
            session.add(Application(id=uuid.uuid4(), slug=slug, name=name, sort_order=i + 1))
    session.commit()
    session.close()


# ---------------------------------------------------------------------------
# Row cleanup between tests (autouse = runs for every test function)
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def clean_db():
    yield
    with TestingSessionLocal() as s:
        s.execute(text("DELETE FROM user_applications"))
        s.execute(text("DELETE FROM tenant_applications"))
        s.execute(text("DELETE FROM licenses"))
        s.execute(text("DELETE FROM tasks"))
        s.execute(text("DELETE FROM validation_runs"))
        s.execute(text("DELETE FROM users"))
        s.execute(text("DELETE FROM tenants"))
        # applications are global seed data — do NOT delete them
        s.commit()


# ---------------------------------------------------------------------------
# FastAPI test client with DB override
# ---------------------------------------------------------------------------
@pytest.fixture()
def client():
    import app.main as main_module
    main_module.app.dependency_overrides[get_db] = override_get_db
    with TestClient(main_module.app, raise_server_exceptions=True) as c:
        yield c
    main_module.app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Shared DB session for fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Pre-seeded tenants
# ---------------------------------------------------------------------------
@pytest.fixture()
def tenant_a(db):
    t = Tenant(id=uuid.uuid4(), slug="tenant-a", name="Tenant A")
    db.add(t); db.commit(); db.refresh(t)
    return t


@pytest.fixture()
def tenant_b(db):
    t = Tenant(id=uuid.uuid4(), slug="tenant-b", name="Tenant B")
    db.add(t); db.commit(); db.refresh(t)
    return t


# ---------------------------------------------------------------------------
# Pre-seeded users
# ---------------------------------------------------------------------------
@pytest.fixture()
def user_org_user(db, tenant_a):
    u = User(
        id=uuid.uuid4(), tenant_id=tenant_a.id,
        email="user@tenant-a.nl",
        password_hash=hash_password("Correct-Password-123!"),
        role=UserRole.ORG_USER,
    )
    db.add(u); db.commit(); db.refresh(u)
    return u


@pytest.fixture()
def user_org_admin(db, tenant_a):
    u = User(
        id=uuid.uuid4(), tenant_id=tenant_a.id,
        email="admin@tenant-a.nl",
        password_hash=hash_password("Admin-Password-123!"),
        role=UserRole.ORG_ADMIN,
    )
    db.add(u); db.commit(); db.refresh(u)
    return u


@pytest.fixture()
def user_rhadix_admin(db, tenant_a):
    u = User(
        id=uuid.uuid4(), tenant_id=tenant_a.id,
        email="rhadix@rhadix.nl",
        password_hash=hash_password("Rhadix-Admin-Pass-999!"),
        role=UserRole.RHADIX_ADMIN,
    )
    db.add(u); db.commit(); db.refresh(u)
    return u


@pytest.fixture()
def user_tenant_b(db, tenant_b):
    u = User(
        id=uuid.uuid4(), tenant_id=tenant_b.id,
        email="user@tenant-b.nl",
        password_hash=hash_password("Tenant-B-Pass-123!"),
        role=UserRole.ORG_USER,
    )
    db.add(u); db.commit(); db.refresh(u)
    return u


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------
def make_token(user):
    from app.auth.security import create_access_token
    return create_access_token({
        "sub":       str(user.id),
        "role":      user.role.value,
        "tenant_id": str(user.tenant_id),
        "email":     user.email,
    })


@pytest.fixture()
def token_org_user(user_org_user):     return make_token(user_org_user)
@pytest.fixture()
def token_org_admin(user_org_admin):   return make_token(user_org_admin)
@pytest.fixture()
def token_rhadix_admin(user_rhadix_admin): return make_token(user_rhadix_admin)
@pytest.fixture()
def token_tenant_b(user_tenant_b):    return make_token(user_tenant_b)


# ---------------------------------------------------------------------------
# Phase 2 helpers — application lookup
# ---------------------------------------------------------------------------
@pytest.fixture()
def app_kikv(db):
    return db.query(Application).filter(Application.slug == "kikv-validator").first()


@pytest.fixture()
def app_zib(db):
    return db.query(Application).filter(Application.slug == "zib-validator").first()


@pytest.fixture()
def app_reconciliation(db):
    return db.query(Application).filter(Application.slug == "reconciliation").first()


# ---------------------------------------------------------------------------
# Phase 2 helpers — license + assignment factories
# ---------------------------------------------------------------------------
@pytest.fixture()
def license_a(db, tenant_a, user_rhadix_admin):
    lic = License(
        id=uuid.uuid4(),
        tenant_id=tenant_a.id,
        name="Test License A",
        created_by_id=user_rhadix_admin.id,
    )
    db.add(lic); db.commit(); db.refresh(lic)
    return lic


@pytest.fixture()
def tenant_app_kikv(db, tenant_a, app_kikv, license_a, user_rhadix_admin):
    """Assign the KIK-V app to tenant_a under license_a."""
    ta = TenantApplication(
        id=uuid.uuid4(),
        tenant_id=tenant_a.id,
        application_id=app_kikv.id,
        license_id=license_a.id,
        assigned_by_id=user_rhadix_admin.id,
    )
    db.add(ta); db.commit(); db.refresh(ta)
    return ta


@pytest.fixture()
def user_app_kikv(db, user_org_user, app_kikv, tenant_app_kikv, user_org_admin):
    """Assign the KIK-V app to user_org_user."""
    ua = UserApplication(
        id=uuid.uuid4(),
        user_id=user_org_user.id,
        application_id=app_kikv.id,
        tenant_application_id=tenant_app_kikv.id,
        assigned_by_id=user_org_admin.id,
    )
    db.add(ua); db.commit(); db.refresh(ua)
    return ua
