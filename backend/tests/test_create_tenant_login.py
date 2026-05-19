"""
test_create_tenant_login.py — End-to-end: create org via admin endpoint → login.

Verifies that a newly created organisation's admin user can immediately log in
with the credentials supplied at creation time.
"""
import pytest
from tests.conftest import make_token
from app.models.auth_models import Tenant, User, UserRole
from app.auth.security import hash_password


def auth(token):
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Helpers — seed a RHADIX_ADMIN with its own tenant so create_tenant works
# ---------------------------------------------------------------------------

@pytest.fixture()
def rhadix_tenant(db):
    t = Tenant(id=__import__('uuid').uuid4(), slug="rhadix-platform", name="Rhadix Platform")
    db.add(t); db.commit(); db.refresh(t)
    return t


@pytest.fixture()
def rhadix_admin(db, rhadix_tenant):
    u = User(
        id=__import__('uuid').uuid4(),
        tenant_id=rhadix_tenant.id,
        email="rhadix-root@rhadix.nl",
        password_hash=hash_password("super-admin-pass-999"),
        role=UserRole.RHADIX_ADMIN,
        is_active=True,
    )
    db.add(u); db.commit(); db.refresh(u)
    return u


@pytest.fixture()
def token_root(rhadix_admin):
    return make_token(rhadix_admin)


# ===========================================================================
# Tests
# ===========================================================================

class TestCreateTenantLogin:

    def test_created_admin_can_login(self, client, rhadix_tenant, token_root):
        """Create a tenant via admin API, then log in with the new org admin credentials."""
        payload = {
            "name": "Test Zorggroep",
            "slug": "test-zorggroep",
            "admin_email": "orgadmin@testzorg.nl",
            "admin_password": "VeiligWachtwoord123!",
            "admin_full_name": "Test Beheerder",
        }

        # Step 1: Create the tenant
        resp = client.post("/api/admin/tenants/", json=payload, headers=auth(token_root))
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert "admin_user_id" in data

        # Step 2: Login with the new credentials
        login_resp = client.post("/api/auth/login", json={
            "email": "orgadmin@testzorg.nl",
            "password": "VeiligWachtwoord123!",
        })
        assert login_resp.status_code == 200, login_resp.text
        assert "access_token" in login_resp.json()

    def test_created_admin_email_case_insensitive(self, client, rhadix_tenant, token_root):
        """Login works regardless of email casing used at creation vs login."""
        payload = {
            "name": "Zorg BV",
            "slug": "zorg-bv",
            "admin_email": "Admin@ZorgBV.nl",   # mixed case at creation
            "admin_password": "ZorgBVWachtwoord99!",
        }
        client.post("/api/admin/tenants/", json=payload, headers=auth(token_root))

        # Login with all-lowercase email
        resp = client.post("/api/auth/login", json={
            "email": "admin@zorgbv.nl",
            "password": "ZorgBVWachtwoord99!",
        })
        assert resp.status_code == 200, resp.text

    def test_wrong_password_rejected(self, client, rhadix_tenant, token_root):
        """Login with wrong password returns 401."""
        payload = {
            "name": "Andere Zorg",
            "slug": "andere-zorg",
            "admin_email": "admin@andere.nl",
            "admin_password": "CorrectPassword123!",
        }
        client.post("/api/admin/tenants/", json=payload, headers=auth(token_root))

        resp = client.post("/api/auth/login", json={
            "email": "admin@andere.nl",
            "password": "WrongPassword999!",
        })
        assert resp.status_code == 401

    def test_short_password_rejected_at_creation(self, client, rhadix_tenant, token_root):
        """Tenant creation fails when admin password < 12 characters."""
        resp = client.post("/api/admin/tenants/", json={
            "name": "Korte Zorg",
            "slug": "korte-zorg",
            "admin_email": "admin@korte.nl",
            "admin_password": "kort",   # too short
        }, headers=auth(token_root))
        assert resp.status_code == 422

    def test_created_user_is_active(self, client, db, rhadix_tenant, token_root):
        """The newly created ORG_ADMIN must have is_active=True."""
        payload = {
            "name": "Actief Org",
            "slug": "actief-org",
            "admin_email": "admin@actief.nl",
            "admin_password": "ActiefWachtwoord99!",
        }
        resp = client.post("/api/admin/tenants/", json=payload, headers=auth(token_root))
        assert resp.status_code == 201
        user_id = resp.json()["admin_user_id"]

        from app.models.auth_models import User as UserModel
        import uuid as uuid_mod
        user = db.query(UserModel).filter(UserModel.id == uuid_mod.UUID(user_id)).first()
        assert user is not None
        assert user.is_active is True
        assert user.role == UserRole.ORG_ADMIN
