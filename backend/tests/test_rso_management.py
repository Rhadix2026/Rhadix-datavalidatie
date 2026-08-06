"""
test_rso_management.py — RSO-beheerder (samenwerkingsorganisatie) scoping.

De RSO_ADMIN beheert alleen de eigen RSO + onderliggende organisaties.
"""
import uuid
import pytest
from tests.conftest import make_token
from app.models.auth_models import Application, Tenant, TenantApplication, User, UserRole
from app.auth.security import hash_password


def auth(token):
    return {"Authorization": f"Bearer {token}"}


# ─── fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture()
def rso(db):
    t = Tenant(id=uuid.uuid4(), slug="rso-noord", name="RSO Noord",
               tenant_type="RSO", is_active=True)
    db.add(t); db.commit(); db.refresh(t)
    return t


@pytest.fixture()
def rso_admin(db, rso):
    u = User(id=uuid.uuid4(), tenant_id=rso.id, email="beheer@rso-noord.nl",
             password_hash=hash_password("Rso-Admin-Pass-123!"),
             role=UserRole.RSO_ADMIN, is_active=True)
    db.add(u); db.commit(); db.refresh(u)
    return u


@pytest.fixture()
def rso_token(rso_admin):
    return make_token(rso_admin)


@pytest.fixture()
def child_org(db, rso):
    t = Tenant(id=uuid.uuid4(), slug="zorg-kind", name="Zorg Kind",
               tenant_type="ORG", parent_tenant_id=rso.id, is_active=True)
    db.add(t); db.commit(); db.refresh(t)
    u = User(id=uuid.uuid4(), tenant_id=t.id, email="user@zorg-kind.nl",
             password_hash=hash_password("Kind-Pass-123!"),
             role=UserRole.ORG_USER, is_active=True)
    db.add(u); db.commit()
    return t


@pytest.fixture()
def other_rso_org(db):
    """Een organisatie onder een ANDERE RSO — mag nooit zichtbaar zijn."""
    other = Tenant(id=uuid.uuid4(), slug="rso-zuid", name="RSO Zuid",
                   tenant_type="RSO", is_active=True)
    db.add(other); db.flush()
    org = Tenant(id=uuid.uuid4(), slug="zorg-zuid", name="Zorg Zuid",
                 tenant_type="ORG", parent_tenant_id=other.id, is_active=True)
    db.add(org); db.commit(); db.refresh(org)
    return org


# ─── listing / scoping ──────────────────────────────────────────────────────────

class TestRsoListing:

    def test_lists_own_rso_and_children(self, client, rso, child_org, rso_token):
        resp = client.get("/api/rso/organisations", headers=auth(rso_token))
        assert resp.status_code == 200
        names = {o["name"] for o in resp.json()}
        assert "RSO Noord" in names and "Zorg Kind" in names

    def test_does_not_see_other_rso(self, client, child_org, other_rso_org, rso_token):
        resp = client.get("/api/rso/organisations", headers=auth(rso_token))
        names = {o["name"] for o in resp.json()}
        assert "Zorg Zuid" not in names and "RSO Zuid" not in names

    def test_org_admin_forbidden(self, client, token_org_admin):
        resp = client.get("/api/rso/organisations", headers=auth(token_org_admin))
        assert resp.status_code == 403


# ─── organisatie aanmaken ────────────────────────────────────────────────────────

class TestRsoCreateOrg:

    def test_create_child_org(self, client, db, rso, rso_token):
        resp = client.post("/api/rso/organisations", json={
            "name": "Nieuwe Zorg", "slug": "nieuwe-zorg",
            "admin_email": "admin@nieuwe-zorg.nl", "admin_password": "NieuweZorg-123!",
        }, headers=auth(rso_token))
        assert resp.status_code == 201
        tid = uuid.UUID(resp.json()["id"])
        created = db.query(Tenant).filter(Tenant.id == tid).first()
        assert created.parent_tenant_id == rso.id
        assert created.tenant_type == "ORG"
        admin = db.query(User).filter(User.tenant_id == tid).first()
        assert admin.role == UserRole.ORG_ADMIN

    def test_duplicate_slug_rejected(self, client, rso, child_org, rso_token):
        resp = client.post("/api/rso/organisations", json={
            "name": "X", "slug": "zorg-kind",
            "admin_email": "x@x.nl", "admin_password": "Xxxxxxxx-123!",
        }, headers=auth(rso_token))
        assert resp.status_code == 400


# ─── gebruikers ─────────────────────────────────────────────────────────────────

class TestRsoUsers:

    def test_create_user_in_child(self, client, child_org, rso_token):
        resp = client.post(f"/api/rso/organisations/{child_org.id}/users", json={
            "email": "nieuw@zorg-kind.nl", "password": "NieuwUser-123!", "role": "ORG_USER",
        }, headers=auth(rso_token))
        assert resp.status_code == 201

    def test_cannot_create_user_in_foreign_org(self, client, other_rso_org, rso_token):
        resp = client.post(f"/api/rso/organisations/{other_rso_org.id}/users", json={
            "email": "hacker@zorg-zuid.nl", "password": "Hacker-123456!",
        }, headers=auth(rso_token))
        assert resp.status_code == 404

    def test_cannot_list_foreign_org_users(self, client, other_rso_org, rso_token):
        resp = client.get(f"/api/rso/organisations/{other_rso_org.id}/users", headers=auth(rso_token))
        assert resp.status_code == 404

    def test_cannot_grant_rhadix_admin(self, client, child_org, rso_token):
        resp = client.post(f"/api/rso/organisations/{child_org.id}/users", json={
            "email": "boss@zorg-kind.nl", "password": "BossPass-123!", "role": "RHADIX_ADMIN",
        }, headers=auth(rso_token))
        assert resp.status_code == 403

    def test_deactivate_scoped_user(self, client, db, child_org, rso_token):
        u = db.query(User).filter(User.tenant_id == child_org.id).first()
        resp = client.patch(f"/api/rso/users/{u.id}/deactivate", headers=auth(rso_token))
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    def test_cannot_deactivate_foreign_user(self, client, db, other_rso_org, rso_token):
        u = User(id=uuid.uuid4(), tenant_id=other_rso_org.id, email="z@zuid.nl",
                 password_hash=hash_password("Zuid-Pass-123!"), role=UserRole.ORG_USER, is_active=True)
        db.add(u); db.commit()
        resp = client.patch(f"/api/rso/users/{u.id}/deactivate", headers=auth(rso_token))
        assert resp.status_code == 404

    def test_last_rso_admin_protected(self, client, rso_admin, rso_token):
        resp = client.patch(f"/api/rso/users/{rso_admin.id}/deactivate", headers=auth(rso_token))
        # eigen account → 400 (self-guard vangt dit ook)
        assert resp.status_code == 400

    def test_no_hard_delete_endpoint(self, client, db, child_org, rso_token):
        u = db.query(User).filter(User.tenant_id == child_org.id).first()
        resp = client.request("DELETE", f"/api/rso/users/{u.id}", headers=auth(rso_token))
        assert resp.status_code in (404, 405)  # endpoint bestaat niet


# ─── apps ───────────────────────────────────────────────────────────────────────

class TestRsoApps:

    def test_assign_and_revoke_app(self, client, db, child_org, rso_token):
        app = Application(id=uuid.uuid4(), slug="kikv-x", name="KIK-V X", is_active=True)
        db.add(app); db.commit()
        r1 = client.post(f"/api/rso/organisations/{child_org.id}/applications",
                         json={"application_id": str(app.id)}, headers=auth(rso_token))
        assert r1.status_code == 201
        r2 = client.request("DELETE", f"/api/rso/organisations/{child_org.id}/applications/{app.id}",
                            headers=auth(rso_token))
        assert r2.status_code == 204

    def test_assignable_list_only_products(self, client, db, rso_token):
        # conftest seedt kikv/zib/algemeen-validator + 'reconciliation' (oude slug).
        for slug, name in [("uitvraag", "Rhadix Uitvraag"), ("rhadix-crm", "Rhadix CRM"),
                           ("reconciliation-engine", "Reconciliation Engine")]:
            if not db.query(Application).filter(Application.slug == slug).first():
                db.add(Application(id=uuid.uuid4(), slug=slug, name=name, is_active=True))
        db.commit()
        resp = client.get("/api/rso/applications", headers=auth(rso_token))
        assert resp.status_code == 200
        slugs = [a["slug"] for a in resp.json()]
        assert "uitvraag" in slugs                        # product zichtbaar
        assert "rhadix-crm" in slugs                      # CRM-tegel zichtbaar
        assert "reconciliation-engine" in slugs           # canonieke reconciliatie-tegel
        assert "reconciliation" not in slugs              # oude dubbele slug verborgen
        assert "kikv-validator" not in slugs              # validatie-sub-module verborgen
        assert slugs.count("reconciliation-engine") == 1  # niet dubbel

    def test_cannot_assign_app_to_foreign_org(self, client, db, other_rso_org, rso_token):
        app = Application(id=uuid.uuid4(), slug="kikv-y", name="KIK-V Y", is_active=True)
        db.add(app); db.commit()
        resp = client.post(f"/api/rso/organisations/{other_rso_org.id}/applications",
                           json={"application_id": str(app.id)}, headers=auth(rso_token))
        assert resp.status_code == 404
