"""
test_dashboard.py — Phase 3 dashboard endpoint tests.

Covers:
  - GET /api/dashboard/me   (any authenticated user, own data only)
  - GET /api/dashboard/org  (ORG_ADMIN + RHADIX_ADMIN; ORG_USER → 403)
  - GET /api/dashboard/admin (RHADIX_ADMIN only; others → 403)
  - Tenant isolation: ORG_ADMIN cannot see another tenant's data
  - Sector benchmark: returns null when < 5 participants
"""
import uuid
import pytest
from tests.conftest import make_token
from app.models.models import ValidationRun
from app.models.auth_models import Tenant, User, UserRole
from app.auth.security import hash_password


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def auth(token):
    return {"Authorization": f"Bearer {token}"}


def seed_run(db, tenant_id, created_by, score=80.0, standard="kikv",
             structural_score=85.0, relational_score=78.0, use_case_score=77.0):
    """Insert a ValidationRun and return it."""
    run = ValidationRun(
        label="Test run",
        files=[],
        results={},
        total_rows=100,
        error_count=5,
        warn_count=3,
        score=score,
        standard=standard,
        tenant_id=tenant_id,
        created_by=created_by,
        structural_score=structural_score,
        relational_score=relational_score,
        use_case_score=use_case_score,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


# ===========================================================================
# GET /api/dashboard/me
# ===========================================================================

class TestDashboardMe:

    def test_unauthenticated_returns_401(self, client):
        resp = client.get("/api/dashboard/me")
        assert resp.status_code == 401

    def test_returns_own_runs_only(self, client, db, user_org_user, user_org_admin,
                                   token_org_user, tenant_a):
        # Seed one run for org_user, one for org_admin
        seed_run(db, tenant_a.id, user_org_user.id, score=75.0)
        seed_run(db, tenant_a.id, user_org_admin.id, score=90.0)

        resp = client.get("/api/dashboard/me", headers=auth(token_org_user))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_runs"] == 1
        assert abs(data["latest_run"]["score"] - 75.0) < 0.1

    def test_empty_when_no_runs(self, client, token_org_user):
        resp = client.get("/api/dashboard/me", headers=auth(token_org_user))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_runs"] == 0
        assert data["latest_run"] is None
        assert data["trend"] == []

    def test_by_standard_aggregation(self, client, db, user_org_user, tenant_a, token_org_user):
        seed_run(db, tenant_a.id, user_org_user.id, score=80.0, standard="kikv")
        seed_run(db, tenant_a.id, user_org_user.id, score=70.0, standard="zib")

        resp = client.get("/api/dashboard/me", headers=auth(token_org_user))
        data = resp.json()
        assert "kikv" in data["by_standard"]
        assert "zib"  in data["by_standard"]
        assert data["by_standard"]["kikv"]["run_count"] == 1

    def test_standard_filter(self, client, db, user_org_user, tenant_a, token_org_user):
        seed_run(db, tenant_a.id, user_org_user.id, score=80.0, standard="kikv")
        seed_run(db, tenant_a.id, user_org_user.id, score=70.0, standard="zib")

        resp = client.get("/api/dashboard/me?standard=kikv", headers=auth(token_org_user))
        data = resp.json()
        assert data["total_runs"] == 1
        assert data["latest_run"]["standard"] == "kikv"

    def test_subscores_present(self, client, db, user_org_user, tenant_a, token_org_user):
        seed_run(db, tenant_a.id, user_org_user.id,
                 score=85.0, structural_score=90.0, relational_score=82.0, use_case_score=83.0)

        resp = client.get("/api/dashboard/me", headers=auth(token_org_user))
        data = resp.json()
        lr = data["latest_run"]
        assert lr["structural_score"] == pytest.approx(90.0, abs=0.1)
        assert lr["relational_score"] == pytest.approx(82.0, abs=0.1)
        assert lr["use_case_score"]   == pytest.approx(83.0, abs=0.1)

    def test_tenant_isolation_me(self, client, db, tenant_b, user_tenant_b, token_tenant_b,
                                  user_org_user, tenant_a, token_org_user):
        """User from tenant B should not see runs from tenant A."""
        seed_run(db, tenant_a.id, user_org_user.id, score=95.0)

        resp = client.get("/api/dashboard/me", headers=auth(token_tenant_b))
        data = resp.json()
        assert data["total_runs"] == 0


# ===========================================================================
# GET /api/dashboard/org
# ===========================================================================

class TestDashboardOrg:

    def test_org_user_forbidden(self, client, token_org_user):
        resp = client.get("/api/dashboard/org", headers=auth(token_org_user))
        assert resp.status_code == 403

    def test_org_admin_sees_own_tenant(self, client, db, tenant_a, user_org_user,
                                        user_org_admin, token_org_admin):
        seed_run(db, tenant_a.id, user_org_user.id, score=80.0)
        seed_run(db, tenant_a.id, user_org_admin.id, score=90.0)

        resp = client.get("/api/dashboard/org", headers=auth(token_org_admin))
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"]["total_runs"] == 2
        assert data["tenant_id"] == str(tenant_a.id)

    def test_org_admin_cannot_access_other_tenant(self, client, db, tenant_b,
                                                   token_org_admin):
        """ORG_ADMIN cannot pass a tenant_id to peek at another tenant."""
        resp = client.get(f"/api/dashboard/org?tenant_id={tenant_b.id}",
                          headers=auth(token_org_admin))
        # Should return own tenant data (tenant_id param ignored for ORG_ADMIN)
        assert resp.status_code == 200
        # tenant_id in response must be OWN tenant, not tenant_b
        data = resp.json()
        assert data["tenant_id"] != str(tenant_b.id)

    def test_rhadix_admin_can_specify_tenant(self, client, db, tenant_b,
                                              user_tenant_b, token_rhadix_admin):
        seed_run(db, tenant_b.id, user_tenant_b.id, score=70.0)

        resp = client.get(f"/api/dashboard/org?tenant_id={tenant_b.id}",
                          headers=auth(token_rhadix_admin))
        assert resp.status_code == 200
        data = resp.json()
        assert data["tenant_id"] == str(tenant_b.id)
        assert data["summary"]["total_runs"] == 1

    def test_tenant_isolation_org(self, client, db, tenant_a, tenant_b,
                                   user_org_user, user_tenant_b,
                                   token_org_admin):
        """ORG_ADMIN for tenant_a should not see tenant_b runs in the response."""
        seed_run(db, tenant_a.id, user_org_user.id, score=80.0)
        seed_run(db, tenant_b.id, user_tenant_b.id, score=95.0)

        resp = client.get("/api/dashboard/org", headers=auth(token_org_admin))
        data = resp.json()
        assert data["summary"]["total_runs"] == 1

    def test_sector_benchmark_null_when_insufficient_tenants(self, client, db,
                                                              tenant_a, user_org_user,
                                                              token_org_admin):
        """With only 1 tenant contributing data, benchmark must be None."""
        seed_run(db, tenant_a.id, user_org_user.id, score=80.0, standard="kikv")

        resp = client.get("/api/dashboard/org", headers=auth(token_org_admin))
        data = resp.json()
        assert data["sector_benchmark"] is None

    def test_summary_avg_scores(self, client, db, tenant_a, user_org_user,
                                 token_org_admin):
        seed_run(db, tenant_a.id, user_org_user.id, score=80.0,
                 structural_score=90.0, relational_score=70.0, use_case_score=80.0)
        seed_run(db, tenant_a.id, user_org_user.id, score=60.0,
                 structural_score=70.0, relational_score=50.0, use_case_score=60.0)

        resp = client.get("/api/dashboard/org", headers=auth(token_org_admin))
        data = resp.json()
        s = data["summary"]
        assert s["avg_score"]            == pytest.approx(70.0, abs=0.2)
        assert s["avg_structural_score"] == pytest.approx(80.0, abs=0.2)
        assert s["avg_relational_score"] == pytest.approx(60.0, abs=0.2)
        assert s["avg_use_case_score"]   == pytest.approx(70.0, abs=0.2)


# ===========================================================================
# GET /api/dashboard/admin
# ===========================================================================

class TestDashboardAdmin:

    def test_org_user_forbidden(self, client, token_org_user):
        resp = client.get("/api/dashboard/admin", headers=auth(token_org_user))
        assert resp.status_code == 403

    def test_org_admin_forbidden(self, client, token_org_admin):
        resp = client.get("/api/dashboard/admin", headers=auth(token_org_admin))
        assert resp.status_code == 403

    def test_rhadix_admin_ok(self, client, token_rhadix_admin):
        resp = client.get("/api/dashboard/admin", headers=auth(token_rhadix_admin))
        assert resp.status_code == 200

    def test_sees_all_tenants(self, client, db, tenant_a, tenant_b,
                               user_org_user, user_tenant_b, token_rhadix_admin):
        seed_run(db, tenant_a.id, user_org_user.id, score=80.0)
        seed_run(db, tenant_b.id, user_tenant_b.id, score=70.0)

        resp = client.get("/api/dashboard/admin", headers=auth(token_rhadix_admin))
        data = resp.json()
        tenant_ids = [t["tenant_id"] for t in data["per_tenant"]]
        assert str(tenant_a.id) in tenant_ids
        assert str(tenant_b.id) in tenant_ids

    def test_platform_summary_counts(self, client, db, tenant_a, tenant_b,
                                      user_org_user, user_tenant_b, token_rhadix_admin):
        seed_run(db, tenant_a.id, user_org_user.id, score=80.0)
        seed_run(db, tenant_a.id, user_org_user.id, score=85.0)
        seed_run(db, tenant_b.id, user_tenant_b.id, score=70.0)

        resp = client.get("/api/dashboard/admin", headers=auth(token_rhadix_admin))
        data = resp.json()
        ps = data["platform_summary"]
        assert ps["total_runs"] == 3
        assert ps["active_tenants_this_period"] == 2

    def test_standard_filter(self, client, db, tenant_a, user_org_user, token_rhadix_admin):
        seed_run(db, tenant_a.id, user_org_user.id, score=80.0, standard="kikv")
        seed_run(db, tenant_a.id, user_org_user.id, score=70.0, standard="zib")

        resp = client.get("/api/dashboard/admin?standard=kikv", headers=auth(token_rhadix_admin))
        data = resp.json()
        assert data["platform_summary"]["total_runs"] == 1

    def test_unauthenticated_returns_401(self, client):
        resp = client.get("/api/dashboard/admin")
        assert resp.status_code == 401
