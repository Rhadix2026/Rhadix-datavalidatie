"""
test_licentiegrens.py — max_users is een harde grens op het aantal actieve gebruikers.

Bevinding 7: "Bij het aanmaken van gebruikers onder een organisatie wordt niet naar de
licentie gekeken. Dus ik kan een licentie hebben met max aantal gebruikers van 1 en er
toch 2 gebruikers aan koppelen."

`License.max_users` werd uitsluitend opgeslagen en teruggegeven; geen enkele plek telde
gebruikers. De grens geldt nu op alle zes de plekken waar een gebruiker actief kan
worden: aanmaken via de org-, admin- en RSO-route, en activeren via diezelfde drie.

Vastgelegde keuzes:

  * alleen ACTIEVE gebruikers tellen mee;
  * bij meerdere licenties geldt de som van hun max_users; één licentie zonder maximum
    maakt het geheel onbeperkt;
  * `valid_until` speelt hier geen rol — dat is bevinding 6 en nog niet besloten.
"""
import uuid

import pytest

from app.auth.licentiegrens import (
    aantal_actieve_gebruikers,
    controleer_ruimte,
    maximum_actieve_gebruikers,
)
from app.auth.security import hash_password
from app.models.auth_models import License, Tenant, User, UserRole


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def _licentie(db, tenant, max_users, actief=True, naam="Testlicentie"):
    lic = License(id=uuid.uuid4(), tenant_id=tenant.id, name=naam,
                  max_users=max_users, is_active=actief)
    db.add(lic); db.commit(); db.refresh(lic)
    return lic


def _gebruiker(db, tenant, email, rol=UserRole.ORG_USER, actief=True):
    u = User(id=uuid.uuid4(), tenant_id=tenant.id, email=email, full_name=email,
             password_hash=hash_password("EenVoldoendeLangWachtwoord1!"),
             role=rol, is_active=actief)
    db.add(u); db.commit(); db.refresh(u)
    return u


def _nieuwe_gebruiker_body(email):
    return {"email": email, "full_name": "Nieuw", "role": "ORG_USER",
            "password": "EenVoldoendeLangWachtwoord1!"}


# ── De rekenregel ───────────────────────────────────────────────────────────

class TestMaximumBepalen:

    def test_zonder_licentie_is_het_onbeperkt(self, db, tenant_a):
        assert maximum_actieve_gebruikers(db, tenant_a.id) is None

    def test_een_licentie_zonder_maximum_is_onbeperkt(self, db, tenant_a):
        _licentie(db, tenant_a, None)
        assert maximum_actieve_gebruikers(db, tenant_a.id) is None

    def test_een_licentie_met_maximum(self, db, tenant_a):
        _licentie(db, tenant_a, 5)
        assert maximum_actieve_gebruikers(db, tenant_a.id) == 5

    def test_meerdere_licenties_tellen_op(self, db, tenant_a):
        _licentie(db, tenant_a, 3, naam="Basis")
        _licentie(db, tenant_a, 2, naam="Uitbreiding")
        assert maximum_actieve_gebruikers(db, tenant_a.id) == 5

    def test_een_onbeperkte_licentie_maakt_het_geheel_onbeperkt(self, db, tenant_a):
        """De ruimste licentie wint; anders zou een uitbreiding de boel juist beperken."""
        _licentie(db, tenant_a, 3, naam="Basis")
        _licentie(db, tenant_a, None, naam="Onbeperkt")
        assert maximum_actieve_gebruikers(db, tenant_a.id) is None

    def test_een_inactieve_licentie_telt_niet_mee(self, db, tenant_a):
        _licentie(db, tenant_a, 1, actief=False)
        assert maximum_actieve_gebruikers(db, tenant_a.id) is None

    def test_een_licentie_van_een_andere_organisatie_telt_niet_mee(self, db, tenant_a, tenant_b):
        _licentie(db, tenant_b, 1)
        assert maximum_actieve_gebruikers(db, tenant_a.id) is None

    def test_valid_until_speelt_hier_geen_rol(self, db, tenant_a):
        """Bewust: of een verlopen licentie effect heeft, is bevinding 6."""
        from datetime import datetime, timedelta, timezone
        lic = _licentie(db, tenant_a, 2)
        lic.valid_until = datetime.now(timezone.utc) - timedelta(days=30)
        db.commit()
        assert maximum_actieve_gebruikers(db, tenant_a.id) == 2


class TestTellingVanActieveGebruikers:

    def test_alleen_actieve_gebruikers_tellen(self, db, tenant_a, user_org_user):
        _gebruiker(db, tenant_a, "slapend@example.org", actief=False)
        assert aantal_actieve_gebruikers(db, tenant_a.id) == 1

    def test_gebruikers_van_een_andere_organisatie_tellen_niet(self, db, tenant_a, tenant_b,
                                                                user_org_user):
        _gebruiker(db, tenant_b, "elders@example.org")
        assert aantal_actieve_gebruikers(db, tenant_a.id) == 1


class TestControleerRuimte:

    def test_zonder_licentie_altijd_ruimte(self, db, tenant_a, user_org_user):
        controleer_ruimte(db, tenant_a.id)   # mag niet opgooien

    def test_onder_de_grens_is_er_ruimte(self, db, tenant_a, user_org_user):
        _licentie(db, tenant_a, 5)
        controleer_ruimte(db, tenant_a.id)

    def test_op_de_grens_is_er_geen_ruimte_meer(self, db, tenant_a, user_org_user):
        from fastapi import HTTPException
        _licentie(db, tenant_a, 1)
        with pytest.raises(HTTPException) as exc:
            controleer_ruimte(db, tenant_a.id)
        assert exc.value.status_code == 400
        assert "maximum aantal actieve gebruikers" in exc.value.detail

    def test_de_melding_noemt_aantal_en_maximum(self, db, tenant_a, user_org_user):
        from fastapi import HTTPException
        _gebruiker(db, tenant_a, "tweede@example.org")
        _licentie(db, tenant_a, 2)
        with pytest.raises(HTTPException) as exc:
            controleer_ruimte(db, tenant_a.id)
        assert "2 van 2" in exc.value.detail
        assert "Deactiveer" in exc.value.detail, "de melding zegt niet wat er kan gebeuren"


# ── Het scenario uit de melding, via de echte routes ────────────────────────

class TestAanmakenViaDeOrgRoute:
    """Precies wat Ruben beschreef: licentie voor 1, tóch een tweede gebruiker."""

    def test_tweede_gebruiker_wordt_geweigerd_bij_een_licentie_voor_een(
        self, client, db, tenant_a, user_org_admin, token_org_admin
    ):
        _licentie(db, tenant_a, 1)   # de beheerder vult die ene plaats al
        res = client.post("/api/org/users", json=_nieuwe_gebruiker_body("tweede@example.org"),
                          headers=auth(token_org_admin))
        assert res.status_code == 400, res.text
        assert "maximum aantal actieve gebruikers" in res.json()["detail"]
        assert db.query(User).filter(User.email == "tweede@example.org").first() is None

    def test_met_ruimte_lukt_het_gewoon(self, client, db, tenant_a, user_org_admin,
                                        token_org_admin):
        _licentie(db, tenant_a, 5)
        res = client.post("/api/org/users", json=_nieuwe_gebruiker_body("past@example.org"),
                          headers=auth(token_org_admin))
        assert res.status_code == 201, res.text

    def test_zonder_licentie_lukt_het_ook(self, client, db, tenant_a, token_org_admin):
        res = client.post("/api/org/users", json=_nieuwe_gebruiker_body("vrij@example.org"),
                          headers=auth(token_org_admin))
        assert res.status_code == 201, res.text

    def test_een_gedeactiveerde_gebruiker_maakt_plaats_vrij(self, client, db, tenant_a,
                                                             user_org_admin, token_org_admin):
        """Een oud account mag een nieuwe medewerker niet blokkeren."""
        _licentie(db, tenant_a, 2)
        _gebruiker(db, tenant_a, "vertrokken@example.org", actief=False)
        res = client.post("/api/org/users", json=_nieuwe_gebruiker_body("opvolger@example.org"),
                          headers=auth(token_org_admin))
        assert res.status_code == 201, res.text


class TestActiveren:

    def test_activeren_wordt_geblokkeerd_zonder_ruimte(self, client, db, tenant_a,
                                                        user_org_admin, token_org_admin):
        slapend = _gebruiker(db, tenant_a, "terug@example.org", actief=False)
        _licentie(db, tenant_a, 1)   # de beheerder vult de enige plaats
        res = client.patch(f"/api/org/users/{slapend.id}/deactivate", headers=auth(token_org_admin))
        assert res.status_code == 400, res.text
        assert "maximum aantal actieve gebruikers" in res.json()["detail"]
        db.expire_all()
        assert db.query(User).filter(User.id == slapend.id).first().is_active is False

    def test_activeren_lukt_met_ruimte(self, client, db, tenant_a, user_org_admin, token_org_admin):
        slapend = _gebruiker(db, tenant_a, "welkom@example.org", actief=False)
        _licentie(db, tenant_a, 5)
        res = client.patch(f"/api/org/users/{slapend.id}/deactivate", headers=auth(token_org_admin))
        assert res.status_code == 200, res.text
        assert res.json()["is_active"] is True

    def test_deactiveren_wordt_nooit_geblokkeerd(self, client, db, tenant_a, user_org_admin,
                                                  token_org_admin):
        """Ook bij een volle licentie moet je een gebruiker kwijt kunnen."""
        actief = _gebruiker(db, tenant_a, "weg@example.org")
        _licentie(db, tenant_a, 1)   # ruim overschreden
        res = client.patch(f"/api/org/users/{actief.id}/deactivate", headers=auth(token_org_admin))
        assert res.status_code == 200, res.text
        assert res.json()["is_active"] is False


class TestAdminRoute:

    def test_platformbeheerder_wordt_ook_begrensd(self, client, db, tenant_a, user_org_admin,
                                                   token_rhadix_admin):
        """Anders is de grens met één omweg te passeren."""
        _licentie(db, tenant_a, 1)
        res = client.post(f"/api/admin/tenants/{tenant_a.id}/users",
                          json=_nieuwe_gebruiker_body("viaadmin@example.org"),
                          headers=auth(token_rhadix_admin))
        assert res.status_code == 400, res.text

    def test_met_ruimte_lukt_het_via_de_adminroute(self, client, db, tenant_a, token_rhadix_admin):
        _licentie(db, tenant_a, 5)
        res = client.post(f"/api/admin/tenants/{tenant_a.id}/users",
                          json=_nieuwe_gebruiker_body("adminok@example.org"),
                          headers=auth(token_rhadix_admin))
        assert res.status_code == 201, res.text


class TestRsoRoute:

    @pytest.fixture()
    def rso_met_kind(self, db):
        from tests.conftest import make_token
        rso = Tenant(id=uuid.uuid4(), slug="rso-licentie", name="RSO Licentie",
                     tenant_type="RSO", is_active=True)
        db.add(rso); db.flush()
        beheerder = User(id=uuid.uuid4(), tenant_id=rso.id, email="beheer@rso-licentie.nl",
                         password_hash=hash_password("EenVoldoendeLangWachtwoord1!"),
                         role=UserRole.RSO_ADMIN, is_active=True)
        db.add(beheerder)
        kind = Tenant(id=uuid.uuid4(), slug="kind-licentie", name="Kind Licentie",
                      tenant_type="ORG", parent_tenant_id=rso.id, is_active=True)
        db.add(kind); db.commit(); db.refresh(kind)
        _gebruiker(db, kind, "zit.er.al@kind.nl", UserRole.ORG_ADMIN)
        return kind, make_token(beheerder)

    def test_rso_beheerder_wordt_ook_begrensd(self, client, db, rso_met_kind):
        kind, token = rso_met_kind
        _licentie(db, kind, 1)
        res = client.post(f"/api/rso/organisations/{kind.id}/users",
                          json=_nieuwe_gebruiker_body("viarso@kind.nl"), headers=auth(token))
        assert res.status_code == 400, res.text

    def test_met_ruimte_lukt_het_via_de_rso_route(self, client, db, rso_met_kind):
        kind, token = rso_met_kind
        _licentie(db, kind, 5)
        res = client.post(f"/api/rso/organisations/{kind.id}/users",
                          json=_nieuwe_gebruiker_body("rsook@kind.nl"), headers=auth(token))
        assert res.status_code == 201, res.text


# ── Wat niet mag veranderen ─────────────────────────────────────────────────

class TestGeenNevenschade:

    def test_de_grens_geldt_per_organisatie(self, client, db, tenant_a, tenant_b,
                                             user_org_admin, token_org_admin):
        """Een volle licentie bij A mag B niet raken."""
        _licentie(db, tenant_a, 1)
        _licentie(db, tenant_b, 5)
        assert maximum_actieve_gebruikers(db, tenant_b.id) == 5
        assert aantal_actieve_gebruikers(db, tenant_b.id) == 0

    def test_bestaande_gebruikers_blijven_werken_bij_een_overschreden_licentie(
        self, client, db, tenant_a, user_org_user, user_org_admin, token_org_user
    ):
        """Een te krappe licentie sluit niemand buiten die er al is."""
        _licentie(db, tenant_a, 1)   # er zijn er al twee actief
        assert client.get("/api/auth/me", headers=auth(token_org_user)).status_code == 200

    def test_rolwijziging_wordt_niet_geraakt(self, client, db, tenant_a, user_org_user,
                                              user_org_admin, token_org_admin):
        """De grens gaat over aantallen, niet over rollen."""
        _licentie(db, tenant_a, 1)
        res = client.patch(f"/api/org/users/{user_org_user.id}",
                           json={"role": "ORG_ADMIN"}, headers=auth(token_org_admin))
        assert res.status_code == 200, res.text

    def test_wachtwoord_resetten_wordt_niet_geraakt(self, client, db, tenant_a, user_org_user,
                                                     user_org_admin, token_org_admin):
        _licentie(db, tenant_a, 1)
        res = client.post(f"/api/org/users/{user_org_user.id}/reset-password",
                          json={"new_password": "EenAnderLangWachtwoord2!"},
                          headers=auth(token_org_admin))
        assert res.status_code == 204, res.text

    def test_verwijderen_wordt_niet_geraakt(self, client, db, tenant_a, user_org_admin,
                                             token_org_admin):
        doelwit = _gebruiker(db, tenant_a, "tijdelijk@example.org")
        _licentie(db, tenant_a, 1)
        res = client.delete(f"/api/org/users/{doelwit.id}", headers=auth(token_org_admin))
        assert res.status_code == 204, res.text


class TestNietGeerfdEnNieuweOrganisatie:
    """Twee grenzen van de keuze, vastgelegd zodat ze zichtbaar zijn als ze wijzigen."""

    def test_een_licentie_van_de_rso_dekt_het_kind_niet(self, db):
        """Een organisatie onder een RSO valt niet onder de RSO-licentie.

        Of dat functioneel de bedoeling is staat nog open; deze test legt alleen vast
        wat het systeem nu doet, zodat een wijziging opvalt.
        """
        rso = Tenant(id=uuid.uuid4(), slug="rso-erf", name="RSO Erf",
                     tenant_type="RSO", is_active=True)
        db.add(rso); db.flush()
        kind = Tenant(id=uuid.uuid4(), slug="kind-erf", name="Kind Erf",
                      tenant_type="ORG", parent_tenant_id=rso.id, is_active=True)
        db.add(kind); db.commit()
        _licentie(db, rso, 1)

        assert maximum_actieve_gebruikers(db, rso.id) == 1
        assert maximum_actieve_gebruikers(db, kind.id) is None, \
            "het kind erft de licentie van de RSO nu niet"

    def test_een_nieuwe_organisatie_heeft_nog_geen_grens(self, client, db, token_rhadix_admin):
        """Daarom is create_tenant bewust niet ingehaakt: er is nog niets om aan te toetsen."""
        res = client.post("/api/admin/tenants", json={
            "slug": "verse-org", "name": "Verse Organisatie",
            "admin_email": "eerste@verse-org.nl", "full_name": "Eerste Beheerder",
            "admin_password": "EenVoldoendeLangWachtwoord1!",
        }, headers=auth(token_rhadix_admin))
        assert res.status_code == 201, res.text
        nieuw = db.query(Tenant).filter(Tenant.slug == "verse-org").first()
        assert maximum_actieve_gebruikers(db, nieuw.id) is None
