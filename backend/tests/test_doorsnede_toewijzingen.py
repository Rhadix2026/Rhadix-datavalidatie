"""
test_doorsnede_toewijzingen.py — bevinding 8 en 11: persoonlijk beslist, binnen de organisatie.

De apps-claim was de VERENIGING van organisatie- en gebruikerstoewijzingen. Omdat een
persoonlijke toewijzing per datamodel altijd onder een organisatietoewijzing hangt, was
die vereniging altijd gelijk aan de organisatietoewijzing — en had persoonlijk intrekken
geen effect (bevinding 8). Vanaf de organisatiekant bekeken is dat bevinding 11.

Het model nu:

    TenantApplication  bepaalt WELKE applicaties de organisatie beschikbaar heeft
    UserApplication    bepaalt tot welke daarvan een GEBRUIKER toegang heeft
    claim              = de doorsnede

Bij het toewijzen van een applicatie aan een organisatie krijgen de huidige gebruikers
hem standaard ook; een nieuwe gebruiker krijgt standaard de applicaties van zijn
organisatie. Daarna kan er per gebruiker worden ingetrokken, en dat heeft effect.
"""
import uuid

import pytest

from app.auth.app_toegang import app_slugs_voor, heeft_toegang
from app.models.auth_models import (
    Application,
    TenantApplication,
    User,
    UserApplication,
    UserRole,
)


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def _app(db, slug, naam=None, actief=True):
    a = db.query(Application).filter(Application.slug == slug).first()
    if not a:
        a = Application(id=uuid.uuid4(), slug=slug, name=naam or slug, is_active=actief)
        db.add(a); db.flush()
    else:
        a.is_active = actief
    return a


def _org_toewijzing(db, tenant_id, slug):
    a = _app(db, slug)
    ta = db.query(TenantApplication).filter(
        TenantApplication.tenant_id == tenant_id,
        TenantApplication.application_id == a.id).first()
    if not ta:
        ta = TenantApplication(id=uuid.uuid4(), tenant_id=tenant_id, application_id=a.id)
        db.add(ta); db.flush()
    db.commit()
    return ta


def _persoonlijk(db, user, slug):
    ta = _org_toewijzing(db, user.tenant_id, slug)
    db.add(UserApplication(id=uuid.uuid4(), user_id=user.id,
                           application_id=ta.application_id,
                           tenant_application_id=ta.id))
    db.commit()
    return ta


def _claim(client, token):
    r = client.get("/api/auth/me", headers=auth(token))
    assert r.status_code == 200, r.text
    return set(r.json()["assigned_app_slugs"])


# ── De regel zelf ───────────────────────────────────────────────────────────

class TestClaimIsDeDoorsnede:

    def test_organisatie_zonder_persoonlijk_geeft_geen_toegang(self, client, db, tenant_a, token_org_user):
        """De kern van bevinding 8: beschikbaar is niet hetzelfde als toegang."""
        _org_toewijzing(db, tenant_a.id, "datastation")
        assert "datastation" not in _claim(client, token_org_user)

    def test_persoonlijk_binnen_de_organisatie_geeft_toegang(self, client, db, tenant_a,
                                                             user_org_user, token_org_user):
        _persoonlijk(db, user_org_user, "datastation")
        assert "datastation" in _claim(client, token_org_user)

    def test_persoonlijk_buiten_de_organisatie_geeft_nooit_toegang(self, client, db, tenant_a,
                                                                   user_org_user, token_org_user):
        """Vangnet tegen datadrift: een persoonlijke rij zonder organisatietoewijzing telt niet."""
        ta = _persoonlijk(db, user_org_user, "uitvraag")
        assert "uitvraag" in _claim(client, token_org_user)

        # Haal alleen de organisatietoewijzing weg, laat de persoonlijke rij staan.
        db.query(UserApplication).filter(
            UserApplication.user_id == user_org_user.id,
            UserApplication.application_id == ta.application_id,
        ).update({"tenant_application_id": ta.id})
        db.query(TenantApplication).filter(TenantApplication.id == ta.id).delete()
        db.commit()

        assert "uitvraag" not in _claim(client, token_org_user)

    def test_inactieve_applicatie_valt_buiten_de_claim(self, client, db, tenant_a,
                                                       user_org_user, token_org_user):
        _persoonlijk(db, user_org_user, "tijdelijk-uit")
        assert "tijdelijk-uit" in _claim(client, token_org_user)
        _app(db, "tijdelijk-uit", actief=False)
        db.commit()
        assert "tijdelijk-uit" not in _claim(client, token_org_user)

    def test_login_en_me_leveren_dezelfde_claim(self, client, db, tenant_a, user_org_user, token_org_user):
        from jose import jwt
        _persoonlijk(db, user_org_user, "datavalidatie")
        res = client.post("/api/auth/login",
                          json={"email": user_org_user.email, "password": "Correct-Password-123!"})
        assert res.status_code == 200, res.text
        uit_token = set(jwt.get_unverified_claims(res.json()["access_token"])["apps"])
        assert uit_token == _claim(client, token_org_user)


class TestRhadixAdminOngewijzigd:
    """De vastgelegde baseline: de platformbeheerder krijgt alle actieve applicaties."""

    def test_admin_krijgt_alles_zonder_enige_toewijzing(self, client, db, token_rhadix_admin):
        for slug in ("datavalidatie", "uitvraag", "datastation", "rhadix-crm"):
            _app(db, slug)
        db.commit()
        claim = _claim(client, token_rhadix_admin)
        for slug in ("datavalidatie", "uitvraag", "datastation", "rhadix-crm"):
            assert slug in claim

    def test_admin_krijgt_geen_inactieve_applicaties(self, client, db, token_rhadix_admin):
        _app(db, "uitgezet", actief=False)
        db.commit()
        assert "uitgezet" not in _claim(client, token_rhadix_admin)


# ── Intrekken ───────────────────────────────────────────────────────────────

class TestPersoonlijkIntrekken:
    """Bevinding 8: intrekken raakt alleen deze gebruiker en werkt écht."""

    def test_intrekken_verwijdert_de_applicatie_uit_de_claim(self, client, db, tenant_a,
                                                             user_org_user, token_org_user,
                                                             token_org_admin):
        _persoonlijk(db, user_org_user, "datastation")
        assert "datastation" in _claim(client, token_org_user)

        app_id = db.query(Application).filter(Application.slug == "datastation").first().id
        res = client.delete(f"/api/org/users/{user_org_user.id}/apps/{app_id}",
                            headers=auth(token_org_admin))
        assert res.status_code == 204, res.text
        assert "datastation" not in _claim(client, token_org_user)

    def test_de_organisatie_houdt_de_applicatie(self, client, db, tenant_a,
                                                user_org_user, token_org_user, token_org_admin):
        _persoonlijk(db, user_org_user, "datastation")
        app_id = db.query(Application).filter(Application.slug == "datastation").first().id
        client.delete(f"/api/org/users/{user_org_user.id}/apps/{app_id}", headers=auth(token_org_admin))

        res = client.get("/api/org/me/apps", headers=auth(token_org_admin))
        assert res.status_code == 200, res.text
        assert any(r.get("application_slug") == "datastation" for r in res.json())

    def test_een_andere_gebruiker_wordt_niet_geraakt(self, client, db, tenant_a,
                                                     user_org_user, user_org_admin,
                                                     token_org_user, token_org_admin):
        _persoonlijk(db, user_org_user, "datastation")
        _persoonlijk(db, user_org_admin, "datastation")
        app_id = db.query(Application).filter(Application.slug == "datastation").first().id
        client.delete(f"/api/org/users/{user_org_user.id}/apps/{app_id}", headers=auth(token_org_admin))

        assert "datastation" not in _claim(client, token_org_user)
        assert "datastation" in _claim(client, token_org_admin)

    def test_opnieuw_inloggen_herstelt_de_ingetrokken_toegang_niet(self, client, db, tenant_a,
                                                                   user_org_user, token_org_admin):
        """Geen automatische synchronisatie mag een bewuste intrekking ongedaan maken."""
        from jose import jwt
        _persoonlijk(db, user_org_user, "datastation")
        app_id = db.query(Application).filter(Application.slug == "datastation").first().id
        client.delete(f"/api/org/users/{user_org_user.id}/apps/{app_id}", headers=auth(token_org_admin))

        res = client.post("/api/auth/login",
                          json={"email": user_org_user.email, "password": "Correct-Password-123!"})
        assert res.status_code == 200, res.text
        apps = set(jwt.get_unverified_claims(res.json()["access_token"])["apps"])
        assert "datastation" not in apps


class TestOrganisatieIntrekken:
    """Bevinding 11: intrekken op organisatieniveau raakt iedereen in die organisatie."""

    def test_cascade_verwijdert_de_persoonlijke_toewijzingen(self, client, db, tenant_a,
                                                             user_org_user, user_org_admin,
                                                             token_org_user, token_org_admin,
                                                             token_rhadix_admin):
        ta = _persoonlijk(db, user_org_user, "uitvraag")
        _persoonlijk(db, user_org_admin, "uitvraag")
        assert "uitvraag" in _claim(client, token_org_user)

        res = client.delete(f"/api/admin/tenants/{tenant_a.id}/applications/{ta.application_id}",
                            headers=auth(token_rhadix_admin))
        assert res.status_code == 204, res.text

        assert "uitvraag" not in _claim(client, token_org_user)
        assert "uitvraag" not in _claim(client, token_org_admin)
        assert db.query(UserApplication).filter(
            UserApplication.application_id == ta.application_id,
            UserApplication.user_id.in_([user_org_user.id, user_org_admin.id]),
        ).count() == 0

    def test_een_andere_organisatie_wordt_niet_geraakt(self, client, db, tenant_a, tenant_b,
                                                       user_org_user, user_tenant_b,
                                                       token_org_user, token_tenant_b,
                                                       token_rhadix_admin):
        ta_a = _persoonlijk(db, user_org_user, "uitvraag")
        _persoonlijk(db, user_tenant_b, "uitvraag")

        client.delete(f"/api/admin/tenants/{tenant_a.id}/applications/{ta_a.application_id}",
                      headers=auth(token_rhadix_admin))

        assert "uitvraag" not in _claim(client, token_org_user)
        assert "uitvraag" in _claim(client, token_tenant_b)


# ── Standaardgedrag ─────────────────────────────────────────────────────────

class TestStandaardgedrag:
    """Variant 2: beschikbaar maken kent standaard ook toe, zodat er niets verandert
    aan wat beheerders gewend zijn — maar intrekken werkt nu wél."""

    def test_nieuwe_gebruiker_krijgt_de_applicaties_van_de_organisatie(self, client, db, tenant_a,
                                                                       token_org_admin):
        _org_toewijzing(db, tenant_a.id, "datavalidatie")
        _org_toewijzing(db, tenant_a.id, "uitvraag")

        res = client.post("/api/org/users", json={
            "email": "verse@example.org", "full_name": "Verse Gebruiker",
            "password": "EenVoldoendeLangWachtwoord1!", "role": "ORG_USER",
        }, headers=auth(token_org_admin))
        assert res.status_code == 201, res.text

        nieuw = db.query(User).filter(User.email == "verse@example.org").first()
        assert set(app_slugs_voor(nieuw, db)) == {"datavalidatie", "uitvraag"}

    def test_beheerder_kan_hiervan_afwijken(self, client, db, tenant_a, token_org_admin):
        _org_toewijzing(db, tenant_a.id, "datavalidatie")
        res = client.post("/api/org/users", json={
            "email": "zonder@example.org", "full_name": "Zonder Apps",
            "password": "EenVoldoendeLangWachtwoord1!", "role": "ORG_USER",
            "apps_toewijzen": False,
        }, headers=auth(token_org_admin))
        assert res.status_code == 201, res.text

        nieuw = db.query(User).filter(User.email == "zonder@example.org").first()
        assert app_slugs_voor(nieuw, db) == []

    def test_organisatietoewijzing_kent_ook_aan_bestaande_gebruikers_toe(self, client, db, tenant_a,
                                                                        user_org_user, token_org_user,
                                                                        token_rhadix_admin):
        a = _app(db, "datastation"); db.commit()
        res = client.post(f"/api/admin/tenants/{tenant_a.id}/applications",
                          json={"application_id": str(a.id), "license_id": None},
                          headers=auth(token_rhadix_admin))
        assert res.status_code == 201, res.text
        assert res.json()["toegewezen_aan_gebruikers"] >= 1
        assert "datastation" in _claim(client, token_org_user)

    def test_beheerder_kan_alleen_beschikbaar_maken(self, client, db, tenant_a,
                                                    user_org_user, token_org_user, token_rhadix_admin):
        a = _app(db, "datastation"); db.commit()
        res = client.post(f"/api/admin/tenants/{tenant_a.id}/applications",
                          json={"application_id": str(a.id), "license_id": None,
                                "toewijzen_aan_bestaande_gebruikers": False},
                          headers=auth(token_rhadix_admin))
        assert res.status_code == 201, res.text
        assert res.json()["toegewezen_aan_gebruikers"] == 0
        assert "datastation" not in _claim(client, token_org_user)


# ── De uploadpoort volgt dezelfde regel ─────────────────────────────────────

class TestUploadpoortVolgtDeClaim:

    def test_zonder_persoonlijke_toewijzing_geen_toegang(self, db, tenant_a, user_org_user):
        _org_toewijzing(db, tenant_a.id, "datavalidatie")
        assert heeft_toegang(user_org_user, ["datavalidatie"], db) is False

    def test_met_persoonlijke_toewijzing_wel(self, db, tenant_a, user_org_user):
        _persoonlijk(db, user_org_user, "datavalidatie")
        assert heeft_toegang(user_org_user, ["datavalidatie"], db) is True

    def test_rhadix_admin_altijd(self, db, user_rhadix_admin):
        assert heeft_toegang(user_rhadix_admin, ["datavalidatie"], db) is True


# ── De migratie ─────────────────────────────────────────────────────────────

class TestMigratie:
    """De effectieve claim moet vóór en ná identiek zijn."""

    def test_materialiseert_de_huidige_toegang(self, db, tenant_a, user_org_user):
        from app.scripts.migratie_persoonlijke_toewijzingen import (
            bepaal_plan, claim_oud, claim_nieuw, voer_uit,
        )
        _org_toewijzing(db, tenant_a.id, "datavalidatie")
        _org_toewijzing(db, tenant_a.id, "uitvraag")

        voor = claim_oud(db, user_org_user)
        assert voor == {"datavalidatie", "uitvraag"}
        assert claim_nieuw(db, user_org_user) == set()      # nog niets persoonlijk

        voer_uit(db, bepaal_plan(db))
        db.expire_all()
        assert claim_nieuw(db, db.query(User).get(user_org_user.id)) == voor

    def test_is_idempotent(self, db, tenant_a, user_org_user):
        from app.scripts.migratie_persoonlijke_toewijzingen import bepaal_plan, voer_uit
        _org_toewijzing(db, tenant_a.id, "datavalidatie")
        voer_uit(db, bepaal_plan(db))
        db.expire_all()
        assert voer_uit(db, bepaal_plan(db)) == 0

    def test_raakt_rhadix_admin_niet(self, db, tenant_a, user_rhadix_admin):
        from app.scripts.migratie_persoonlijke_toewijzingen import bepaal_plan
        _org_toewijzing(db, tenant_a.id, "datavalidatie")
        assert all(u.id != user_rhadix_admin.id for u, _ in bepaal_plan(db))

    def test_blijft_binnen_de_eigen_organisatie(self, db, tenant_a, tenant_b,
                                                user_org_user, user_tenant_b):
        from app.scripts.migratie_persoonlijke_toewijzingen import bepaal_plan, voer_uit
        _org_toewijzing(db, tenant_a.id, "datavalidatie")
        voer_uit(db, bepaal_plan(db))
        db.expire_all()
        assert app_slugs_voor(db.query(User).get(user_tenant_b.id), db) == []
