"""
test_licenses.py — Phase 2 license, application and access control tests.

Coverage:
  1. License creation (RHADIX_ADMIN only)
  2. Application listing
  3. Org-app assignment (RHADIX_ADMIN assigns app to tenant)
  4. User-app assignment (ORG_ADMIN assigns app to user)
  5. Unauthorized access — ORG_USER blocked without app assignment
  6. Cross-tenant isolation — ORG_ADMIN cannot touch another tenant's users
  7. Validation run linkage — application_id + license_id stored correctly
  8. /api/auth/me returns assigned_app_slugs
"""
import uuid
import pytest

from tests.conftest import make_token


# ═══════════════════════════════════════════════════════════════════════════════
# 1. License creation
# ═══════════════════════════════════════════════════════════════════════════════

class TestLicenseCreation:
    def test_rhadix_admin_can_create_license(self, client, token_rhadix_admin, tenant_a):
        res = client.post(
            "/api/admin/licenses/",
            json={"tenant_id": str(tenant_a.id), "name": "Jaarlicentie 2026"},
            headers={"Authorization": f"Bearer {token_rhadix_admin}"},
        )
        assert res.status_code == 201, res.text
        body = res.json()
        assert body["name"] == "Jaarlicentie 2026"
        assert body["tenant_id"] == str(tenant_a.id)
        assert body["is_active"] is True
        assert "id" in body

    def test_license_with_expiry(self, client, token_rhadix_admin, tenant_a):
        res = client.post(
            "/api/admin/licenses/",
            json={
                "tenant_id":   str(tenant_a.id),
                "name":        "Tijdelijke licentie",
                "valid_until": "2027-01-01T00:00:00",
                "max_users":   5,
                "notes":       "Test notes",
            },
            headers={"Authorization": f"Bearer {token_rhadix_admin}"},
        )
        assert res.status_code == 201
        body = res.json()
        assert body["max_users"] == 5
        assert body["notes"] == "Test notes"
        assert body["valid_until"] is not None

    def test_org_user_cannot_create_license(self, client, token_org_user, tenant_a):
        res = client.post(
            "/api/admin/licenses/",
            json={"tenant_id": str(tenant_a.id), "name": "Illegale licentie"},
            headers={"Authorization": f"Bearer {token_org_user}"},
        )
        assert res.status_code == 403

    def test_org_admin_cannot_create_license(self, client, token_org_admin, tenant_a):
        res = client.post(
            "/api/admin/licenses/",
            json={"tenant_id": str(tenant_a.id), "name": "Illegale licentie"},
            headers={"Authorization": f"Bearer {token_org_admin}"},
        )
        assert res.status_code == 403

    def test_license_unknown_tenant_rejected(self, client, token_rhadix_admin):
        res = client.post(
            "/api/admin/licenses/",
            json={"tenant_id": str(uuid.uuid4()), "name": "Ghost license"},
            headers={"Authorization": f"Bearer {token_rhadix_admin}"},
        )
        assert res.status_code == 404

    def test_list_licenses(self, client, token_rhadix_admin, license_a):
        res = client.get("/api/admin/licenses/", headers={"Authorization": f"Bearer {token_rhadix_admin}"})
        assert res.status_code == 200
        ids = [l["id"] for l in res.json()]
        assert str(license_a.id) in ids

    def test_update_license(self, client, token_rhadix_admin, license_a):
        res = client.patch(
            f"/api/admin/licenses/{license_a.id}",
            json={"name": "Updated Name", "is_active": False},
            headers={"Authorization": f"Bearer {token_rhadix_admin}"},
        )
        assert res.status_code == 200
        body = res.json()
        assert body["name"] == "Updated Name"
        assert body["is_active"] is False


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Application listing
# ═══════════════════════════════════════════════════════════════════════════════

class TestApplications:
    def test_rhadix_admin_can_list_applications(self, client, token_rhadix_admin):
        res = client.get("/api/admin/applications/", headers={"Authorization": f"Bearer {token_rhadix_admin}"})
        assert res.status_code == 200
        slugs = [a["slug"] for a in res.json()]
        assert "kikv-validator"     in slugs
        assert "zib-validator"      in slugs
        assert "algemeen-validator" in slugs
        assert "reconciliation"     in slugs

    def test_org_user_cannot_list_applications(self, client, token_org_user):
        res = client.get("/api/admin/applications/", headers={"Authorization": f"Bearer {token_org_user}"})
        assert res.status_code == 403

    def test_update_application(self, client, token_rhadix_admin, app_kikv):
        original_name = app_kikv.name
        res = client.patch(
            f"/api/admin/applications/{app_kikv.id}",
            json={"description": "Updated description"},
            headers={"Authorization": f"Bearer {token_rhadix_admin}"},
        )
        assert res.status_code == 200
        assert res.json()["description"] == "Updated description"
        assert res.json()["name"] == original_name   # unchanged


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Org-app assignment (RHADIX_ADMIN assigns app to tenant)
# ═══════════════════════════════════════════════════════════════════════════════

class TestTenantAppAssignment:
    def test_rhadix_admin_assigns_app_to_tenant(self, client, token_rhadix_admin, tenant_a, app_kikv):
        res = client.post(
            f"/api/admin/tenants/{tenant_a.id}/applications",
            json={"application_id": str(app_kikv.id)},
            headers={"Authorization": f"Bearer {token_rhadix_admin}"},
        )
        assert res.status_code == 201, res.text
        body = res.json()
        assert body["application_id"] == str(app_kikv.id)
        assert body["tenant_id"]      == str(tenant_a.id)

    def test_duplicate_assignment_rejected(self, client, token_rhadix_admin, tenant_a, tenant_app_kikv, app_kikv):
        res = client.post(
            f"/api/admin/tenants/{tenant_a.id}/applications",
            json={"application_id": str(app_kikv.id)},
            headers={"Authorization": f"Bearer {token_rhadix_admin}"},
        )
        assert res.status_code == 400

    def test_list_tenant_app_assignments(self, client, token_rhadix_admin, tenant_a, tenant_app_kikv, app_kikv):
        res = client.get(
            f"/api/admin/tenants/{tenant_a.id}/applications",
            headers={"Authorization": f"Bearer {token_rhadix_admin}"},
        )
        assert res.status_code == 200
        slugs = [a["application_slug"] for a in res.json()]
        assert "kikv-validator" in slugs

    def test_revoke_app_from_tenant(self, client, token_rhadix_admin, tenant_a, tenant_app_kikv, app_kikv):
        res = client.delete(
            f"/api/admin/tenants/{tenant_a.id}/applications/{app_kikv.id}",
            headers={"Authorization": f"Bearer {token_rhadix_admin}"},
        )
        assert res.status_code == 204

        # Verify it's gone
        res2 = client.get(
            f"/api/admin/tenants/{tenant_a.id}/applications",
            headers={"Authorization": f"Bearer {token_rhadix_admin}"},
        )
        slugs = [a["application_slug"] for a in res2.json()]
        assert "kikv-validator" not in slugs

    def test_org_user_cannot_assign_app_to_tenant(self, client, token_org_user, tenant_a, app_kikv):
        res = client.post(
            f"/api/admin/tenants/{tenant_a.id}/applications",
            json={"application_id": str(app_kikv.id)},
            headers={"Authorization": f"Bearer {token_org_user}"},
        )
        assert res.status_code == 403

    def test_assign_app_with_license(self, client, token_rhadix_admin, tenant_a, app_zib, license_a):
        res = client.post(
            f"/api/admin/tenants/{tenant_a.id}/applications",
            json={"application_id": str(app_zib.id), "license_id": str(license_a.id)},
            headers={"Authorization": f"Bearer {token_rhadix_admin}"},
        )
        assert res.status_code == 201
        assert res.json()["license_id"] == str(license_a.id)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. User-app assignment (ORG_ADMIN assigns app to user)
# ═══════════════════════════════════════════════════════════════════════════════

class TestUserAppAssignment:
    def test_org_admin_assigns_app_to_user(
        self, client, token_org_admin, user_org_user, app_kikv, tenant_app_kikv
    ):
        res = client.post(
            f"/api/org/users/{user_org_user.id}/apps",
            json={"user_id": str(user_org_user.id), "application_id": str(app_kikv.id)},
            headers={"Authorization": f"Bearer {token_org_admin}"},
        )
        assert res.status_code == 201, res.text
        body = res.json()
        assert body["user_id"]        == str(user_org_user.id)
        assert body["application_id"] == str(app_kikv.id)

    def test_duplicate_user_app_rejected(
        self, client, token_org_admin, user_org_user, app_kikv, user_app_kikv
    ):
        res = client.post(
            f"/api/org/users/{user_org_user.id}/apps",
            json={"user_id": str(user_org_user.id), "application_id": str(app_kikv.id)},
            headers={"Authorization": f"Bearer {token_org_admin}"},
        )
        assert res.status_code == 400

    def test_cannot_assign_app_not_licensed_for_tenant(
        self, client, token_org_admin, user_org_user, app_zib
    ):
        # app_zib is NOT assigned to tenant_a (no tenant_application fixture here)
        res = client.post(
            f"/api/org/users/{user_org_user.id}/apps",
            json={"user_id": str(user_org_user.id), "application_id": str(app_zib.id)},
            headers={"Authorization": f"Bearer {token_org_admin}"},
        )
        assert res.status_code == 403

    def test_list_user_app_assignments(
        self, client, token_org_admin, user_org_user, app_kikv, user_app_kikv
    ):
        res = client.get(
            f"/api/org/users/{user_org_user.id}/apps",
            headers={"Authorization": f"Bearer {token_org_admin}"},
        )
        assert res.status_code == 200
        slugs = [ua["application_slug"] for ua in res.json()]
        assert "kikv-validator" in slugs

    def test_revoke_user_app(
        self, client, token_org_admin, user_org_user, app_kikv, user_app_kikv
    ):
        res = client.delete(
            f"/api/org/users/{user_org_user.id}/apps/{app_kikv.id}",
            headers={"Authorization": f"Bearer {token_org_admin}"},
        )
        assert res.status_code == 204

    def test_list_my_tenant_apps(self, client, token_org_user, tenant_app_kikv):
        res = client.get("/api/org/me/apps", headers={"Authorization": f"Bearer {token_org_user}"})
        assert res.status_code == 200
        slugs = [a["application_slug"] for a in res.json()]
        assert "kikv-validator" in slugs


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Unauthorized access — ORG_USER blocked without app assignment
# ═══════════════════════════════════════════════════════════════════════════════

class TestUnauthorizedAccess:
    def test_org_user_cannot_assign_apps(self, client, token_org_user, user_org_user, app_kikv):
        """ORG_USER is not allowed to call the org-admin endpoints."""
        res = client.post(
            f"/api/org/users/{user_org_user.id}/apps",
            json={"user_id": str(user_org_user.id), "application_id": str(app_kikv.id)},
            headers={"Authorization": f"Bearer {token_org_user}"},
        )
        assert res.status_code == 403

    def test_unauthenticated_cannot_access_org_endpoints(self, client):
        res = client.get("/api/org/users")
        assert res.status_code == 401

    def test_unauthenticated_cannot_access_admin_licenses(self, client):
        res = client.get("/api/admin/licenses/")
        assert res.status_code == 401

    def test_org_admin_cannot_access_rhadix_admin_stats(self, client, token_org_admin):
        res = client.get("/api/admin/stats", headers={"Authorization": f"Bearer {token_org_admin}"})
        assert res.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Cross-tenant isolation
# ═══════════════════════════════════════════════════════════════════════════════

class TestCrossTenantIsolation:
    def test_org_admin_cannot_access_user_from_other_tenant(
        self, client, token_org_admin, user_tenant_b, app_kikv
    ):
        """ORG_ADMIN of tenant A should not be able to assign apps to a user in tenant B."""
        res = client.post(
            f"/api/org/users/{user_tenant_b.id}/apps",
            json={"user_id": str(user_tenant_b.id), "application_id": str(app_kikv.id)},
            headers={"Authorization": f"Bearer {token_org_admin}"},
        )
        assert res.status_code == 404   # "user not found in your organisation"

    def test_org_admin_cannot_list_users_from_other_tenant(
        self, client, token_org_admin, user_tenant_b
    ):
        """The /api/org/users endpoint should only return users from the caller's tenant."""
        res = client.get("/api/org/users", headers={"Authorization": f"Bearer {token_org_admin}"})
        assert res.status_code == 200
        ids = [u["id"] for u in res.json()]
        assert str(user_tenant_b.id) not in ids

    def test_tenant_b_user_cannot_see_tenant_a_apps(
        self, client, token_tenant_b, tenant_app_kikv
    ):
        """User from tenant B should not see tenant A's app assignments."""
        res = client.get("/api/org/me/apps", headers={"Authorization": f"Bearer {token_tenant_b}"})
        assert res.status_code == 200
        slugs = [a["application_slug"] for a in res.json()]
        assert "kikv-validator" not in slugs


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Validation run linkage
# ═══════════════════════════════════════════════════════════════════════════════

class TestValidationRunLinkage:
    def _create_run(self, db, tenant_id, app_id=None, lic_id=None):
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
            application_id=app_id,
            license_id=lic_id,
        )
        db.add(run); db.commit(); db.refresh(run)
        return run

    def test_run_stores_application_and_license(self, db, tenant_a, app_kikv, license_a):
        run = self._create_run(db, tenant_a.id, app_id=app_kikv.id, lic_id=license_a.id)
        assert run.application_id == app_kikv.id
        assert run.license_id     == license_a.id

    def test_run_without_app_is_allowed(self, db, tenant_a):
        """Demo runs (no authenticated user) have no application_id — must still be stored."""
        run = self._create_run(db, tenant_a.id)
        assert run.application_id is None
        assert run.license_id     is None

    def test_tenant_isolation_still_works(
        self, client, db, token_org_user, token_tenant_b, tenant_a, tenant_b
    ):
        """Runs from tenant_a invisible to tenant_b and vice versa."""
        run_a = self._create_run(db, tenant_a.id)
        run_b = self._create_run(db, tenant_b.id)

        res_a = client.get("/api/history/", headers={"Authorization": f"Bearer {token_org_user}"})
        ids_a = [r["id"] for r in res_a.json()]
        assert run_a.id in ids_a
        assert run_b.id not in ids_a

        res_b = client.get("/api/history/", headers={"Authorization": f"Bearer {token_tenant_b}"})
        ids_b = [r["id"] for r in res_b.json()]
        assert run_b.id in ids_b
        assert run_a.id not in ids_b


# ═══════════════════════════════════════════════════════════════════════════════
# 8. /api/auth/me returns assigned_app_slugs
# ═══════════════════════════════════════════════════════════════════════════════

class TestMeAssignedApps:
    def test_me_returns_empty_slugs_when_no_apps_assigned(
        self, client, token_org_user
    ):
        res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_org_user}"})
        assert res.status_code == 200
        assert res.json()["assigned_app_slugs"] == []

    def test_me_returns_slugs_after_assignment(
        self, client, token_org_user, user_app_kikv
    ):
        res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_org_user}"})
        assert res.status_code == 200
        assert "kikv-validator" in res.json()["assigned_app_slugs"]

    def test_rhadix_admin_me_returns_all_app_slugs(
        self, client, token_rhadix_admin
    ):
        res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_rhadix_admin}"})
        assert res.status_code == 200
        slugs = res.json()["assigned_app_slugs"]
        assert "kikv-validator"     in slugs
        assert "zib-validator"      in slugs
        assert "reconciliation"     in slugs
