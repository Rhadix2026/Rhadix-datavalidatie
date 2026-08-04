"""
test_tenant_management.py — RHADIX_ADMIN organisatie-beheer.

Covers:
  GET    /api/admin/tenants/{id}/impact       — impact-overzicht
  PATCH  /api/admin/tenants/{id}/deactivate   — organisatie (de)activeren (cascade users)
  DELETE /api/admin/tenants/{id}              — organisatie definitief verwijderen (cascade)
"""
import uuid
import pytest
from app.models.auth_models import User, UserRole
from app.models.models import ValidationRun
from app.auth.security import hash_password


def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def tenant_b_user(db, tenant_b):
    u = User(
        id=uuid.uuid4(), tenant_id=tenant_b.id,
        email="member@tenant-b.nl",
        password_hash=hash_password("Member-Pass-123!"),
        role=UserRole.ORG_USER, is_active=True,
    )
    db.add(u); db.commit(); db.refresh(u)
    return u


# ─── impact ────────────────────────────────────────────────────────────────────

class TestTenantImpact:

    def test_impact_counts_users(self, client, tenant_b, tenant_b_user, token_rhadix_admin):
        resp = client.get(f"/api/admin/tenants/{tenant_b.id}/impact", headers=auth(token_rhadix_admin))
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Tenant B"
        assert data["user_count"] == 1

    def test_impact_forbidden_for_org_admin(self, client, tenant_b, token_org_admin):
        resp = client.get(f"/api/admin/tenants/{tenant_b.id}/impact", headers=auth(token_org_admin))
        assert resp.status_code == 403

    def test_impact_404(self, client, token_rhadix_admin):
        resp = client.get(f"/api/admin/tenants/{uuid.uuid4()}/impact", headers=auth(token_rhadix_admin))
        assert resp.status_code == 404


# ─── deactivate ─────────────────────────────────────────────────────────────────

class TestTenantDeactivate:

    def test_deactivate_sets_users_inactive(self, client, db, tenant_b, tenant_b_user, token_rhadix_admin):
        resp = client.patch(f"/api/admin/tenants/{tenant_b.id}/deactivate",
                            json={"is_active": False}, headers=auth(token_rhadix_admin))
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False
        db.refresh(tenant_b_user)
        assert tenant_b_user.is_active is False

    def test_deactivated_user_cannot_login(self, client, tenant_b, tenant_b_user, token_rhadix_admin):
        client.patch(f"/api/admin/tenants/{tenant_b.id}/deactivate",
                     json={"is_active": False}, headers=auth(token_rhadix_admin))
        resp = client.post("/api/auth/login", json={
            "email": tenant_b_user.email, "password": "Member-Pass-123!"})
        assert resp.status_code == 401

    def test_reactivate(self, client, db, tenant_b, tenant_b_user, token_rhadix_admin):
        client.patch(f"/api/admin/tenants/{tenant_b.id}/deactivate",
                     json={"is_active": False}, headers=auth(token_rhadix_admin))
        resp = client.patch(f"/api/admin/tenants/{tenant_b.id}/deactivate",
                            json={"is_active": True}, headers=auth(token_rhadix_admin))
        assert resp.json()["is_active"] is True
        db.refresh(tenant_b_user)
        assert tenant_b_user.is_active is True

    def test_cannot_deactivate_own_tenant(self, client, tenant_a, token_rhadix_admin):
        # rhadix admin zit in tenant_a
        resp = client.patch(f"/api/admin/tenants/{tenant_a.id}/deactivate",
                            json={"is_active": False}, headers=auth(token_rhadix_admin))
        assert resp.status_code == 400

    def test_forbidden_for_org_admin(self, client, tenant_b, token_org_admin):
        resp = client.patch(f"/api/admin/tenants/{tenant_b.id}/deactivate",
                            json={"is_active": False}, headers=auth(token_org_admin))
        assert resp.status_code == 403


# ─── delete ─────────────────────────────────────────────────────────────────────

class TestTenantDelete:

    def test_delete_requires_matching_name(self, client, tenant_b, token_rhadix_admin):
        resp = client.request("DELETE", f"/api/admin/tenants/{tenant_b.id}",
                              json={"confirm_name": "verkeerd"}, headers=auth(token_rhadix_admin))
        assert resp.status_code == 400

    def test_delete_cascades_users(self, client, db, tenant_b, tenant_b_user, token_rhadix_admin):
        uid = tenant_b_user.id
        resp = client.request("DELETE", f"/api/admin/tenants/{tenant_b.id}",
                              json={"confirm_name": "Tenant B"}, headers=auth(token_rhadix_admin))
        assert resp.status_code == 200
        assert resp.json()["removed"]["user_count"] == 1
        assert db.query(User).filter(User.id == uid).first() is None

    def test_deleted_user_cannot_login(self, client, tenant_b, tenant_b_user, token_rhadix_admin):
        email = tenant_b_user.email   # capture before cascade-delete
        client.request("DELETE", f"/api/admin/tenants/{tenant_b.id}",
                       json={"confirm_name": "Tenant B"}, headers=auth(token_rhadix_admin))
        resp = client.post("/api/auth/login", json={
            "email": email, "password": "Member-Pass-123!"})
        assert resp.status_code == 401

    def test_scans_retained_but_detached(self, client, db, tenant_b, token_rhadix_admin):
        run = ValidationRun(label="run-b", files=[], results={}, tenant_id=tenant_b.id)
        db.add(run); db.commit(); db.refresh(run)
        rid = run.id
        client.request("DELETE", f"/api/admin/tenants/{tenant_b.id}",
                       json={"confirm_name": "Tenant B"}, headers=auth(token_rhadix_admin))
        db.expire_all()
        kept = db.query(ValidationRun).filter(ValidationRun.id == rid).first()
        assert kept is not None
        assert kept.tenant_id is None

    def test_cannot_delete_own_tenant(self, client, tenant_a, token_rhadix_admin):
        resp = client.request("DELETE", f"/api/admin/tenants/{tenant_a.id}",
                              json={"confirm_name": "Tenant A"}, headers=auth(token_rhadix_admin))
        assert resp.status_code == 400

    def test_forbidden_for_org_admin(self, client, tenant_b, token_org_admin):
        resp = client.request("DELETE", f"/api/admin/tenants/{tenant_b.id}",
                              json={"confirm_name": "Tenant B"}, headers=auth(token_org_admin))
        assert resp.status_code == 403

    def test_404(self, client, token_rhadix_admin):
        resp = client.request("DELETE", f"/api/admin/tenants/{uuid.uuid4()}",
                              json={"confirm_name": "x"}, headers=auth(token_rhadix_admin))
        assert resp.status_code == 404
