"""Tests voor de generieke taken-/workflow-module."""
import uuid
import pytest
from app.models.auth_models import User, UserRole
from app.auth.security import hash_password

def auth(token): return {"Authorization": f"Bearer {token}"}

@pytest.fixture()
def user_a2(db, tenant_a):
    u = User(id=uuid.uuid4(), tenant_id=tenant_a.id, email="collega@tenant-a.nl",
             password_hash=hash_password("Pass-Collega-123!"), role=UserRole.ORG_USER, full_name="Collega A")
    db.add(u); db.commit(); db.refresh(u); return u


class TestCreateAssign:
    def test_create_and_list_mine(self, client, user_org_user, token_org_user):
        r = client.post("/api/tasks", json={"title": "Controleer AFAS-bestand"}, headers=auth(token_org_user))
        assert r.status_code == 201, r.text
        assert r.json()["status"] == "OPEN"
        # standaard niet toegewezen → niet in 'mine'
        assert client.get("/api/tasks?scope=mine", headers=auth(token_org_user)).json() == []
        assert len(client.get("/api/tasks?scope=created", headers=auth(token_org_user)).json()) == 1

    def test_assign_within_tenant(self, client, user_org_admin, token_org_admin, user_a2):
        r = client.post("/api/tasks", json={"title": "Pas organisatie aan", "assignee_id": str(user_a2.id),
                                            "priority": "HOOG"}, headers=auth(token_org_admin))
        assert r.status_code == 201, r.text
        assert r.json()["assignee_name"] == "Collega A"
        assert r.json()["priority"] == "HOOG"

    def test_assign_cross_tenant_blocked(self, client, token_org_admin, user_tenant_b):
        r = client.post("/api/tasks", json={"title": "x", "assignee_id": str(user_tenant_b.id)},
                        headers=auth(token_org_admin))
        assert r.status_code == 400


class TestTenantIsolation:
    def test_cannot_see_other_tenant_tasks(self, client, token_org_admin, token_tenant_b):
        client.post("/api/tasks", json={"title": "Taak tenant A"}, headers=auth(token_org_admin))
        assert client.get("/api/tasks?scope=all", headers=auth(token_tenant_b)).json() == []

    def test_cannot_patch_other_tenant_task(self, client, token_org_admin, token_tenant_b):
        tid = client.post("/api/tasks", json={"title": "A"}, headers=auth(token_org_admin)).json()["id"]
        assert client.patch(f"/api/tasks/{tid}", json={"status": "KLAAR"},
                            headers=auth(token_tenant_b)).status_code == 404


class TestStatusAndSummary:
    def test_status_to_klaar_sets_completed(self, client, user_org_user, token_org_user):
        tid = client.post("/api/tasks", json={"title": "T", "assignee_id": str(user_org_user.id)},
                          headers=auth(token_org_user)).json()["id"]
        r = client.patch(f"/api/tasks/{tid}", json={"status": "KLAAR"}, headers=auth(token_org_user))
        assert r.json()["status"] == "KLAAR" and r.json()["completed_at"]

    def test_summary_counts_open_mine(self, client, user_org_user, token_org_user):
        for i in range(3):
            client.post("/api/tasks", json={"title": f"T{i}", "assignee_id": str(user_org_user.id)},
                        headers=auth(token_org_user))
        s = client.get("/api/tasks/summary", headers=auth(token_org_user)).json()
        assert s["mine_open"] == 3


class TestBulk:
    def test_bulk_from_findings(self, client, user_org_admin, token_org_admin, user_a2):
        payload = {"items": [{"title": f"Fout {i}", "source_label": f"rij {i}"} for i in range(5)],
                   "assignee_id": str(user_a2.id), "source_type": "afas_validatie", "source_ref": "run-123"}
        r = client.post("/api/tasks/bulk", json=payload, headers=auth(token_org_admin))
        assert r.status_code == 201, r.text
        assert r.json()["created"] == 5
        mine = client.get("/api/tasks?scope=mine", headers=auth(token_org_admin))
        # toegewezen aan collega, niet aan admin
        assert all(t["assignee_name"] == "Collega A" for t in r.json()["tasks"])
        assert r.json()["tasks"][0]["source_type"] == "afas_validatie"

    def test_assignable_users_only_own_tenant(self, client, token_org_admin, user_a2, user_tenant_b):
        users = client.get("/api/tasks/assignable-users", headers=auth(token_org_admin)).json()
        emails = {u["email"] for u in users}
        assert "collega@tenant-a.nl" in emails
        assert "user@tenant-b.nl" not in emails
