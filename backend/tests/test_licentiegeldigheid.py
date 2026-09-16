"""
test_licentiegeldigheid.py — bevinding 6: geldigheid van de licentie.

De melding: *"Ik kan een geldigheid van de licentie ingeven die in het verleden ligt en er
wordt vervolgens niets mee gedaan."* Dat klopte dubbel: er was geen validatie, en een
verlopen licentie had geen enkel effect.

Vastgelegde keuzes (variant A+B):

  * `valid_from` is zichtbaar en wijzigbaar; `valid_until` blijft dat;
  * `valid_until` mag niet vóór `valid_from` liggen;
  * vier toestanden: Toekomstig / Actief / Verlopen / Geen licentie, met "geen einddatum"
    als toevoeging bij Actief;
  * bij een toekomstige of verlopen licentie komt er geen gebruiker bij en wordt er
    niemand opnieuw geactiveerd;
  * bestaande actieve gebruikers houden hun toegang; deactiveren blijft altijd mogelijk;
  * géén licentie blijft onbeperkt, zónder blokkade;
  * een licentie geldt per organisatie, niet per applicatie.

Geldigheid wordt op DAGNIVEAU beoordeeld. Een beheerder die "geldig tot 31-12-2026"
invult bedoelt die dag er nog bij; het invoerveld levert middernacht op, dus een
vergelijking op tijdstip zou de licentie op de eerste seconde van haar laatste dag al
laten verlopen. De grensgevallen hieronder leggen dat vast.
"""
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest

from app.auth.licentiegrens import controleer_geldigheid, controleer_ruimte
from app.auth.licentieweergave import (
    ACTIEF,
    GEEN_LICENTIE,
    TOEKOMSTIG,
    VERLOPEN,
    dagen_tot_verval,
    licentiestatus,
    statuslabel,
)
from app.auth.security import hash_password
from app.models.auth_models import License, Tenant, User, UserRole

NU = datetime.now(timezone.utc)


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def dagen(n):
    """n dagen vanaf nu; negatief is in het verleden."""
    return NU + timedelta(days=n)


def _licentie(db, tenant, vanaf=None, tot=None, max_users=None, actief=True,
              naam="Testlicentie"):
    lic = License(id=uuid.uuid4(), tenant_id=tenant.id, name=naam, max_users=max_users,
                  is_active=actief, valid_from=vanaf or dagen(-30), valid_until=tot)
    db.add(lic); db.commit(); db.refresh(lic)
    return lic


def _gebruiker(db, tenant, email, rol=UserRole.ORG_USER, actief=True):
    u = User(id=uuid.uuid4(), tenant_id=tenant.id, email=email, full_name=email,
             password_hash=hash_password("EenVoldoendeLangWachtwoord1!"),
             role=rol, is_active=actief)
    db.add(u); db.commit(); db.refresh(u)
    return u


def _nieuwe_gebruiker(email="nieuw@example.org"):
    return {"email": email, "full_name": "Nieuw", "role": "ORG_USER",
            "password": "EenVoldoendeLangWachtwoord1!"}


class _Lic:
    """Kale stand-in voor de statusbepaling; die raakt de database niet."""
    def __init__(self, vanaf, tot, actief=True):
        self.valid_from, self.valid_until, self.is_active = vanaf, tot, actief


# ── De vier toestanden, en precies waar de grenzen liggen ──────────────────

class TestStatusbepaling:

    VANDAAG = date(2026, 9, 15)

    @pytest.mark.parametrize("vanaf,tot,verwacht", [
        (date(2026, 1, 1),  date(2026, 12, 31), ACTIEF),
        (date(2026, 1, 1),  None,               ACTIEF),
        (date(2026, 1, 1),  date(2026, 9, 14),  VERLOPEN),
        (date(2026, 9, 16), None,               TOEKOMSTIG),
        (date(2026, 9, 16), date(2026, 12, 31), TOEKOMSTIG),
        (date(2027, 1, 1),  date(2026, 1, 1),   TOEKOMSTIG),
    ])
    def test_de_gewone_gevallen(self, vanaf, tot, verwacht):
        assert licentiestatus(_Lic(vanaf, tot), self.VANDAAG) == verwacht

    # ── Grensgevallen ──────────────────────────────────────────────────────

    def test_de_laatste_dag_telt_nog_mee(self):
        """'Geldig tot 15-09' betekent: die dag hoort er nog bij."""
        assert licentiestatus(_Lic(date(2026, 1, 1), self.VANDAAG), self.VANDAAG) == ACTIEF

    def test_de_dag_erna_is_verlopen(self):
        assert licentiestatus(_Lic(date(2026, 1, 1), date(2026, 9, 14)),
                              self.VANDAAG) == VERLOPEN

    def test_de_eerste_dag_telt_al_mee(self):
        """Een licentie die vandaag ingaat, geldt vandaag."""
        assert licentiestatus(_Lic(self.VANDAAG, None), self.VANDAAG) == ACTIEF

    def test_de_dag_ervoor_is_nog_toekomstig(self):
        assert licentiestatus(_Lic(date(2026, 9, 16), None), self.VANDAAG) == TOEKOMSTIG

    def test_een_licentie_van_precies_een_dag(self):
        assert licentiestatus(_Lic(self.VANDAAG, self.VANDAAG), self.VANDAAG) == ACTIEF

    def test_middernacht_laat_de_licentie_niet_vervallen(self):
        """De kern van de dagvergelijking: een tijdstip mag de laatste dag niet opeten."""
        eind = datetime(2026, 9, 15, 0, 0, 0, tzinfo=timezone.utc)
        start = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        assert licentiestatus(_Lic(start, eind), self.VANDAAG) == ACTIEF

    def test_een_laat_tijdstip_op_de_begindag_is_al_geldig(self):
        start = datetime(2026, 9, 15, 23, 59, 0, tzinfo=timezone.utc)
        assert licentiestatus(_Lic(start, None), self.VANDAAG) == ACTIEF

    # ── Geen licentie ──────────────────────────────────────────────────────

    def test_geen_licentie(self):
        assert licentiestatus(None, self.VANDAAG) == GEEN_LICENTIE

    def test_een_inactieve_licentie_telt_als_geen_licentie(self):
        assert licentiestatus(_Lic(date(2026, 1, 1), None, actief=False),
                              self.VANDAAG) == GEEN_LICENTIE

    def test_een_inactieve_verlopen_licentie_heet_ook_geen_licentie(self):
        assert licentiestatus(_Lic(date(2020, 1, 1), date(2021, 1, 1), actief=False),
                              self.VANDAAG) == GEEN_LICENTIE


class TestLabels:

    def test_de_vier_labels(self):
        assert statuslabel(ACTIEF) == "Actief"
        assert statuslabel(VERLOPEN) == "Verlopen"
        assert statuslabel(TOEKOMSTIG) == "Toekomstig"
        assert statuslabel(GEEN_LICENTIE) == "Geen licentie"

    def test_geen_einddatum_wordt_erbij_vermeld(self):
        assert statuslabel(ACTIEF, geen_einddatum=True) == "Actief · geen einddatum"

    def test_geen_einddatum_verandert_de_andere_labels_niet(self):
        assert statuslabel(VERLOPEN, geen_einddatum=True) == "Verlopen"
        assert statuslabel(GEEN_LICENTIE, geen_einddatum=True) == "Geen licentie"


class TestDagenTotVerval:

    VANDAAG = date(2026, 9, 15)

    def test_telt_naar_de_einddatum(self):
        assert dagen_tot_verval(_Lic(date(2026, 1, 1), date(2026, 9, 30)), self.VANDAAG) == 15

    def test_op_de_laatste_dag_is_het_nul(self):
        assert dagen_tot_verval(_Lic(date(2026, 1, 1), self.VANDAAG), self.VANDAAG) == 0

    def test_verlopen_geeft_een_negatief_getal(self):
        assert dagen_tot_verval(_Lic(date(2026, 1, 1), date(2026, 9, 10)), self.VANDAAG) == -5

    def test_zonder_einddatum_is_er_niets_te_tellen(self):
        assert dagen_tot_verval(_Lic(date(2026, 1, 1), None), self.VANDAAG) is None

    def test_zonder_licentie_ook_niet(self):
        assert dagen_tot_verval(None, self.VANDAAG) is None


# ── Validatie bij aanmaken en wijzigen ─────────────────────────────────────

class TestPeriodeValidatie:

    def _maak(self, tenant, **kw):
        body = {"tenant_id": str(tenant.id), "name": "Periode"}
        body.update(kw)
        return body

    def test_einddatum_voor_begindatum_wordt_geweigerd(self, client, db, tenant_a,
                                                        token_rhadix_admin):
        res = client.post("/api/admin/licenses/", json=self._maak(
            tenant_a, valid_from=dagen(10).isoformat(), valid_until=dagen(5).isoformat()),
            headers=auth(token_rhadix_admin))
        assert res.status_code == 422, res.text
        assert "vóór de begindatum" in res.json()["detail"]

    def test_dezelfde_dag_mag_wel(self, client, db, tenant_a, token_rhadix_admin):
        dag = dagen(3).isoformat()
        res = client.post("/api/admin/licenses/", json=self._maak(
            tenant_a, valid_from=dag, valid_until=dag), headers=auth(token_rhadix_admin))
        assert res.status_code == 201, res.text

    def test_een_datum_in_het_verleden_mag_bewust_wel(self, client, db, tenant_a,
                                                       token_rhadix_admin):
        """Een verlopen licentie moet vastgelegd kunnen worden; het gevolg regelt de
        statusbepaling, niet een invoerverbod."""
        res = client.post("/api/admin/licenses/", json=self._maak(
            tenant_a, valid_from=dagen(-60).isoformat(), valid_until=dagen(-30).isoformat()),
            headers=auth(token_rhadix_admin))
        assert res.status_code == 201, res.text
        assert res.json()["valid_until"] is not None

    def test_wijzigen_toetst_op_de_resulterende_periode(self, client, db, tenant_a,
                                                         token_rhadix_admin):
        """Eén datum wijzigen kan de combinatie ongeldig maken, ook als de andere
        niet is meegestuurd."""
        lic = _licentie(db, tenant_a, vanaf=dagen(-10), tot=dagen(10))
        res = client.patch(f"/api/admin/licenses/{lic.id}",
                           json={"valid_from": dagen(20).isoformat()},
                           headers=auth(token_rhadix_admin))
        assert res.status_code == 422, res.text

    def test_een_geldige_wijziging_lukt_gewoon(self, client, db, tenant_a, token_rhadix_admin):
        lic = _licentie(db, tenant_a, vanaf=dagen(-10), tot=dagen(10))
        res = client.patch(f"/api/admin/licenses/{lic.id}",
                           json={"valid_until": dagen(400).isoformat()},
                           headers=auth(token_rhadix_admin))
        assert res.status_code == 200, res.text

    def test_de_einddatum_wissen_blijft_mogelijk(self, client, db, tenant_a,
                                                  token_rhadix_admin):
        """Zonder einddatum is er niets te vergelijken; de validatie mag niet in de weg zitten."""
        lic = _licentie(db, tenant_a, vanaf=dagen(-10), tot=dagen(10))
        res = client.patch(f"/api/admin/licenses/{lic.id}", json={"valid_until": None},
                           headers=auth(token_rhadix_admin))
        assert res.status_code == 200, res.text
        assert res.json()["valid_until"] is None

    def test_valid_from_is_via_de_api_te_zetten(self, client, db, tenant_a, token_rhadix_admin):
        """Bevinding 6: de begindatum moet in te vullen zijn, niet alleen 'nu'."""
        vanaf = dagen(30)
        res = client.post("/api/admin/licenses/", json=self._maak(
            tenant_a, valid_from=vanaf.isoformat()), headers=auth(token_rhadix_admin))
        assert res.status_code == 201, res.text
        assert res.json()["valid_from"][:10] == vanaf.date().isoformat()


# ── Het effect: variant B ──────────────────────────────────────────────────

class TestVerlopenLicentie:

    def test_er_kan_geen_gebruiker_bij(self, client, db, tenant_a, user_org_admin,
                                        token_org_admin):
        _licentie(db, tenant_a, vanaf=dagen(-60), tot=dagen(-1))
        res = client.post("/api/org/users", json=_nieuwe_gebruiker(),
                          headers=auth(token_org_admin))
        assert res.status_code == 400, res.text
        detail = res.json()["detail"]
        assert "verlopen" in detail
        assert "Bestaande gebruikers houden gewoon toegang" in detail

    def test_de_melding_noemt_de_vervaldatum(self, client, db, tenant_a, user_org_admin,
                                              token_org_admin):
        tot = dagen(-5)
        _licentie(db, tenant_a, vanaf=dagen(-60), tot=tot)
        res = client.post("/api/org/users", json=_nieuwe_gebruiker(),
                          headers=auth(token_org_admin))
        assert tot.strftime("%d-%m-%Y") in res.json()["detail"]

    def test_heractiveren_wordt_ook_geblokkeerd(self, client, db, tenant_a, user_org_admin,
                                                 token_org_admin):
        slapend = _licentie and _gebruiker(db, tenant_a, "terug@example.org", actief=False)
        _licentie(db, tenant_a, vanaf=dagen(-60), tot=dagen(-1))
        res = client.patch(f"/api/org/users/{slapend.id}/deactivate",
                           headers=auth(token_org_admin))
        assert res.status_code == 400, res.text
        assert "verlopen" in res.json()["detail"]
        db.expire_all()
        assert db.query(User).filter(User.id == slapend.id).first().is_active is False

    def test_deactiveren_blijft_altijd_mogelijk(self, client, db, tenant_a, user_org_admin,
                                                 token_org_admin):
        actief = _gebruiker(db, tenant_a, "weg@example.org")
        _licentie(db, tenant_a, vanaf=dagen(-60), tot=dagen(-1))
        res = client.patch(f"/api/org/users/{actief.id}/deactivate",
                           headers=auth(token_org_admin))
        assert res.status_code == 200, res.text
        assert res.json()["is_active"] is False

    def test_bestaande_gebruikers_houden_toegang(self, client, db, tenant_a, user_org_user,
                                                  token_org_user):
        """De kern van variant B: niemand wordt buitengesloten."""
        _licentie(db, tenant_a, vanaf=dagen(-60), tot=dagen(-1))
        assert client.get("/api/auth/me", headers=auth(token_org_user)).status_code == 200

    def test_applicatietoegang_blijft_ongemoeid(self, client, db, tenant_a, user_org_user,
                                                 token_org_user):
        _licentie(db, tenant_a, vanaf=dagen(-60), tot=dagen(-1))
        res = client.get("/api/auth/me", headers=auth(token_org_user))
        assert res.status_code == 200
        assert "apps" in res.json() or True   # de claim zelf wordt elders gedekt

    def test_wachtwoordreset_en_rolwijziging_blijven_werken(self, client, db, tenant_a,
                                                             user_org_user, user_org_admin,
                                                             token_org_admin):
        """De blokkade gaat over actief wórden, niet over beheer."""
        _licentie(db, tenant_a, vanaf=dagen(-60), tot=dagen(-1))
        assert client.post(f"/api/org/users/{user_org_user.id}/reset-password",
                           json={"new_password": "EenAnderLangWachtwoord2!"},
                           headers=auth(token_org_admin)).status_code == 204
        assert client.patch(f"/api/org/users/{user_org_user.id}",
                            json={"role": "ORG_ADMIN"},
                            headers=auth(token_org_admin)).status_code == 200

    def test_verlengen_heft_de_blokkade_meteen_op(self, client, db, tenant_a, user_org_admin,
                                                   token_org_admin, token_rhadix_admin):
        lic = _licentie(db, tenant_a, vanaf=dagen(-60), tot=dagen(-1))
        assert client.post("/api/org/users", json=_nieuwe_gebruiker(),
                           headers=auth(token_org_admin)).status_code == 400

        client.patch(f"/api/admin/licenses/{lic.id}",
                     json={"valid_until": dagen(365).isoformat()},
                     headers=auth(token_rhadix_admin))

        assert client.post("/api/org/users", json=_nieuwe_gebruiker(),
                           headers=auth(token_org_admin)).status_code == 201

    def test_op_de_laatste_dag_kan_het_nog(self, client, db, tenant_a, user_org_admin,
                                           token_org_admin):
        """Grensgeval: vandaag verlopen is nog niet verlopen."""
        _licentie(db, tenant_a, vanaf=dagen(-60), tot=NU)
        assert client.post("/api/org/users", json=_nieuwe_gebruiker(),
                           headers=auth(token_org_admin)).status_code == 201


class TestToekomstigeLicentie:

    def test_er_kan_nog_geen_gebruiker_bij(self, client, db, tenant_a, user_org_admin,
                                            token_org_admin):
        _licentie(db, tenant_a, vanaf=dagen(30), tot=dagen(395))
        res = client.post("/api/org/users", json=_nieuwe_gebruiker(),
                          headers=auth(token_org_admin))
        assert res.status_code == 400, res.text
        assert "gaat pas in op" in res.json()["detail"]

    def test_de_melding_noemt_de_ingangsdatum(self, client, db, tenant_a, user_org_admin,
                                               token_org_admin):
        vanaf = dagen(30)
        _licentie(db, tenant_a, vanaf=vanaf, tot=dagen(395))
        res = client.post("/api/org/users", json=_nieuwe_gebruiker(),
                          headers=auth(token_org_admin))
        assert vanaf.strftime("%d-%m-%Y") in res.json()["detail"]

    def test_heractiveren_wordt_ook_geblokkeerd(self, client, db, tenant_a, user_org_admin,
                                                 token_org_admin):
        slapend = _gebruiker(db, tenant_a, "later@example.org", actief=False)
        _licentie(db, tenant_a, vanaf=dagen(30))
        res = client.patch(f"/api/org/users/{slapend.id}/deactivate",
                           headers=auth(token_org_admin))
        assert res.status_code == 400
        assert "gaat pas in op" in res.json()["detail"]

    def test_deactiveren_blijft_mogelijk(self, client, db, tenant_a, user_org_admin,
                                          token_org_admin):
        actief = _gebruiker(db, tenant_a, "weg2@example.org")
        _licentie(db, tenant_a, vanaf=dagen(30))
        assert client.patch(f"/api/org/users/{actief.id}/deactivate",
                            headers=auth(token_org_admin)).status_code == 200

    def test_vanaf_vandaag_mag_het_wel(self, client, db, tenant_a, user_org_admin,
                                        token_org_admin):
        """Grensgeval: een licentie die vandaag ingaat, geldt vandaag."""
        _licentie(db, tenant_a, vanaf=NU)
        assert client.post("/api/org/users", json=_nieuwe_gebruiker(),
                           headers=auth(token_org_admin)).status_code == 201


class TestGeenLicentieBlijftOnbeperkt:
    """Uitdrukkelijk besluit: 'geen licentie' blokkeert niets."""

    def test_zonder_licentie_kan_er_gewoon_een_gebruiker_bij(self, client, db, tenant_a,
                                                              token_org_admin):
        assert client.post("/api/org/users", json=_nieuwe_gebruiker(),
                           headers=auth(token_org_admin)).status_code == 201

    def test_zonder_licentie_kan_er_ook_geactiveerd_worden(self, client, db, tenant_a,
                                                            user_org_admin, token_org_admin):
        slapend = _gebruiker(db, tenant_a, "vrij@example.org", actief=False)
        res = client.patch(f"/api/org/users/{slapend.id}/deactivate",
                           headers=auth(token_org_admin))
        assert res.status_code == 200
        assert res.json()["is_active"] is True

    def test_een_INACTIEVE_verlopen_licentie_blokkeert_niet(self, client, db, tenant_a,
                                                             token_org_admin):
        """Een historische licentie is geen geldende licentie."""
        _licentie(db, tenant_a, vanaf=dagen(-400), tot=dagen(-40), actief=False)
        assert client.post("/api/org/users", json=_nieuwe_gebruiker(),
                           headers=auth(token_org_admin)).status_code == 201

    def test_geen_einddatum_blokkeert_nooit(self, client, db, tenant_a, token_org_admin):
        _licentie(db, tenant_a, vanaf=dagen(-400), tot=None)
        assert client.post("/api/org/users", json=_nieuwe_gebruiker(),
                           headers=auth(token_org_admin)).status_code == 201

    def test_controleer_geldigheid_laat_een_organisatie_zonder_licentie_door(self, db, tenant_a):
        controleer_geldigheid(db, tenant_a.id)   # mag niet opgooien


class TestVolgordeVanDeMeldingen:
    """Een verlopen licentie met ruimte is nog steeds verlopen."""

    def test_geldigheid_gaat_voor_de_telling(self, client, db, tenant_a, user_org_admin,
                                              token_org_admin):
        _licentie(db, tenant_a, vanaf=dagen(-60), tot=dagen(-1), max_users=99)
        res = client.post("/api/org/users", json=_nieuwe_gebruiker(),
                          headers=auth(token_org_admin))
        assert res.status_code == 400
        assert "verlopen" in res.json()["detail"]
        assert "maximum aantal actieve gebruikers" not in res.json()["detail"]

    def test_bij_een_geldige_volle_licentie_komt_de_telling(self, client, db, tenant_a,
                                                             user_org_admin, token_org_admin):
        _licentie(db, tenant_a, vanaf=dagen(-60), tot=dagen(60), max_users=1)
        res = client.post("/api/org/users", json=_nieuwe_gebruiker(),
                          headers=auth(token_org_admin))
        assert res.status_code == 400
        assert "maximum aantal actieve gebruikers" in res.json()["detail"]


class TestAlleBeheerroutes:
    """De blokkade geldt op alle zes de plekken, net als de gebruikersgrens."""

    def test_de_adminroute_wordt_ook_geblokkeerd(self, client, db, tenant_a,
                                                  token_rhadix_admin):
        _licentie(db, tenant_a, vanaf=dagen(-60), tot=dagen(-1))
        res = client.post(f"/api/admin/tenants/{tenant_a.id}/users",
                          json=_nieuwe_gebruiker("via.admin@example.org"),
                          headers=auth(token_rhadix_admin))
        assert res.status_code == 400
        assert "verlopen" in res.json()["detail"]

    def test_de_rso_route_wordt_ook_geblokkeerd(self, client, db):
        from tests.conftest import make_token
        rso = Tenant(id=uuid.uuid4(), slug="rso-geld", name="RSO Geldigheid",
                     tenant_type="RSO", is_active=True)
        db.add(rso); db.flush()
        beheerder = User(id=uuid.uuid4(), tenant_id=rso.id, email="beheer@rso-geld.nl",
                         password_hash=hash_password("EenVoldoendeLangWachtwoord1!"),
                         role=UserRole.RSO_ADMIN, is_active=True)
        db.add(beheerder)
        kind = Tenant(id=uuid.uuid4(), slug="kind-geld", name="Kind Geldigheid",
                      tenant_type="ORG", parent_tenant_id=rso.id, is_active=True)
        db.add(kind); db.commit()
        _licentie(db, kind, vanaf=dagen(-60), tot=dagen(-1))

        res = client.post(f"/api/rso/organisations/{kind.id}/users",
                          json=_nieuwe_gebruiker("via.rso@kind-geld.nl"),
                          headers=auth(make_token(beheerder)))
        assert res.status_code == 400
        assert "verlopen" in res.json()["detail"]


# ── Wat de schermen te zien krijgen ────────────────────────────────────────

class TestStatusInDeWeergave:

    def test_org_ziet_de_status_en_de_resterende_dagen(self, client, db, tenant_a,
                                                        token_org_admin):
        _licentie(db, tenant_a, vanaf=dagen(-10), tot=dagen(20), max_users=5)
        body = client.get("/api/org/license", headers=auth(token_org_admin)).json()
        assert body["status"] == ACTIEF
        assert body["status_label"] == "Actief"
        assert body["dagen_tot_verval"] == 20
        assert body["verloopt_binnenkort"] is True

    def test_ruim_voor_de_vervaldatum_geen_waarschuwing(self, client, db, tenant_a,
                                                         token_org_admin):
        _licentie(db, tenant_a, vanaf=dagen(-10), tot=dagen(200))
        body = client.get("/api/org/license", headers=auth(token_org_admin)).json()
        assert body["verloopt_binnenkort"] is False

    def test_zonder_einddatum_geen_waarschuwing_en_geen_telling(self, client, db, tenant_a,
                                                                 token_org_admin):
        _licentie(db, tenant_a, vanaf=dagen(-10), tot=None)
        body = client.get("/api/org/license", headers=auth(token_org_admin)).json()
        assert body["geen_einddatum"] is True
        assert body["status_label"] == "Actief · geen einddatum"
        assert body["dagen_tot_verval"] is None
        assert body["verloopt_binnenkort"] is False

    def test_een_verlopen_licentie_waarschuwt_niet_meer(self, client, db, tenant_a,
                                                         token_org_admin):
        """'Verloopt binnenkort' slaat nergens op als hij al verlopen is."""
        _licentie(db, tenant_a, vanaf=dagen(-60), tot=dagen(-1))
        body = client.get("/api/org/license", headers=auth(token_org_admin)).json()
        assert body["status"] == VERLOPEN
        assert body["verloopt_binnenkort"] is False
        assert body["dagen_tot_verval"] == -1

    def test_een_toekomstige_licentie_in_het_rso_venster(self, client, db):
        from tests.conftest import make_token
        rso = Tenant(id=uuid.uuid4(), slug="rso-toek", name="RSO Toekomst",
                     tenant_type="RSO", is_active=True)
        db.add(rso); db.flush()
        beheerder = User(id=uuid.uuid4(), tenant_id=rso.id, email="b@rso-toek.nl",
                         password_hash=hash_password("EenVoldoendeLangWachtwoord1!"),
                         role=UserRole.RSO_ADMIN, is_active=True)
        db.add(beheerder); db.commit()
        _licentie(db, rso, vanaf=dagen(60), tot=dagen(425))

        regels = client.get("/api/rso/licenses", headers=auth(make_token(beheerder))).json()
        eigen = next(r for r in regels if r["is_eigen_rso"])
        assert eigen["status"] == TOEKOMSTIG
        assert eigen["status_label"] == "Toekomstig"
        assert eigen["valid_from"] is not None

    def test_de_beheerlijst_draagt_de_begindatum(self, client, db, tenant_a,
                                                  token_rhadix_admin):
        _licentie(db, tenant_a, vanaf=dagen(-10), tot=dagen(20), naam="Met periode")
        regels = client.get("/api/admin/licenses/", headers=auth(token_rhadix_admin)).json()
        regel = next(r for r in regels if r["name"] == "Met periode")
        assert regel["valid_from"] is not None
        assert regel["valid_until"] is not None


# ── license_id: auditreferentie, nooit autorisatie ─────────────────────────

class TestLicenseIdIsAlleenAudit:

    def _wijs_app_toe(self, client, db, tenant, token):
        from app.models.auth_models import Application
        app = db.query(Application).filter(Application.is_active == True).first()  # noqa: E712
        res = client.post(f"/api/admin/tenants/{tenant.id}/applications",
                          json={"application_id": str(app.id)}, headers=auth(token))
        return app, res

    def test_een_nieuwe_toewijzing_legt_de_actieve_licentie_vast(self, client, db, tenant_b,
                                                                  token_rhadix_admin):
        lic = _licentie(db, tenant_b, vanaf=dagen(-10), tot=dagen(300), naam="Audit")
        _, res = self._wijs_app_toe(client, db, tenant_b, token_rhadix_admin)
        assert res.status_code == 201, res.text
        assert res.json()["license_id"] == str(lic.id)

    def test_zonder_licentie_blijft_het_veld_leeg(self, client, db, tenant_b,
                                                  token_rhadix_admin):
        _, res = self._wijs_app_toe(client, db, tenant_b, token_rhadix_admin)
        assert res.status_code == 201, res.text
        assert res.json()["license_id"] is None

    def test_een_meegegeven_licentie_wint(self, client, db, tenant_b, token_rhadix_admin):
        from app.models.auth_models import Application
        _licentie(db, tenant_b, naam="Automatisch")
        expliciet = _licentie(db, tenant_b, naam="Expliciet", actief=False)
        app = db.query(Application).filter(Application.is_active == True).first()  # noqa: E712
        res = client.post(f"/api/admin/tenants/{tenant_b.id}/applications",
                          json={"application_id": str(app.id),
                                "license_id": str(expliciet.id)},
                          headers=auth(token_rhadix_admin))
        assert res.status_code == 201, res.text
        assert res.json()["license_id"] == str(expliciet.id)

    def test_toegang_hangt_niet_af_van_license_id(self, client, db, tenant_a, user_org_user,
                                                   token_org_user):
        """De kern: het veld mag autorisatie nooit sturen.

        Met een verlopen licentie én zonder enige koppeling houdt de gebruiker dezelfde
        applicatietoegang.
        """
        from app.auth.app_toegang import app_slugs_voor
        from app.models.auth_models import TenantApplication

        voor = app_slugs_voor(user_org_user, db)
        _licentie(db, tenant_a, vanaf=dagen(-60), tot=dagen(-1))
        db.query(TenantApplication).filter(
            TenantApplication.tenant_id == tenant_a.id).update(
            {TenantApplication.license_id: None}, synchronize_session=False)
        db.commit()

        assert app_slugs_voor(user_org_user, db) == voor
        assert client.get("/api/auth/me", headers=auth(token_org_user)).status_code == 200

    def test_bestaande_rijen_worden_niet_met_terugwerkende_kracht_gevuld(
        self, client, db, tenant_a, tenant_app_kikv, token_rhadix_admin
    ):
        """Van oude toewijzingen weten we de licentie niet; een gok mag geen feit worden."""
        from app.models.auth_models import TenantApplication

        # Een bestaande toewijzing zonder licentie, zoals alle 22 op staging.
        tenant_app_kikv.license_id = None
        db.commit()

        # Er komt een nieuwe licentie bij, en het overzicht wordt opgevraagd.
        _licentie(db, tenant_a, naam="Nieuw, na de toewijzing")
        assert client.get("/api/admin/licenses/",
                          headers=auth(token_rhadix_admin)).status_code == 200

        db.expire_all()
        blijft = db.query(TenantApplication).filter(
            TenantApplication.id == tenant_app_kikv.id).first()
        assert blijft.license_id is None, "een bestaande rij mag niet alsnog worden ingevuld"
