"""
test_rol_wijzigen.py — een organisatiebeheerder wijzigt rollen binnen zijn organisatie.

Bevinding 14: "Als ik als hoofdgebruiker van een organisatie van één van mijn gebruikers
een rol wil wijzigen kan dat niet." De oorzaak was eenvoudig: `org.py` kende geen
PATCH-route. Rol wijzigen kon alleen via `/admin/users/{id}` (RHADIX_ADMIN) of
`/rso/users/{id}` (RSO_ADMIN); een organisatiebeheerder moest escaleren.

Het model dat hier wordt vastgelegd:

  * RHADIX_ADMIN mag rollen wijzigen;
  * ORG_ADMIN mag uitsluitend binnen de eigen organisatie wisselen tussen ORG_USER en
    ORG_ADMIN;
  * ORG_ADMIN mag nooit RHADIX_ADMIN toekennen of verwijderen;
  * ORG_USER mag geen rollen wijzigen;
  * de laatste actieve ORG_ADMIN mag niet worden gedegradeerd — een organisatie mag niet
    zonder beheerder komen te zitten;
  * gebruikers van andere organisaties blijven buiten bereik.

Die laatste regel geldt op ALLE DRIE de routes waarlangs een rol te wijzigen is. Zou hij
alleen op de nieuwe route gelden, dan was hij met twee klikken te omzeilen.
"""
import uuid

import pytest

from tests.conftest import make_token

from app.auth.security import hash_password
from app.models.auth_models import Tenant, User, UserRole


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def _gebruiker(db, tenant, email, rol=UserRole.ORG_USER, actief=True):
    u = User(id=uuid.uuid4(), tenant_id=tenant.id, email=email,
             full_name=email.split("@")[0],
             password_hash=hash_password("EenVoldoendeLangWachtwoord1!"),
             role=rol, is_active=actief)
    db.add(u); db.commit(); db.refresh(u)
    return u


def _rol_van(db, user_id):
    db.expire_all()
    return db.query(User).filter(User.id == user_id).first().role


# ── De nieuwe route doet wat bevinding 14 vroeg ─────────────────────────────

class TestOrgAdminWijzigtRol:

    def test_gebruiker_wordt_beheerder(self, client, db, tenant_a, user_org_user, token_org_admin):
        res = client.patch(f"/api/org/users/{user_org_user.id}",
                           json={"role": "ORG_ADMIN"}, headers=auth(token_org_admin))
        assert res.status_code == 200, res.text
        assert res.json()["role"] == "ORG_ADMIN"
        assert _rol_van(db, user_org_user.id) == UserRole.ORG_ADMIN

    def test_beheerder_wordt_gebruiker(self, client, db, tenant_a, user_org_admin, token_org_admin):
        # Tweede beheerder, anders blokkeert de laatste-beheerder-bescherming terecht.
        tweede = _gebruiker(db, tenant_a, "tweede.beheerder@example.org", UserRole.ORG_ADMIN)
        res = client.patch(f"/api/org/users/{tweede.id}",
                           json={"role": "ORG_USER"}, headers=auth(token_org_admin))
        assert res.status_code == 200, res.text
        assert _rol_van(db, tweede.id) == UserRole.ORG_USER

    def test_naam_wijzigen_kan_ook(self, client, db, user_org_user, token_org_admin):
        res = client.patch(f"/api/org/users/{user_org_user.id}",
                           json={"full_name": "Nieuwe Naam"}, headers=auth(token_org_admin))
        assert res.status_code == 200, res.text
        assert res.json()["full_name"] == "Nieuwe Naam"
        assert res.json()["role"] == "ORG_USER", "de rol mag niet meeveranderen"

    def test_rhadix_admin_mag_het_ook_via_deze_route(self, client, db, user_org_user, token_rhadix_admin):
        res = client.patch(f"/api/org/users/{user_org_user.id}",
                           json={"role": "ORG_ADMIN"}, headers=auth(token_rhadix_admin))
        assert res.status_code == 200, res.text


# ── Wat een organisatiebeheerder niet mag ───────────────────────────────────

class TestGrenzenVanDeOrgAdmin:

    @pytest.mark.parametrize("rol", ["RHADIX_ADMIN", "RSO_ADMIN"])
    def test_mag_die_rol_niet_toekennen(self, client, db, user_org_user, token_org_admin, rol):
        res = client.patch(f"/api/org/users/{user_org_user.id}",
                           json={"role": rol}, headers=auth(token_org_admin))
        assert res.status_code == 403, res.text
        assert _rol_van(db, user_org_user.id) == UserRole.ORG_USER, "de rol is toch gewijzigd"

    def test_mag_een_rhadix_admin_niet_degraderen(self, client, db, tenant_a,
                                                  user_rhadix_admin, token_org_admin):
        res = client.patch(f"/api/org/users/{user_rhadix_admin.id}",
                           json={"role": "ORG_USER"}, headers=auth(token_org_admin))
        assert res.status_code == 403, res.text
        assert _rol_van(db, user_rhadix_admin.id) == UserRole.RHADIX_ADMIN

    def test_mag_geen_gebruiker_van_een_andere_organisatie_wijzigen(self, client, db,
                                                                    user_tenant_b, token_org_admin):
        res = client.patch(f"/api/org/users/{user_tenant_b.id}",
                           json={"role": "ORG_ADMIN"}, headers=auth(token_org_admin))
        assert res.status_code == 404, res.text
        assert _rol_van(db, user_tenant_b.id) == UserRole.ORG_USER

    def test_een_gewone_gebruiker_mag_niets_wijzigen(self, client, db, user_org_admin, token_org_user):
        res = client.patch(f"/api/org/users/{user_org_admin.id}",
                           json={"role": "ORG_USER"}, headers=auth(token_org_user))
        assert res.status_code == 403, res.text

    def test_zonder_sessie_geen_toegang(self, client, user_org_user):
        assert client.patch(f"/api/org/users/{user_org_user.id}",
                            json={"role": "ORG_ADMIN"}).status_code == 401

    def test_onbekende_rol_wordt_geweigerd(self, client, user_org_user, token_org_admin):
        res = client.patch(f"/api/org/users/{user_org_user.id}",
                           json={"role": "SUPERUSER"}, headers=auth(token_org_admin))
        assert res.status_code == 422, res.text

    def test_onbekende_gebruiker_geeft_404(self, client, token_org_admin):
        res = client.patch(f"/api/org/users/{uuid.uuid4()}",
                           json={"role": "ORG_ADMIN"}, headers=auth(token_org_admin))
        assert res.status_code == 404


# ── De laatste beheerder — op alle drie de routes ───────────────────────────

class TestLaatsteBeheerder:
    """Een organisatie mag niet zonder beheerder komen te zitten."""

    def test_org_route_blokkeert_de_laatste_beheerder(self, client, db, tenant_a,
                                                      user_org_admin, token_org_admin):
        res = client.patch(f"/api/org/users/{user_org_admin.id}",
                           json={"role": "ORG_USER"}, headers=auth(token_org_admin))
        assert res.status_code == 400, res.text
        assert "laatste actieve beheerder" in res.json()["detail"]
        assert _rol_van(db, user_org_admin.id) == UserRole.ORG_ADMIN

    def test_admin_route_blokkeert_de_laatste_beheerder(self, client, db, tenant_a,
                                                        user_org_admin, token_rhadix_admin):
        """Zou de bescherming hier ontbreken, dan was hij met twee klikken te omzeilen."""
        res = client.patch(f"/api/admin/users/{user_org_admin.id}",
                           json={"role": "ORG_USER"}, headers=auth(token_rhadix_admin))
        assert res.status_code == 400, res.text
        assert _rol_van(db, user_org_admin.id) == UserRole.ORG_ADMIN

    def test_met_een_tweede_beheerder_mag_het_wel(self, client, db, tenant_a,
                                                  user_org_admin, token_org_admin):
        _gebruiker(db, tenant_a, "reserve.beheerder@example.org", UserRole.ORG_ADMIN)
        res = client.patch(f"/api/org/users/{user_org_admin.id}",
                           json={"role": "ORG_USER"}, headers=auth(token_org_admin))
        assert res.status_code == 200, res.text
        assert _rol_van(db, user_org_admin.id) == UserRole.ORG_USER

    def test_een_inactieve_tweede_beheerder_telt_niet_mee(self, client, db, tenant_a,
                                                          user_org_admin, token_org_admin):
        _gebruiker(db, tenant_a, "slapende.beheerder@example.org", UserRole.ORG_ADMIN, actief=False)
        res = client.patch(f"/api/org/users/{user_org_admin.id}",
                           json={"role": "ORG_USER"}, headers=auth(token_org_admin))
        assert res.status_code == 400, res.text

    def test_een_beheerder_van_een_andere_organisatie_telt_niet_mee(self, client, db, tenant_b,
                                                                     user_org_admin, token_org_admin):
        _gebruiker(db, tenant_b, "beheerder.elders@example.org", UserRole.ORG_ADMIN)
        res = client.patch(f"/api/org/users/{user_org_admin.id}",
                           json={"role": "ORG_USER"}, headers=auth(token_org_admin))
        assert res.status_code == 400, res.text

    def test_een_inactieve_beheerder_degraderen_mag_wel(self, client, db, tenant_a,
                                                        user_org_admin, token_org_admin):
        """Die is al geen actieve beheerder; de organisatie raakt niets kwijt."""
        slapend = _gebruiker(db, tenant_a, "inactief@example.org", UserRole.ORG_ADMIN, actief=False)
        res = client.patch(f"/api/org/users/{slapend.id}",
                           json={"role": "ORG_USER"}, headers=auth(token_org_admin))
        assert res.status_code == 200, res.text

    def test_naam_wijzigen_raakt_de_bescherming_niet(self, client, db, user_org_admin, token_org_admin):
        """De blokkade geldt de rol, niet elke wijziging aan de laatste beheerder."""
        res = client.patch(f"/api/org/users/{user_org_admin.id}",
                           json={"full_name": "Andere Naam"}, headers=auth(token_org_admin))
        assert res.status_code == 200, res.text

    def test_dezelfde_rol_opnieuw_zetten_blijft_toegestaan(self, client, db, user_org_admin,
                                                           token_org_admin):
        res = client.patch(f"/api/org/users/{user_org_admin.id}",
                           json={"role": "ORG_ADMIN"}, headers=auth(token_org_admin))
        assert res.status_code == 200, res.text


class TestLaatstePlatformbeheerder:
    """Zelfde regel een niveau hoger: het platform mag niet zonder Rhadix-beheerder."""

    def test_de_laatste_rhadix_admin_kan_niet_worden_gedegradeerd(self, client, db,
                                                                  user_rhadix_admin,
                                                                  token_rhadix_admin):
        res = client.patch(f"/api/admin/users/{user_rhadix_admin.id}",
                           json={"role": "ORG_USER"}, headers=auth(token_rhadix_admin))
        assert res.status_code == 400, res.text
        assert _rol_van(db, user_rhadix_admin.id) == UserRole.RHADIX_ADMIN

    def test_met_een_tweede_platformbeheerder_mag_het_wel(self, client, db, tenant_a,
                                                          user_rhadix_admin, token_rhadix_admin):
        _gebruiker(db, tenant_a, "tweede.platform@example.org", UserRole.RHADIX_ADMIN)
        res = client.patch(f"/api/admin/users/{user_rhadix_admin.id}",
                           json={"role": "ORG_USER"}, headers=auth(token_rhadix_admin))
        assert res.status_code == 200, res.text


# ── De RSO-route ────────────────────────────────────────────────────────────

@pytest.fixture()
def rso(db):
    t = Tenant(id=uuid.uuid4(), slug="rso-rolwijziging", name="RSO Rolwijziging",
               tenant_type="RSO", is_active=True)
    db.add(t); db.commit(); db.refresh(t)
    return t


@pytest.fixture()
def rso_token(db, rso):
    u = User(id=uuid.uuid4(), tenant_id=rso.id, email="beheer@rso-rolwijziging.nl",
             password_hash=hash_password("EenVoldoendeLangWachtwoord1!"),
             role=UserRole.RSO_ADMIN, is_active=True)
    db.add(u); db.commit(); db.refresh(u)
    return make_token(u)


@pytest.fixture()
def kind_org(db, rso):
    """Een organisatie onder de RSO, met precies één actieve beheerder."""
    t = Tenant(id=uuid.uuid4(), slug="kind-rolwijziging", name="Kind Rolwijziging",
               tenant_type="ORG", parent_tenant_id=rso.id, is_active=True)
    db.add(t); db.commit(); db.refresh(t)
    beheerder = _gebruiker(db, t, "enige.beheerder@kind.nl", UserRole.ORG_ADMIN)
    gebruiker = _gebruiker(db, t, "gewone.gebruiker@kind.nl", UserRole.ORG_USER)
    return t, beheerder, gebruiker


class TestRsoRouteBeschermtDeLaatsteBeheerder:
    """De derde route waarlangs een rol te wijzigen is.

    Deze route kende de bescherming niet: `update_rso_user` beperkte wél welke rollen
    toegekend mochten worden, maar controleerde niet of de organisatie een beheerder
    overhield. Zonder deze tests leunde die route uitsluitend op handmatig testen.
    """

    def test_rso_admin_kan_een_rol_wijzigen_in_een_onderliggende_organisatie(
        self, client, db, kind_org, rso_token
    ):
        """Vertrekpunt: de route werkt gewoon."""
        _, _, gebruiker = kind_org
        res = client.patch(f"/api/rso/users/{gebruiker.id}",
                           json={"role": "ORG_ADMIN"}, headers=auth(rso_token))
        assert res.status_code == 200, res.text
        assert _rol_van(db, gebruiker.id) == UserRole.ORG_ADMIN

    def test_de_laatste_beheerder_kan_niet_worden_gedegradeerd(self, client, db, kind_org, rso_token):
        """De kern: dezelfde blokkade als op de org- en de adminroute."""
        _, beheerder, _ = kind_org
        res = client.patch(f"/api/rso/users/{beheerder.id}",
                           json={"role": "ORG_USER"}, headers=auth(rso_token))
        assert res.status_code == 400, res.text
        assert "laatste actieve beheerder" in res.json()["detail"]
        assert _rol_van(db, beheerder.id) == UserRole.ORG_ADMIN

    def test_met_een_tweede_beheerder_mag_het_wel(self, client, db, kind_org, rso_token):
        org, beheerder, gebruiker = kind_org
        client.patch(f"/api/rso/users/{gebruiker.id}",
                     json={"role": "ORG_ADMIN"}, headers=auth(rso_token))
        res = client.patch(f"/api/rso/users/{beheerder.id}",
                           json={"role": "ORG_USER"}, headers=auth(rso_token))
        assert res.status_code == 200, res.text
        assert _rol_van(db, beheerder.id) == UserRole.ORG_USER

    def test_een_inactieve_tweede_beheerder_telt_niet_mee(self, client, db, kind_org, rso_token):
        org, beheerder, _ = kind_org
        _gebruiker(db, org, "slapend@kind.nl", UserRole.ORG_ADMIN, actief=False)
        res = client.patch(f"/api/rso/users/{beheerder.id}",
                           json={"role": "ORG_USER"}, headers=auth(rso_token))
        assert res.status_code == 400, res.text

    def test_naam_wijzigen_raakt_de_bescherming_niet(self, client, db, kind_org, rso_token):
        _, beheerder, _ = kind_org
        res = client.patch(f"/api/rso/users/{beheerder.id}",
                           json={"full_name": "Andere Naam"}, headers=auth(rso_token))
        assert res.status_code == 200, res.text
        assert _rol_van(db, beheerder.id) == UserRole.ORG_ADMIN

    def test_een_organisatie_buiten_de_eigen_rso_blijft_buiten_bereik(
        self, client, db, tenant_a, user_org_admin, rso_token
    ):
        """tenant_a hangt niet onder deze RSO."""
        res = client.patch(f"/api/rso/users/{user_org_admin.id}",
                           json={"role": "ORG_USER"}, headers=auth(rso_token))
        assert res.status_code == 404, res.text
        assert _rol_van(db, user_org_admin.id) == UserRole.ORG_ADMIN


# ── Wat niet mag veranderen ─────────────────────────────────────────────────

class TestGeenNevenschade:

    def test_de_adminroute_blijft_dicht_voor_een_org_admin(self, client, user_org_user, token_org_admin):
        """Bestaand gedrag: de brede beheerdersroute is voorbehouden aan RHADIX_ADMIN."""
        res = client.patch(f"/api/admin/users/{user_org_user.id}",
                           json={"role": "RHADIX_ADMIN"}, headers=auth(token_org_admin))
        assert res.status_code == 403

    def test_rhadix_admin_kan_nog_steeds_promoveren(self, client, db, user_org_user,
                                                    token_rhadix_admin):
        res = client.patch(f"/api/admin/users/{user_org_user.id}",
                           json={"role": "RHADIX_ADMIN"}, headers=auth(token_rhadix_admin))
        assert res.status_code == 200, res.text
        assert _rol_van(db, user_org_user.id) == UserRole.RHADIX_ADMIN

    def test_deactiveren_en_verwijderen_zijn_ongewijzigd(self, client, db, tenant_a,
                                                          token_org_admin):
        doelwit = _gebruiker(db, tenant_a, "tijdelijk@example.org")
        assert client.patch(f"/api/org/users/{doelwit.id}/deactivate",
                            headers=auth(token_org_admin)).status_code == 200
        assert client.delete(f"/api/org/users/{doelwit.id}",
                             headers=auth(token_org_admin)).status_code == 204

    def test_een_rolwijziging_raakt_de_apps_claim_niet(self, client, db, tenant_a,
                                                        user_org_user, token_org_user,
                                                        token_org_admin):
        """ORG_USER en ORG_ADMIN krijgen allebei de doorsnede; alleen RHADIX_ADMIN wijkt af."""
        from app.auth.app_toegang import app_slugs_voor

        voor = set(app_slugs_voor(user_org_user, db))
        client.patch(f"/api/org/users/{user_org_user.id}",
                     json={"role": "ORG_ADMIN"}, headers=auth(token_org_admin))
        db.expire_all()
        na = set(app_slugs_voor(db.query(User).filter(User.id == user_org_user.id).first(), db))
        assert voor == na
