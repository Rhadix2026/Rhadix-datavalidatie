"""
test_user_management.py — Tests for user management endpoints.

Covers:
  - POST   /api/org/users                          — create user in org
  - PATCH  /api/org/users/{id}/deactivate          — toggle is_active
  - DELETE /api/org/users/{id}                     — delete user
  - POST   /api/org/users/{id}/reset-password      — admin resets password

  - PATCH  /api/admin/users/{id}/deactivate        — RHADIX_ADMIN toggle
  - DELETE /api/admin/users/{id}                   — RHADIX_ADMIN delete
  - POST   /api/admin/users/{id}/reset-password    — RHADIX_ADMIN reset
"""
import uuid
import pytest
from tests.conftest import make_token
from app.models.auth_models import Tenant, User, UserRole
from app.auth.security import hash_password, verify_password


def auth(token):
    return {"Authorization": f"Bearer {token}"}


# ─── extra fixtures ───────────────────────────────────────────────────────────

@pytest.fixture()
def user_to_manage(db, tenant_a):
    """A regular ORG_USER that can be managed by org admin."""
    u = User(
        id=uuid.uuid4(), tenant_id=tenant_a.id,
        email="target@tenant-a.nl",
        password_hash=hash_password("Target-Password-123!"),
        role=UserRole.ORG_USER, is_active=True,
    )
    db.add(u); db.commit(); db.refresh(u)
    return u


# ═══════════════════════════════════════════════════════════════════════════════
# POST /api/org/users — create user
# ═══════════════════════════════════════════════════════════════════════════════

class TestCreateOrgUser:

    def test_org_admin_can_create_user(self, client, tenant_a, token_org_admin):
        resp = client.post("/api/org/users", json={
            "email": "new@tenant-a.nl",
            "full_name": "Nieuwe Gebruiker",
            "password": "NieuwWachtwoord123!",
            "role": "ORG_USER",
        }, headers=auth(token_org_admin))
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "new@tenant-a.nl"
        assert data["is_active"] is True
        assert data["role"] == "ORG_USER"

    def test_org_user_forbidden(self, client, token_org_user):
        resp = client.post("/api/org/users", json={
            "email": "hacker@tenant-a.nl",
            "password": "HackerPass123!",
        }, headers=auth(token_org_user))
        assert resp.status_code == 403

    def test_duplicate_email_rejected(self, client, user_org_user, token_org_admin):
        resp = client.post("/api/org/users", json={
            "email": user_org_user.email,
            "password": "SomePassword123!",
        }, headers=auth(token_org_admin))
        assert resp.status_code == 400

    def test_short_password_rejected(self, client, token_org_admin):
        resp = client.post("/api/org/users", json={
            "email": "short@tenant-a.nl",
            "password": "kort",
        }, headers=auth(token_org_admin))
        assert resp.status_code == 422

    def test_created_user_can_login(self, client, token_org_admin):
        client.post("/api/org/users", json={
            "email": "logintest@tenant-a.nl",
            "password": "LoginTestPass123!",
            "role": "ORG_USER",
        }, headers=auth(token_org_admin))

        resp = client.post("/api/auth/login", json={
            "email": "logintest@tenant-a.nl",
            "password": "LoginTestPass123!",
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()


# ═══════════════════════════════════════════════════════════════════════════════
# PATCH /api/org/users/{id}/deactivate
# ═══════════════════════════════════════════════════════════════════════════════

class TestDeactivateOrgUser:

    def test_org_admin_can_deactivate(self, client, user_to_manage, token_org_admin):
        resp = client.patch(f"/api/org/users/{user_to_manage.id}/deactivate",
                            headers=auth(token_org_admin))
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    def test_toggle_reactivates(self, client, user_to_manage, token_org_admin):
        # deactivate
        client.patch(f"/api/org/users/{user_to_manage.id}/deactivate",
                     headers=auth(token_org_admin))
        # reactivate
        resp = client.patch(f"/api/org/users/{user_to_manage.id}/deactivate",
                            headers=auth(token_org_admin))
        assert resp.json()["is_active"] is True

    def test_cannot_deactivate_self(self, client, user_org_admin, token_org_admin):
        resp = client.patch(f"/api/org/users/{user_org_admin.id}/deactivate",
                            headers=auth(token_org_admin))
        assert resp.status_code == 400

    def test_deactivated_user_cannot_login(self, client, user_to_manage, token_org_admin):
        client.patch(f"/api/org/users/{user_to_manage.id}/deactivate",
                     headers=auth(token_org_admin))
        resp = client.post("/api/auth/login", json={
            "email": user_to_manage.email,
            "password": "Target-Password-123!",
        })
        assert resp.status_code == 401

    def test_cross_tenant_blocked(self, client, user_tenant_b, token_org_admin):
        resp = client.patch(f"/api/org/users/{user_tenant_b.id}/deactivate",
                            headers=auth(token_org_admin))
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# DELETE /api/org/users/{id}
# ═══════════════════════════════════════════════════════════════════════════════

class TestDeleteOrgUser:

    def test_org_admin_can_delete(self, client, user_to_manage, token_org_admin):
        resp = client.delete(f"/api/org/users/{user_to_manage.id}",
                             headers=auth(token_org_admin))
        assert resp.status_code == 204

    def test_deleted_user_cannot_login(self, client, user_to_manage, token_org_admin):
        client.delete(f"/api/org/users/{user_to_manage.id}",
                      headers=auth(token_org_admin))
        resp = client.post("/api/auth/login", json={
            "email": user_to_manage.email,
            "password": "Target-Password-123!",
        })
        assert resp.status_code == 401

    def test_cannot_delete_self(self, client, user_org_admin, token_org_admin):
        resp = client.delete(f"/api/org/users/{user_org_admin.id}",
                             headers=auth(token_org_admin))
        assert resp.status_code == 400

    def test_cross_tenant_blocked(self, client, user_tenant_b, token_org_admin):
        resp = client.delete(f"/api/org/users/{user_tenant_b.id}",
                             headers=auth(token_org_admin))
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# POST /api/org/users/{id}/reset-password
# ═══════════════════════════════════════════════════════════════════════════════

class TestResetPasswordOrg:

    def test_admin_can_reset_password(self, client, user_to_manage, token_org_admin):
        resp = client.post(f"/api/org/users/{user_to_manage.id}/reset-password",
                           json={"new_password": "NieuwWachtwoord456!"},
                           headers=auth(token_org_admin))
        assert resp.status_code == 204

    def test_old_password_no_longer_works(self, client, user_to_manage, token_org_admin):
        client.post(f"/api/org/users/{user_to_manage.id}/reset-password",
                    json={"new_password": "NieuwWachtwoord456!"},
                    headers=auth(token_org_admin))
        resp = client.post("/api/auth/login", json={
            "email": user_to_manage.email,
            "password": "Target-Password-123!",   # old password
        })
        assert resp.status_code == 401

    def test_new_password_works(self, client, user_to_manage, token_org_admin):
        client.post(f"/api/org/users/{user_to_manage.id}/reset-password",
                    json={"new_password": "NieuwWachtwoord456!"},
                    headers=auth(token_org_admin))
        resp = client.post("/api/auth/login", json={
            "email": user_to_manage.email,
            "password": "NieuwWachtwoord456!",
        })
        assert resp.status_code == 200

    def test_short_password_rejected(self, client, user_to_manage, token_org_admin):
        resp = client.post(f"/api/org/users/{user_to_manage.id}/reset-password",
                           json={"new_password": "kort"},
                           headers=auth(token_org_admin))
        assert resp.status_code == 422

    def test_cross_tenant_blocked(self, client, user_tenant_b, token_org_admin):
        resp = client.post(f"/api/org/users/{user_tenant_b.id}/reset-password",
                           json={"new_password": "NieuwWachtwoord456!"},
                           headers=auth(token_org_admin))
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# RHADIX_ADMIN user management (/api/admin/users/...)
# ═══════════════════════════════════════════════════════════════════════════════

class TestAdminUserManagement:

    def test_rhadix_admin_can_deactivate_any_user(self, client, user_org_user, token_rhadix_admin):
        resp = client.patch(f"/api/admin/users/{user_org_user.id}/deactivate",
                            headers=auth(token_rhadix_admin))
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    def test_rhadix_admin_can_delete_user(self, client, user_org_user, token_rhadix_admin):
        resp = client.delete(f"/api/admin/users/{user_org_user.id}",
                             headers=auth(token_rhadix_admin))
        assert resp.status_code == 204

    def test_rhadix_admin_can_reset_password(self, client, user_org_user, token_rhadix_admin):
        resp = client.post(f"/api/admin/users/{user_org_user.id}/reset-password",
                           json={"new_password": "AdminResetPass123!"},
                           headers=auth(token_rhadix_admin))
        assert resp.status_code == 204

    def test_rhadix_admin_cannot_delete_self(self, client, user_rhadix_admin, token_rhadix_admin):
        resp = client.delete(f"/api/admin/users/{user_rhadix_admin.id}",
                             headers=auth(token_rhadix_admin))
        assert resp.status_code == 400

    def test_org_admin_cannot_use_admin_endpoint(self, client, user_org_user, token_org_admin):
        resp = client.patch(f"/api/admin/users/{user_org_user.id}/deactivate",
                            headers=auth(token_org_admin))
        assert resp.status_code == 403

    def test_nonexistent_user_returns_404(self, client, token_rhadix_admin):
        resp = client.delete(f"/api/admin/users/{uuid.uuid4()}",
                             headers=auth(token_rhadix_admin))
        assert resp.status_code == 404

    def test_admin_can_promote_user_to_rhadix_admin(self, client, user_org_user, token_rhadix_admin):
        # Voorkom single-point-of-failure: een tweede Rhadix-beheerder aanwijzen.
        resp = client.patch(f"/api/admin/users/{user_org_user.id}",
                            json={"role": "RHADIX_ADMIN"}, headers=auth(token_rhadix_admin))
        assert resp.status_code == 200
        assert resp.json()["role"] == "RHADIX_ADMIN"

    def test_org_admin_cannot_promote(self, client, user_org_user, token_org_admin):
        resp = client.patch(f"/api/admin/users/{user_org_user.id}",
                            json={"role": "RHADIX_ADMIN"}, headers=auth(token_org_admin))
        assert resp.status_code == 403
