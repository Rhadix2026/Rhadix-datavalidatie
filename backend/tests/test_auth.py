"""
test_auth.py — Phase 1 authentication and authorisation tests.

Coverage:
  1. Login — success and failure cases
  2. /api/auth/me — returns correct user profile
  3. Role checks — ORG_USER cannot access admin endpoints
  4. Tenant isolation — user from tenant A cannot see tenant B's data
  5. Protected routes — 401 when no token is provided
  6. Password change
"""
import uuid
import pytest

from tests.conftest import make_token


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Login
# ═══════════════════════════════════════════════════════════════════════════════

class TestLogin:
    def test_login_success(self, client, user_org_user):
        res = client.post("/api/auth/login", json={
            "email":    "user@tenant-a.nl",
            "password": "correct-password-123",
        })
        assert res.status_code == 200
        body = res.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    def test_login_wrong_password(self, client, user_org_user):
        res = client.post("/api/auth/login", json={
            "email":    "user@tenant-a.nl",
            "password": "wrong-password",
        })
        assert res.status_code == 401
        assert "Incorrect" in res.json()["detail"]

    def test_login_unknown_email(self, client):
        res = client.post("/api/auth/login", json={
            "email":    "nobody@nowhere.com",
            "password": "doesnt-matter-123",
        })
        # Same error message as wrong password — no enumeration
        assert res.status_code == 401

    def test_login_inactive_user(self, client, db, user_org_user):
        user_org_user.is_active = False
        db.commit()
        res = client.post("/api/auth/login", json={
            "email":    "user@tenant-a.nl",
            "password": "correct-password-123",
        })
        assert res.status_code == 401
        # Restore for other tests
        user_org_user.is_active = True
        db.commit()

    def test_login_email_case_insensitive(self, client, user_org_user):
        res = client.post("/api/auth/login", json={
            "email":    "USER@TENANT-A.NL",
            "password": "correct-password-123",
        })
        assert res.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# 2. /api/auth/me
# ═══════════════════════════════════════════════════════════════════════════════

class TestMe:
    def test_me_returns_profile(self, client, token_org_user, user_org_user, tenant_a):
        res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_org_user}"})
        assert res.status_code == 200
        body = res.json()
        assert body["email"]       == "user@tenant-a.nl"
        assert body["role"]        == "ORG_USER"
        assert body["tenant_name"] == "Tenant A"

    def test_me_requires_auth(self, client):
        res = client.get("/api/auth/me")
        assert res.status_code == 401

    def test_me_rejects_invalid_token(self, client):
        res = client.get("/api/auth/me", headers={"Authorization": "Bearer this.is.garbage"})
        assert res.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Role checks
# ═══════════════════════════════════════════════════════════════════════════════

class TestRoleChecks:
    def test_org_user_cannot_access_admin_stats(self, client, token_org_user):
        res = client.get("/api/admin/stats", headers={"Authorization": f"Bearer {token_org_user}"})
        assert res.status_code == 403

    def test_org_admin_cannot_access_admin_stats(self, client, token_org_admin):
        res = client.get("/api/admin/stats", headers={"Authorization": f"Bearer {token_org_admin}"})
        assert res.status_code == 403

    def test_rhadix_admin_can_access_admin_stats(self, client, token_rhadix_admin):
        res = client.get("/api/admin/stats", headers={"Authorization": f"Bearer {token_rhadix_admin}"})
        assert res.status_code == 200
        body = res.json()
        assert "total_tenants"  in body
        assert "total_scans"    in body

    def test_rhadix_admin_can_list_tenants(self, client, token_rhadix_admin, tenant_a, tenant_b):
        res = client.get("/api/admin/tenants/", headers={"Authorization": f"Bearer {token_rhadix_admin}"})
        assert res.status_code == 200
        slugs = [t["slug"] for t in res.json()]
        assert "tenant-a" in slugs
        assert "tenant-b" in slugs

    def test_org_user_cannot_list_tenants(self, client, token_org_user):
        res = client.get("/api/admin/tenants/", headers={"Authorization": f"Bearer {token_org_user}"})
        assert res.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Tenant isolation
# ═══════════════════════════════════════════════════════════════════════════════

class TestTenantIsolation:
    def _create_run(self, db, tenant_id):
        """Insert a ValidationRun owned by the given tenant."""
        from app.models.models import ValidationRun
        run = ValidationRun(
            label="test-run",
            files=[],
            results={},
            total_rows=0,
            error_count=0,
            warn_count=0,
            score=100.0,
            status="completed",
            standard="kikv",
            tenant_id=tenant_id,
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        return run

    def test_user_sees_only_own_tenant_runs(self, client, db, token_org_user, token_tenant_b, tenant_a, tenant_b):
        run_a = self._create_run(db, tenant_a.id)
        run_b = self._create_run(db, tenant_b.id)

        # Tenant A user sees run A
        res = client.get("/api/history/", headers={"Authorization": f"Bearer {token_org_user}"})
        assert res.status_code == 200
        ids = [r["id"] for r in res.json()]
        assert run_a.id in ids
        assert run_b.id not in ids

        # Tenant B user sees run B
        res = client.get("/api/history/", headers={"Authorization": f"Bearer {token_tenant_b}"})
        assert res.status_code == 200
        ids = [r["id"] for r in res.json()]
        assert run_b.id in ids
        assert run_a.id not in ids

    def test_user_cannot_fetch_other_tenant_run_directly(self, client, db, token_org_user, tenant_b):
        run_b = self._create_run(db, tenant_b.id)
        res = client.get(f"/api/history/{run_b.id}", headers={"Authorization": f"Bearer {token_org_user}"})
        assert res.status_code == 404

    def test_rhadix_admin_sees_all_runs(self, client, db, token_rhadix_admin, tenant_a, tenant_b):
        run_a = self._create_run(db, tenant_a.id)
        run_b = self._create_run(db, tenant_b.id)
        res = client.get("/api/history/", headers={"Authorization": f"Bearer {token_rhadix_admin}"})
        assert res.status_code == 200
        ids = [r["id"] for r in res.json()]
        assert run_a.id in ids
        assert run_b.id in ids


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Protected routes — no token
# ═══════════════════════════════════════════════════════════════════════════════

class TestProtectedRoutes:
    @pytest.mark.parametrize("method,url", [
        ("GET",  "/api/history/"),
        ("GET",  "/api/history/stats/summary"),
        ("GET",  "/api/history/1"),
        ("GET",  "/api/admin/stats"),
        ("GET",  "/api/admin/tenants/"),
    ])
    def test_unauthenticated_returns_401(self, client, method, url):
        res = client.request(method, url)
        assert res.status_code == 401, f"Expected 401 for {method} {url}, got {res.status_code}"

    def test_health_is_public(self, client):
        """The health endpoint must never require authentication."""
        res = client.get("/api/health")
        assert res.status_code == 200

    def test_login_is_public(self, client):
        """Login endpoint must be accessible without a token."""
        res = client.post("/api/auth/login", json={"email": "x@x.com", "password": "y"})
        # We expect 401 (wrong creds) not 422 or 500
        assert res.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Password change
# ═══════════════════════════════════════════════════════════════════════════════

class TestPasswordChange:
    def test_change_password_success(self, client, db, user_org_user, token_org_user):
        res = client.patch(
            "/api/auth/me/password",
            json={"current_password": "correct-password-123", "new_password": "new-password-456-ok"},
            headers={"Authorization": f"Bearer {token_org_user}"},
        )
        assert res.status_code == 204

        # Can now login with new password
        res2 = client.post("/api/auth/login", json={"email": "user@tenant-a.nl", "password": "new-password-456-ok"})
        assert res2.status_code == 200

        # Restore original password
        res3 = client.patch(
            "/api/auth/me/password",
            json={"current_password": "new-password-456-ok", "new_password": "correct-password-123"},
            headers={"Authorization": f"Bearer {token_org_user}"},
        )
        assert res3.status_code == 204

    def test_change_password_wrong_current(self, client, token_org_user):
        res = client.patch(
            "/api/auth/me/password",
            json={"current_password": "completely-wrong", "new_password": "new-password-456-ok"},
            headers={"Authorization": f"Bearer {token_org_user}"},
        )
        assert res.status_code == 400

    def test_change_password_too_short(self, client, token_org_user):
        res = client.patch(
            "/api/auth/me/password",
            json={"current_password": "correct-password-123", "new_password": "short"},
            headers={"Authorization": f"Bearer {token_org_user}"},
        )
        assert res.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Admin — create tenant
# ═══════════════════════════════════════════════════════════════════════════════

class TestAdminCreateTenant:
    def test_rhadix_admin_can_create_tenant(self, client, token_rhadix_admin):
        res = client.post(
            "/api/admin/tenants/",
            json={
                "name":             "New Hospital",
                "slug":             "new-hospital",
                "admin_email":      "admin@newhospital.nl",
                "admin_password":   "secure-pass-word-99",
                "admin_full_name":  "New Admin",
            },
            headers={"Authorization": f"Bearer {token_rhadix_admin}"},
        )
        assert res.status_code == 201
        body = res.json()
        assert body["slug"] == "new-hospital"
        assert "id" in body

    def test_duplicate_slug_rejected(self, client, token_rhadix_admin, tenant_a):
        res = client.post(
            "/api/admin/tenants/",
            json={
                "name":           "Another Tenant A",
                "slug":           "tenant-a",   # already exists
                "admin_email":    "other@a.nl",
                "admin_password": "another-pass-word-99",
            },
            headers={"Authorization": f"Bearer {token_rhadix_admin}"},
        )
        assert res.status_code == 400

    def test_short_password_rejected(self, client, token_rhadix_admin):
        res = client.post(
            "/api/admin/tenants/",
            json={
                "name":           "Short Pass Org",
                "slug":           "short-pass-org",
                "admin_email":    "x@shortpass.nl",
                "admin_password": "tooshort",
            },
            headers={"Authorization": f"Bearer {token_rhadix_admin}"},
        )
        assert res.status_code == 422
