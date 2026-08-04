"""
test_branding.py — look-and-feel per tenant (branding + overerving).
"""
import uuid
import pytest
from app.models.auth_models import Tenant, TenantBranding, User, UserRole
from app.auth.security import hash_password
from app.services.branding import resolve_effective_branding


def auth(token):
    return {"Authorization": f"Bearer {token}"}


PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 40


def _set_branding(db, tenant_id, **kw):
    b = TenantBranding(tenant_id=tenant_id, **kw)
    db.add(b); db.commit()
    return b


# ─── resolver / overerving ───────────────────────────────────────────────────────

class TestResolver:

    def test_own_branding_wins(self, db, tenant_a):
        _set_branding(db, tenant_a.id, preset="kikv", primary_color="#bd285f", accent_color="#2e6896")
        eff = resolve_effective_branding(db, tenant_a)
        assert eff["source"] == "self"
        assert eff["primary_color"] == "#bd285f"

    def test_inherits_from_rso(self, db):
        rso = Tenant(id=uuid.uuid4(), slug="rso-x", name="RSO X", tenant_type="RSO")
        db.add(rso); db.flush()
        org = Tenant(id=uuid.uuid4(), slug="org-x", name="Org X", tenant_type="ORG", parent_tenant_id=rso.id)
        db.add(org); db.commit()
        _set_branding(db, rso.id, preset="custom", primary_color="#123456")
        eff = resolve_effective_branding(db, org)
        assert eff["source"] == "rso"
        assert eff["primary_color"] == "#123456"

    def test_inherits_from_platform(self, db):
        platform = Tenant(id=uuid.uuid4(), slug="rhadix-platform", name="Rhadix Platform", tenant_type="PLATFORM")
        db.add(platform); db.flush()
        org = Tenant(id=uuid.uuid4(), slug="org-y", name="Org Y", tenant_type="ORG")
        db.add(org); db.commit()
        _set_branding(db, platform.id, preset="custom", primary_color="#0abab5")
        eff = resolve_effective_branding(db, org)
        assert eff["source"] == "platform"
        assert eff["primary_color"] == "#0abab5"

    def test_default_when_nothing(self, db, tenant_a):
        eff = resolve_effective_branding(db, tenant_a)
        assert eff["source"] == "default"
        assert eff["preset"] == "rhadix"


# ─── admin endpoints ─────────────────────────────────────────────────────────────

class TestBrandingEndpoints:

    def test_put_and_get(self, client, tenant_a, token_rhadix_admin):
        r = client.put(f"/api/admin/tenants/{tenant_a.id}/branding",
                       json={"preset": "custom", "primary_color": "#112233", "accent_color": "#445566", "wordmark": "Zorg X"},
                       headers=auth(token_rhadix_admin))
        assert r.status_code == 200
        g = client.get(f"/api/admin/tenants/{tenant_a.id}/branding", headers=auth(token_rhadix_admin))
        assert g.json()["primary_color"] == "#112233"
        assert g.json()["wordmark"] == "Zorg X"

    def test_invalid_hex_rejected(self, client, tenant_a, token_rhadix_admin):
        r = client.put(f"/api/admin/tenants/{tenant_a.id}/branding",
                       json={"primary_color": "rood"}, headers=auth(token_rhadix_admin))
        assert r.status_code == 422

    def test_org_admin_forbidden(self, client, tenant_a, token_org_admin):
        r = client.put(f"/api/admin/tenants/{tenant_a.id}/branding",
                       json={"primary_color": "#112233"}, headers=auth(token_org_admin))
        assert r.status_code == 403

    def test_delete_resets(self, client, db, tenant_a, token_rhadix_admin):
        _set_branding(db, tenant_a.id, primary_color="#112233")
        r = client.request("DELETE", f"/api/admin/tenants/{tenant_a.id}/branding", headers=auth(token_rhadix_admin))
        assert r.status_code == 204
        g = client.get(f"/api/admin/tenants/{tenant_a.id}/branding", headers=auth(token_rhadix_admin))
        assert g.json()["primary_color"] is None


# ─── logo ────────────────────────────────────────────────────────────────────────

class TestLogo:

    def test_upload_and_serve(self, client, tenant_a, token_rhadix_admin):
        up = client.post(f"/api/admin/tenants/{tenant_a.id}/branding/logo",
                         files={"file": ("logo.png", PNG, "image/png")}, headers=auth(token_rhadix_admin))
        assert up.status_code == 200
        assert up.json()["has_logo"] is True
        served = client.get(f"/api/branding/{tenant_a.id}/logo")
        assert served.status_code == 200
        assert served.content == PNG
        assert served.headers["content-type"].startswith("image/png")

    def test_bad_mime_rejected(self, client, tenant_a, token_rhadix_admin):
        up = client.post(f"/api/admin/tenants/{tenant_a.id}/branding/logo",
                         files={"file": ("x.txt", b"hello", "text/plain")}, headers=auth(token_rhadix_admin))
        assert up.status_code == 422

    def test_logo_404_when_absent(self, client, tenant_a):
        r = client.get(f"/api/branding/{tenant_a.id}/logo")
        assert r.status_code == 404


# ─── /me payload ─────────────────────────────────────────────────────────────────

class TestMeBranding:

    def test_me_includes_branding(self, client, db, tenant_a, user_org_user, token_org_user):
        _set_branding(db, tenant_a.id, preset="kikv", primary_color="#bd285f")
        r = client.get("/api/auth/me", headers=auth(token_org_user))
        assert r.status_code == 200
        assert r.json()["branding"]["primary_color"] == "#bd285f"
