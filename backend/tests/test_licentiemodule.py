"""
test_licentiemodule.py — licentiemodule passend gemaakt op het RSO/organisatiemodel.

De licentiemodule bestond al vóór RSO's en onderliggende organisaties bestonden, en is
daarin niet meegegroeid. Vastgelegde keuzes:

  * een licentie hangt RECHTSTREEKS aan een organisatie of aan een RSO en wordt NIET
    geërfd door onderliggende organisaties;
  * per organisatie ten hoogste ÉÉN actieve licentie; historische licenties blijven als
    inactief bestaan;
  * beheer blijft centraal bij RHADIX_ADMIN; RSO_ADMIN en ORG_ADMIN krijgen uitsluitend
    inzage;
  * een organisatie zonder licentie is een geldig antwoord (`heeft_licentie=False`), geen
    404 en geen blokkade — wat "geen licentie" functioneel betekent is bevinding 6.

Daarnaast de fout die maakte dat een eenmaal gezette grens nooit meer op te heffen was:
PATCH las `null` als "niet wijzigen", terwijl juist `null` de betekenis "onbeperkt" draagt.
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.auth.security import hash_password
from app.models.auth_models import License, Tenant, User, UserRole


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def _licentie(db, tenant, max_users=None, actief=True, naam="Testlicentie", valid_until=None):
    lic = License(id=uuid.uuid4(), tenant_id=tenant.id, name=naam,
                  max_users=max_users, is_active=actief, valid_until=valid_until)
    db.add(lic); db.commit(); db.refresh(lic)
    return lic


def _gebruiker(db, tenant, email, rol=UserRole.ORG_USER, actief=True):
    u = User(id=uuid.uuid4(), tenant_id=tenant.id, email=email, full_name=email,
             password_hash=hash_password("EenVoldoendeLangWachtwoord1!"),
             role=rol, is_active=actief)
    db.add(u); db.commit(); db.refresh(u)
    return u


# ── De PATCH-fout: een grens moet ook weer op te heffen zijn ────────────────

class TestGrensOpheffen:
    """`null` betekent WISSEN; een weggelaten veld betekent NIET WIJZIGEN."""

    def test_max_users_kan_terug_naar_onbeperkt(self, client, db, tenant_a, token_rhadix_admin):
        lic = _licentie(db, tenant_a, max_users=5)
        res = client.patch(f"/api/admin/licenses/{lic.id}", json={"max_users": None},
                           headers=auth(token_rhadix_admin))
        assert res.status_code == 200, res.text
        assert res.json()["max_users"] is None
        db.expire_all()
        assert db.query(License).filter(License.id == lic.id).first().max_users is None

    def test_valid_until_kan_terug_naar_geen_einddatum(self, client, db, tenant_a,
                                                        token_rhadix_admin):
        lic = _licentie(db, tenant_a, valid_until=datetime(2026, 12, 31, tzinfo=timezone.utc))
        res = client.patch(f"/api/admin/licenses/{lic.id}", json={"valid_until": None},
                           headers=auth(token_rhadix_admin))
        assert res.status_code == 200, res.text
        assert res.json()["valid_until"] is None

    def test_een_weggelaten_veld_blijft_ongemoeid(self, client, db, tenant_a, token_rhadix_admin):
        """Anders zou elke naamswijziging stilzwijgend de grens wissen."""
        lic = _licentie(db, tenant_a, max_users=5,
                        valid_until=datetime(2026, 12, 31, tzinfo=timezone.utc))
        res = client.patch(f"/api/admin/licenses/{lic.id}", json={"name": "Andere naam"},
                           headers=auth(token_rhadix_admin))
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["name"] == "Andere naam"
        assert body["max_users"] == 5, "een weggelaten max_users mag niet gewist worden"
        assert body["valid_until"] is not None

    def test_een_leeg_verzoek_verandert_niets(self, client, db, tenant_a, token_rhadix_admin):
        lic = _licentie(db, tenant_a, max_users=5, naam="Ongewijzigd")
        res = client.patch(f"/api/admin/licenses/{lic.id}", json={},
                           headers=auth(token_rhadix_admin))
        assert res.status_code == 200, res.text
        assert res.json()["max_users"] == 5
        assert res.json()["name"] == "Ongewijzigd"

    def test_de_naam_wordt_niet_gewist_door_null(self, client, db, tenant_a, token_rhadix_admin):
        """`name` is NOT NULL in de database; daar kan null niets betekenen."""
        lic = _licentie(db, tenant_a, naam="Blijft staan")
        res = client.patch(f"/api/admin/licenses/{lic.id}", json={"name": None},
                           headers=auth(token_rhadix_admin))
        assert res.status_code == 200, res.text
        assert res.json()["name"] == "Blijft staan"

    def test_max_users_nul_of_negatief_wordt_geweigerd(self, client, db, tenant_a,
                                                        token_rhadix_admin):
        lic = _licentie(db, tenant_a, max_users=5)
        for waarde in (0, -3):
            res = client.patch(f"/api/admin/licenses/{lic.id}", json={"max_users": waarde},
                               headers=auth(token_rhadix_admin))
            assert res.status_code == 422, f"{waarde}: {res.text}"

    def test_een_grens_opheffen_geeft_meteen_weer_ruimte(self, client, db, tenant_a,
                                                          user_org_admin, token_rhadix_admin,
                                                          token_org_admin):
        """De hele reden dat dit een fout was: de blokkade was niet ongedaan te maken."""
        lic = _licentie(db, tenant_a, max_users=1)
        nieuw = {"email": "na.opheffen@example.org", "full_name": "N", "role": "ORG_USER",
                 "password": "EenVoldoendeLangWachtwoord1!"}
        assert client.post("/api/org/users", json=nieuw,
                           headers=auth(token_org_admin)).status_code == 400

        client.patch(f"/api/admin/licenses/{lic.id}", json={"max_users": None},
                     headers=auth(token_rhadix_admin))

        assert client.post("/api/org/users", json=nieuw,
                           headers=auth(token_org_admin)).status_code == 201


# ── Eén actieve licentie per organisatie ────────────────────────────────────

class TestEenActieveLicentie:

    def _nieuw(self, tenant, naam="Tweede licentie"):
        return {"tenant_id": str(tenant.id), "name": naam}

    def test_een_tweede_actieve_licentie_wordt_geweigerd(self, client, db, tenant_a,
                                                          token_rhadix_admin):
        _licentie(db, tenant_a, naam="Eerste")
        res = client.post("/api/admin/licenses/", json=self._nieuw(tenant_a),
                          headers=auth(token_rhadix_admin))
        assert res.status_code == 400, res.text
        assert "al een actieve licentie" in res.json()["detail"]
        assert "Eerste" in res.json()["detail"], "de melding noemt niet wélke licentie"

    def test_naast_een_inactieve_licentie_mag_het_wel(self, client, db, tenant_a,
                                                       token_rhadix_admin):
        """Historische licenties blijven bewaard, maar staan een nieuwe niet in de weg."""
        _licentie(db, tenant_a, naam="Vorig jaar", actief=False)
        res = client.post("/api/admin/licenses/", json=self._nieuw(tenant_a, "Dit jaar"),
                          headers=auth(token_rhadix_admin))
        assert res.status_code == 201, res.text

    def test_een_tweede_licentie_activeren_wordt_geweigerd(self, client, db, tenant_a,
                                                            token_rhadix_admin):
        _licentie(db, tenant_a, naam="Actief")
        oud = _licentie(db, tenant_a, naam="Oud", actief=False)
        res = client.patch(f"/api/admin/licenses/{oud.id}", json={"is_active": True},
                           headers=auth(token_rhadix_admin))
        assert res.status_code == 400, res.text

    def test_de_eigen_licentie_bijwerken_blijft_gewoon_lukken(self, client, db, tenant_a,
                                                               token_rhadix_admin):
        """De regel mag niet in de weg zitten bij het bewerken van de enige licentie."""
        lic = _licentie(db, tenant_a, max_users=5)
        res = client.patch(f"/api/admin/licenses/{lic.id}",
                           json={"max_users": 10, "is_active": True},
                           headers=auth(token_rhadix_admin))
        assert res.status_code == 200, res.text
        assert res.json()["max_users"] == 10

    def test_een_andere_organisatie_wordt_niet_geraakt(self, client, db, tenant_a, tenant_b,
                                                        token_rhadix_admin):
        _licentie(db, tenant_a, naam="Van A")
        res = client.post("/api/admin/licenses/", json=self._nieuw(tenant_b, "Van B"),
                          headers=auth(token_rhadix_admin))
        assert res.status_code == 201, res.text

    def test_max_users_nul_wordt_bij_aanmaken_geweigerd(self, client, db, tenant_a,
                                                         token_rhadix_admin):
        res = client.post("/api/admin/licenses/",
                          json={"tenant_id": str(tenant_a.id), "name": "Nul", "max_users": 0},
                          headers=auth(token_rhadix_admin))
        assert res.status_code == 422, res.text


# ── Organisatiecontext in het beheeroverzicht ───────────────────────────────

class TestOrganisatieContext:
    """KIK-V (RSO) en kik-g (organisatie eronder) moeten te onderscheiden zijn."""

    def test_licentie_draagt_naam_type_en_ouder(self, client, db, token_rhadix_admin):
        rso = Tenant(id=uuid.uuid4(), slug="rso-ctx", name="RSO Context",
                     tenant_type="RSO", is_active=True)
        db.add(rso); db.flush()
        kind = Tenant(id=uuid.uuid4(), slug="kind-ctx", name="Kind Context",
                      tenant_type="ORG", parent_tenant_id=rso.id, is_active=True)
        db.add(kind); db.commit()
        _gebruiker(db, kind, "iemand@kind-ctx.nl")
        _licentie(db, kind, max_users=3, naam="Licentie kind")

        res = client.get("/api/admin/licenses/", headers=auth(token_rhadix_admin))
        assert res.status_code == 200, res.text
        regel = next(r for r in res.json() if r["name"] == "Licentie kind")
        assert regel["tenant_name"] == "Kind Context"
        assert regel["tenant_type"] == "ORG"
        assert regel["parent_tenant_name"] == "RSO Context"
        assert regel["actieve_gebruikers"] == 1

    def test_tenantlijst_telt_actieve_gebruikers_apart(self, client, db, tenant_a,
                                                        user_org_user, token_rhadix_admin):
        _gebruiker(db, tenant_a, "slapend@example.org", actief=False)
        res = client.get("/api/admin/tenants/", headers=auth(token_rhadix_admin))
        regel = next(r for r in res.json() if r["id"] == str(tenant_a.id))
        assert regel["active_user_count"] == regel["user_count"] - 1, \
            "de gedeactiveerde gebruiker telt wel in user_count, niet in active_user_count"


# ── Inzage voor RSO_ADMIN ───────────────────────────────────────────────────

class TestRsoInzage:

    @pytest.fixture()
    def rso_boom(self, db):
        from tests.conftest import make_token
        rso = Tenant(id=uuid.uuid4(), slug="rso-inz", name="RSO Inzage",
                     tenant_type="RSO", is_active=True)
        db.add(rso); db.flush()
        beheerder = User(id=uuid.uuid4(), tenant_id=rso.id, email="beheer@rso-inz.nl",
                         password_hash=hash_password("EenVoldoendeLangWachtwoord1!"),
                         role=UserRole.RSO_ADMIN, is_active=True)
        db.add(beheerder)
        met_lic = Tenant(id=uuid.uuid4(), slug="kind-met", name="Kind Met Licentie",
                         tenant_type="ORG", parent_tenant_id=rso.id, is_active=True)
        zonder  = Tenant(id=uuid.uuid4(), slug="kind-zonder", name="Kind Zonder Licentie",
                         tenant_type="ORG", parent_tenant_id=rso.id, is_active=True)
        db.add_all([met_lic, zonder]); db.commit()
        _licentie(db, rso, max_users=2, naam="RSO-licentie")
        _licentie(db, met_lic, max_users=4, naam="Kindlicentie")
        _gebruiker(db, met_lic, "a@kind-met.nl")
        return rso, met_lic, zonder, make_token(beheerder)

    def test_rso_ziet_eigen_rso_en_kinderen(self, client, db, rso_boom):
        rso, met_lic, zonder, token = rso_boom
        res = client.get("/api/rso/licenses", headers=auth(token))
        assert res.status_code == 200, res.text
        namen = [r["tenant_name"] for r in res.json()]
        assert namen == ["RSO Inzage", "Kind Met Licentie", "Kind Zonder Licentie"], \
            "eigen RSO hoort bovenaan, kinderen daaronder op naam"

    def test_een_organisatie_zonder_licentie_komt_gewoon_in_de_lijst(self, client, db, rso_boom):
        """Anders is 'nog niets ingericht' niet te onderscheiden van 'bestaat niet'."""
        *_, token = rso_boom
        regels = client.get("/api/rso/licenses", headers=auth(token)).json()
        leeg = next(r for r in regels if r["tenant_name"] == "Kind Zonder Licentie")
        assert leeg["heeft_licentie"] is False
        assert leeg["max_users"] is None
        assert leeg["licentie_naam"] is None

    def test_de_eigen_rso_is_als_zodanig_herkenbaar(self, client, db, rso_boom):
        *_, token = rso_boom
        regels = client.get("/api/rso/licenses", headers=auth(token)).json()
        assert [r["is_eigen_rso"] for r in regels] == [True, False, False]

    def test_de_licentie_van_het_kind_is_niet_die_van_de_rso(self, client, db, rso_boom):
        """De kern van het model: er wordt niets geërfd."""
        *_, token = rso_boom
        regels = client.get("/api/rso/licenses", headers=auth(token)).json()
        per_naam = {r["tenant_name"]: r for r in regels}
        assert per_naam["RSO Inzage"]["max_users"] == 2
        assert per_naam["Kind Met Licentie"]["max_users"] == 4
        assert per_naam["Kind Zonder Licentie"]["max_users"] is None

    def test_organisaties_buiten_de_eigen_boom_zijn_onzichtbaar(self, client, db, rso_boom,
                                                                 tenant_a):
        *_, token = rso_boom
        _licentie(db, tenant_a, naam="Niet van jou")
        regels = client.get("/api/rso/licenses", headers=auth(token)).json()
        assert all(r["licentie_naam"] != "Niet van jou" for r in regels)
        assert all(r["tenant_id"] != str(tenant_a.id) for r in regels)

    def test_interne_aantekeningen_lekken_niet(self, client, db, rso_boom):
        *_, token = rso_boom
        regels = client.get("/api/rso/licenses", headers=auth(token)).json()
        for r in regels:
            assert "notes" not in r
            assert "created_by_id" not in r

    def test_een_org_admin_komt_hier_niet_binnen(self, client, db, token_org_admin):
        assert client.get("/api/rso/licenses",
                          headers=auth(token_org_admin)).status_code == 403

    def test_de_rso_route_kent_geen_schrijfbewerking_op_licenties(self, client, db, rso_boom):
        """Beheer blijft centraal; deze router mag nooit een licentie kunnen wijzigen."""
        rso, met_lic, _, token = rso_boom
        for methode, pad in [("post",   "/api/rso/licenses"),
                             ("patch",  "/api/rso/licenses"),
                             ("delete", "/api/rso/licenses")]:
            res = getattr(client, methode)(pad, headers=auth(token))
            assert res.status_code in (404, 405), f"{methode.upper()} {pad}: {res.status_code}"


# ── Inzage voor ORG_ADMIN ───────────────────────────────────────────────────

class TestOrgInzage:

    def test_org_admin_ziet_de_eigen_licentie(self, client, db, tenant_a, user_org_admin,
                                               token_org_admin):
        _licentie(db, tenant_a, max_users=7, naam="Onze licentie")
        res = client.get("/api/org/license", headers=auth(token_org_admin))
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["heeft_licentie"] is True
        assert body["licentie_naam"] == "Onze licentie"
        assert body["max_users"] == 7
        assert body["tenant_name"] == tenant_a.name

    def test_zonder_licentie_komt_er_geen_fout_maar_een_antwoord(self, client, db, tenant_a,
                                                                  token_org_admin):
        res = client.get("/api/org/license", headers=auth(token_org_admin))
        assert res.status_code == 200, res.text
        assert res.json()["heeft_licentie"] is False

    def test_het_aantal_actieve_gebruikers_staat_erbij(self, client, db, tenant_a,
                                                        user_org_admin, token_org_admin):
        """Zodat 'het maximum is bereikt' te plaatsen is."""
        _gebruiker(db, tenant_a, "extra@example.org")
        _gebruiker(db, tenant_a, "slapend@example.org", actief=False)
        _licentie(db, tenant_a, max_users=2)
        body = client.get("/api/org/license", headers=auth(token_org_admin)).json()
        assert body["actieve_gebruikers"] == 2
        assert body["max_users"] == 2

    def test_een_gewone_gebruiker_komt_er_niet_bij(self, client, db, token_org_user):
        assert client.get("/api/org/license",
                          headers=auth(token_org_user)).status_code == 403

    def test_de_licentie_van_een_andere_organisatie_is_onzichtbaar(self, client, db, tenant_a,
                                                                    tenant_b, user_org_admin,
                                                                    token_org_admin):
        _licentie(db, tenant_b, max_users=99, naam="Van B")
        body = client.get("/api/org/license", headers=auth(token_org_admin)).json()
        assert body["tenant_id"] == str(tenant_a.id)
        assert body["licentie_naam"] != "Van B"

    def test_interne_aantekeningen_lekken_niet(self, client, db, tenant_a, token_org_admin):
        _licentie(db, tenant_a)
        body = client.get("/api/org/license", headers=auth(token_org_admin)).json()
        assert "notes" not in body
        assert "created_by_id" not in body

    def test_er_is_geen_route_om_hem_te_wijzigen(self, client, db, tenant_a, token_org_admin):
        _licentie(db, tenant_a, max_users=1)
        for methode in ("post", "patch", "put"):
            res = getattr(client, methode)("/api/org/license", json={"max_users": 99},
                                           headers=auth(token_org_admin))
            assert res.status_code in (404, 405), f"{methode.upper()}: {res.status_code}"
        assert client.delete("/api/org/license",
                             headers=auth(token_org_admin)).status_code in (404, 405)


# ── Geen oordeel over geldigheid: dat is bevinding 6 ────────────────────────

class TestGeldigheidNogGeenOordeel:

    def test_een_verlopen_licentie_wordt_gewoon_getoond(self, client, db, tenant_a,
                                                         token_org_admin):
        """Geen status 'Verlopen' en geen blokkade — die keuze valt bij bevinding 6."""
        verleden = datetime.now(timezone.utc) - timedelta(days=60)
        _licentie(db, tenant_a, max_users=5, valid_until=verleden)
        body = client.get("/api/org/license", headers=auth(token_org_admin)).json()
        assert body["heeft_licentie"] is True
        assert body["valid_until"] is not None
        assert body["max_users"] == 5
        assert "status" not in body, "een geldigheidsoordeel hoort bij bevinding 6"

    def test_een_verlopen_licentie_begrenst_nog_steeds(self, client, db, tenant_a,
                                                        user_org_admin, token_org_admin):
        """Bewust: de telling kijkt naar is_active, niet naar de datum."""
        verleden = datetime.now(timezone.utc) - timedelta(days=60)
        _licentie(db, tenant_a, max_users=1, valid_until=verleden)
        res = client.post("/api/org/users",
                          json={"email": "na.verval@example.org", "full_name": "N",
                                "role": "ORG_USER", "password": "EenVoldoendeLangWachtwoord1!"},
                          headers=auth(token_org_admin))
        assert res.status_code == 400
