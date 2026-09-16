"""
test_app_access_orglevel.py — app-toegang op organisatieniveau + licentie verwijderen.

BIJGEWERKT bij bevinding 8/11. De claim was de vereniging van organisatie- en
gebruikerstoewijzing; hij is nu de doorsnede: de organisatietoewijzing bepaalt wat
BESCHIKBAAR is, de persoonlijke toewijzing bepaalt wie er toegang toe heeft.

De tests hieronder toetsten dat een organisatietoewijzing alléén al de slug opleverde.
Dat is met opzet niet meer zo. Ze toetsen nu het standaardgedrag dat daarvoor in de
plaats komt: beschikbaar maken kent standaard ook toe aan de gebruikers, en zonder die
persoonlijke toewijzing geeft beschikbaar zijn geen toegang.
"""
import uuid
from tests.conftest import make_token
from app.auth.app_toegang import wijs_toe_aan_bestaande_gebruikers
from app.models.auth_models import Application, License, TenantApplication, User, UserRole


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def _grant_tenant_app(db, tenant_id, slug, name, ook_aan_gebruikers=True):
    """Wijs een applicatie toe aan de organisatie.

    `ook_aan_gebruikers` bootst het standaardgedrag van de beheerroute na: beschikbaar
    maken kent de applicatie ook meteen toe aan de huidige gebruikers.
    """
    app = db.query(Application).filter(Application.slug == slug).first()
    if not app:
        app = Application(id=uuid.uuid4(), slug=slug, name=name, is_active=True)
        db.add(app); db.flush()
    ta = TenantApplication(id=uuid.uuid4(), tenant_id=tenant_id, application_id=app.id)
    db.add(ta); db.flush()
    if ook_aan_gebruikers:
        wijs_toe_aan_bestaande_gebruikers(db, ta)
    db.commit()
    return app


class TestOrgLevelAppAccess:

    def test_me_includes_tenant_level_apps(self, client, db, tenant_a, user_org_user, token_org_user):
        """Standaardgedrag: toewijzen aan de organisatie kent ook aan de gebruikers toe."""
        _grant_tenant_app(db, tenant_a.id, "datavalidatie", "Rhadix Datavalidatie")
        r = client.get("/api/auth/me", headers=auth(token_org_user))
        assert r.status_code == 200
        assert "datavalidatie" in r.json()["assigned_app_slugs"]

    def test_alleen_beschikbaar_maken_geeft_geen_toegang(self, client, db, tenant_a,
                                                         user_org_user, token_org_user):
        """De kern van bevinding 8: beschikbaar is niet hetzelfde als toegang."""
        _grant_tenant_app(db, tenant_a.id, "datavalidatie", "Rhadix Datavalidatie",
                          ook_aan_gebruikers=False)
        r = client.get("/api/auth/me", headers=auth(token_org_user))
        assert r.status_code == 200
        assert "datavalidatie" not in r.json()["assigned_app_slugs"]

    def test_rso_admin_gets_org_apps(self, db, client):
        from app.auth.security import hash_password
        from app.models.auth_models import Tenant
        rso = Tenant(id=uuid.uuid4(), slug="rso-acc", name="RSO Acc", tenant_type="RSO")
        db.add(rso); db.flush()
        u = User(id=uuid.uuid4(), tenant_id=rso.id, email="a@rso-acc.nl",
                 password_hash=hash_password("Pass-123456789!"), role=UserRole.RSO_ADMIN, is_active=True)
        db.add(u); db.commit()
        _grant_tenant_app(db, rso.id, "datavalidatie", "Rhadix Datavalidatie")
        r = client.get("/api/auth/me", headers=auth(make_token(u)))
        assert "datavalidatie" in r.json()["assigned_app_slugs"]


class TestLicenseDelete:

    def test_rhadix_admin_can_delete_license(self, client, db, tenant_a, token_rhadix_admin):
        lic = License(id=uuid.uuid4(), tenant_id=tenant_a.id, name="Test-lic")
        db.add(lic); db.commit()
        lid = lic.id
        r = client.request("DELETE", f"/api/admin/licenses/{lid}", headers=auth(token_rhadix_admin))
        assert r.status_code == 204
        assert db.query(License).filter(License.id == lid).first() is None

    def test_delete_license_404(self, client, token_rhadix_admin):
        r = client.request("DELETE", f"/api/admin/licenses/{uuid.uuid4()}", headers=auth(token_rhadix_admin))
        assert r.status_code == 404

    def test_org_admin_cannot_delete_license(self, client, db, tenant_a, token_org_admin):
        lic = License(id=uuid.uuid4(), tenant_id=tenant_a.id, name="Test-lic-2")
        db.add(lic); db.commit()
        r = client.request("DELETE", f"/api/admin/licenses/{lic.id}", headers=auth(token_org_admin))
        assert r.status_code == 403
