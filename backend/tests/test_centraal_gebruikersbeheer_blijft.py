"""
test_centraal_gebruikersbeheer_blijft.py — de tegenhanger van bevinding 13.

Uit Uitvraag, Datastation en CRM zijn de lokale bewerkacties verdwenen: gebruikers
aanmaken, wachtwoorden zetten, (de)activeren en verwijderen. De voorwaarde daarvoor was
dat dezelfde bevoegde rol het hier, in de centrale identity provider, onverkort kan.

Deze suite bewaakt precies dat. Valt een van deze routes weg of wordt hij strenger
afgeschermd, dan is er in de resource-apps functionaliteit weggehaald zonder dat er een
alternatief overblijft — en dat is waar deze tests op afgaan.

De routes zijn uitsluitend op rol beschermd (`require_role`), niet op een apps-claim.
Dat is belangrijk: ook een beheerder van een organisatie zónder de datavalidatie-slug
moet hier zijn gebruikers kunnen beheren.
"""
import uuid

import pytest

from app.auth.security import hash_password
from app.models.auth_models import User, UserRole


def auth(token):
    return {"Authorization": f"Bearer {token}"}


class TestBeheerderKanAlsVoorheen:
    """De vier functies die uit de resource-apps zijn verdwenen, werken hier."""

    def test_gebruiker_aanmaken(self, client, token_org_admin):
        res = client.post("/api/org/users", json={
            "email": "nieuw-centraal@example.org",
            "full_name": "Nieuw Centraal",
            "password": "EenVoldoendeLangWachtwoord1!",
            "role": "ORG_USER",
        }, headers=auth(token_org_admin))
        assert res.status_code == 201, res.text
        assert res.json()["email"] == "nieuw-centraal@example.org"

    def test_aangemaakte_gebruiker_kan_inloggen(self, client, token_org_admin):
        """Het verschil met de resource-apps: hier levert aanmaken een bruikbaar account."""
        client.post("/api/org/users", json={
            "email": "kaninloggen@example.org", "full_name": "Kan Inloggen",
            "password": "EenVoldoendeLangWachtwoord1!", "role": "ORG_USER",
        }, headers=auth(token_org_admin))
        res = client.post("/api/auth/login", json={
            "email": "kaninloggen@example.org", "password": "EenVoldoendeLangWachtwoord1!",
        })
        assert res.status_code == 200, res.text
        assert res.json()["access_token"]

    def test_wachtwoord_van_een_ander_zetten(self, client, user_org_user, token_org_admin):
        res = client.post(f"/api/org/users/{user_org_user.id}/reset-password",
                          json={"new_password": "Centraal-Gezet-Wachtwoord-1!"},
                          headers=auth(token_org_admin))
        assert res.status_code == 204, res.text
        login = client.post("/api/auth/login", json={
            "email": user_org_user.email, "password": "Centraal-Gezet-Wachtwoord-1!"})
        assert login.status_code == 200

    def test_gebruiker_deactiveren_blokkeert_inloggen(self, client, db, tenant_a, token_org_admin):
        """Centraal deactiveren wérkt: er wordt geen token meer uitgegeven, dus de
        gebruiker komt in geen enkele applicatie meer binnen."""
        u = User(id=uuid.uuid4(), tenant_id=tenant_a.id, email="tedeactiveren@example.org",
                 password_hash=hash_password("EenVoldoendeLangWachtwoord1!"),
                 role=UserRole.ORG_USER, is_active=True)
        db.add(u); db.commit()

        res = client.patch(f"/api/org/users/{u.id}/deactivate", headers=auth(token_org_admin))
        assert res.status_code == 200, res.text
        assert res.json()["is_active"] is False

        login = client.post("/api/auth/login", json={
            "email": "tedeactiveren@example.org", "password": "EenVoldoendeLangWachtwoord1!"})
        assert login.status_code == 401, "een gedeactiveerde gebruiker krijgt nog een token"

    def test_gebruiker_verwijderen(self, client, db, tenant_a, token_org_admin):
        u = User(id=uuid.uuid4(), tenant_id=tenant_a.id, email="teverwijderen@example.org",
                 password_hash=hash_password("EenVoldoendeLangWachtwoord1!"),
                 role=UserRole.ORG_USER, is_active=True)
        db.add(u); db.commit()
        uid = u.id

        res = client.delete(f"/api/org/users/{uid}", headers=auth(token_org_admin))
        assert res.status_code == 204, res.text
        assert db.query(User).filter(User.id == uid).first() is None

        login = client.post("/api/auth/login", json={
            "email": "teverwijderen@example.org", "password": "EenVoldoendeLangWachtwoord1!"})
        assert login.status_code == 401


class TestBereikbaarheid:
    """De routes mogen niet achter een apps-claim komen te staan."""

    def test_de_routes_hangen_alleen_aan_een_rol(self):
        from pathlib import Path
        from app.routers import org
        bron = Path(org.__file__).read_text(encoding="utf-8")
        assert "require_role(UserRole.ORG_ADMIN, UserRole.RHADIX_ADMIN)" in bron
        assert "require_app_access" not in bron, (
            "organisatiebeheer is achter een apps-claim gezet; een beheerder zonder de "
            "datavalidatie-slug kan zijn gebruikers dan niet meer beheren"
        )

    def test_een_gewone_gebruiker_komt_er_niet_bij(self, client, token_org_user):
        assert client.get("/api/org/users", headers=auth(token_org_user)).status_code == 403

    def test_zonder_sessie_geen_toegang(self, client):
        assert client.get("/api/org/users").status_code == 401


class TestGrenzenOngewijzigd:
    """Wat een beheerder niet mocht, mag hij nog steeds niet."""

    def test_geen_beheer_over_een_andere_organisatie(self, client, user_org_user, token_tenant_b):
        res = client.delete(f"/api/org/users/{user_org_user.id}", headers=auth(token_tenant_b))
        assert res.status_code in (403, 404)

    def test_eigen_account_niet_verwijderen(self, client, user_org_admin, token_org_admin):
        res = client.delete(f"/api/org/users/{user_org_admin.id}", headers=auth(token_org_admin))
        assert res.status_code == 400

    def test_eigen_account_niet_deactiveren(self, client, user_org_admin, token_org_admin):
        res = client.patch(f"/api/org/users/{user_org_admin.id}/deactivate",
                           headers=auth(token_org_admin))
        assert res.status_code == 400

    def test_beheerder_kan_geen_platformrol_uitdelen(self, client, token_org_admin):
        res = client.post("/api/org/users", json={
            "email": "wil-admin-zijn@example.org", "full_name": "Te Hoog",
            "password": "EenVoldoendeLangWachtwoord1!", "role": "RHADIX_ADMIN",
        }, headers=auth(token_org_admin))
        assert res.status_code == 403, res.text
