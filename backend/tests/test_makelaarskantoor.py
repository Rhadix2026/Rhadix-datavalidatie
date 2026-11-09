"""
test_makelaarskantoor.py — organisatietype MAKELAAR (Rhadix Makelaarsportaal).

Een makelaarskantoor is een gewone organisatie in het bestaande beheer (gebruikers, rollen,
licenties, applicaties, huisstijl) met een eigen type, en staat los van de zorgketen: nooit
onder een samenwerkingsorganisatie (RSO). De bestaande typen ORG en RSO blijven ongewijzigd.
"""
import uuid

from app.models.auth_models import Application, Tenant, User, UserRole

WACHTWOORD = "Makelaar-Pass-Word-99!"


def _maak(client, token, **extra):
    body = {"name": "Makelaardij Noord", "slug": "makelaardij-noord", "admin_email": "beheer@makelaardij-noord.nl",
            "admin_password": WACHTWOORD, "admin_full_name": "Kantoorbeheer", "tenant_type": "MAKELAAR", **extra}
    return client.post("/api/admin/tenants/", json=body, headers={"Authorization": f"Bearer {token}"})


def _rso(db):
    rso = Tenant(id=uuid.uuid4(), slug="rso-noord", name="RSO Noord", is_active=True, tenant_type="RSO")
    db.add(rso); db.commit()
    return rso


def _app(db):
    app = db.query(Application).filter(Application.slug == "rhadix-makelaarsportaal").first()
    if not app:
        app = Application(id=uuid.uuid4(), slug="rhadix-makelaarsportaal", name="Rhadix Makelaarsportaal", is_active=True, sort_order=15)
        db.add(app); db.commit()
    return app


class TestMakelaarskantoorAanmaken:
    def test_aanmaken_met_kantoorbeheerder_als_eerste_beheerder(self, client, db, token_rhadix_admin):
        res = _maak(client, token_rhadix_admin)
        assert res.status_code == 201
        body = res.json()
        assert body["tenant_type"] == "MAKELAAR"
        assert body["admin_role"] == "ORG_ADMIN"
        t = db.query(Tenant).filter(Tenant.id == uuid.UUID(body["id"])).first()
        assert t.tenant_type == "MAKELAAR" and t.parent_tenant_id is None

    def test_type_is_hoofdletterongevoelig(self, client, token_rhadix_admin):
        assert _maak(client, token_rhadix_admin, tenant_type="makelaar").json()["tenant_type"] == "MAKELAAR"

    def test_nooit_onder_een_rso(self, client, db, token_rhadix_admin):
        rso = _rso(db)
        res = _maak(client, token_rhadix_admin, parent_tenant_id=str(rso.id))
        assert res.status_code == 422
        assert db.query(Tenant).filter(Tenant.slug == "makelaardij-noord").first() is None

    def test_zichtbaar_in_de_lijst_met_type(self, client, token_rhadix_admin):
        tid = _maak(client, token_rhadix_admin).json()["id"]
        rij = next(t for t in client.get("/api/admin/tenants/", headers={"Authorization": f"Bearer {token_rhadix_admin}"}).json() if t["id"] == tid)
        assert rij["tenant_type"] == "MAKELAAR" and rij["parent_tenant_id"] is None

    def test_onbekend_type_blijft_geweigerd(self, client, token_rhadix_admin):
        assert _maak(client, token_rhadix_admin, tenant_type="WINKEL").status_code == 422


class TestBestaandeTypenOngewijzigd:
    def test_zorgorganisatie_onder_rso_blijft_werken(self, client, db, token_rhadix_admin):
        rso = _rso(db)
        res = _maak(client, token_rhadix_admin, tenant_type="ORG", slug="zorg-noord", name="Zorg Noord",
                    admin_email="admin@zorg-noord.nl", parent_tenant_id=str(rso.id))
        assert res.status_code == 201 and res.json()["admin_role"] == "ORG_ADMIN"

    def test_rso_krijgt_nog_steeds_een_rso_beheerder(self, client, token_rhadix_admin):
        res = _maak(client, token_rhadix_admin, tenant_type="RSO", slug="rso-zuid", name="RSO Zuid", admin_email="admin@rso-zuid.nl")
        assert res.status_code == 201 and res.json()["admin_role"] == "RSO_ADMIN"

    def test_standaardtype_blijft_zorgorganisatie(self, client, token_rhadix_admin):
        body = {"name": "Zonder type", "slug": "zonder-type", "admin_email": "a@zonder-type.nl", "admin_password": WACHTWOORD}
        res = client.post("/api/admin/tenants/", json=body, headers={"Authorization": f"Bearer {token_rhadix_admin}"})
        assert res.status_code == 201 and res.json()["tenant_type"] == "ORG"


class TestMakelaarsportaalViaBestaandBeheer:
    def test_toewijzing_licentie_en_claim(self, client, db, token_rhadix_admin):
        """Applicatie toewijzen, licentie afdwingen en de claim die het portaal leest (tenant_id + apps)."""
        h = {"Authorization": f"Bearer {token_rhadix_admin}"}
        tid = _maak(client, token_rhadix_admin).json()["id"]
        app = _app(db)
        lic = client.post("/api/admin/licenses/", json={"tenant_id": tid, "name": "Pilot 2026", "max_users": 2}, headers=h)
        assert lic.status_code == 201
        res = client.post(f"/api/admin/tenants/{tid}/applications", json={"application_id": str(app.id), "license_id": lic.json()["id"]}, headers=h)
        assert res.status_code == 201

        # Tweede gebruiker (makelaar) past binnen de licentie; een derde niet (harde grens).
        mk = client.post(f"/api/admin/tenants/{tid}/users", json={"email": "makelaar@makelaardij-noord.nl", "password": WACHTWOORD, "role": "ORG_USER"}, headers=h)
        assert mk.status_code == 201
        derde = client.post(f"/api/admin/tenants/{tid}/users", json={"email": "derde@makelaardij-noord.nl", "password": WACHTWOORD, "role": "ORG_USER"}, headers=h)
        assert derde.status_code == 400

        # Het centrale token van de kantoorbeheerder: organisatie-ID en de applicatie in de claim.
        from app.auth.security import decode_access_token
        login = client.post("/api/auth/login", json={"email": "beheer@makelaardij-noord.nl", "password": WACHTWOORD})
        assert login.status_code == 200
        claims = decode_access_token(login.json()["access_token"])
        assert claims["tenant_id"] == tid
        assert claims["role"] == "ORG_ADMIN"
        assert "rhadix-makelaarsportaal" in claims["apps"]

    def test_eigen_huisstijl(self, client, token_rhadix_admin):
        h = {"Authorization": f"Bearer {token_rhadix_admin}"}
        tid = _maak(client, token_rhadix_admin).json()["id"]
        res = client.put(f"/api/admin/tenants/{tid}/branding", json={"preset": "custom", "primary_color": "#123456", "accent_color": "#abcdef", "wordmark": "Makelaardij Noord"}, headers=h)
        assert res.status_code == 200
        assert client.get(f"/api/admin/tenants/{tid}/branding", headers=h).json()["wordmark"] == "Makelaardij Noord"
        # De huisstijl reist mee in het centrale token (daaruit leest het Makelaarsportaal hem).
        from app.auth.security import decode_access_token
        login = client.post("/api/auth/login", json={"email": "beheer@makelaardij-noord.nl", "password": WACHTWOORD})
        b = decode_access_token(login.json()["access_token"])["branding"]
        assert b["primary_color"] == "#123456" and b["wordmark"] == "Makelaardij Noord"
