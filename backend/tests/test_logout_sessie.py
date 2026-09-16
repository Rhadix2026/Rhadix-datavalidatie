"""
test_logout_sessie.py — uitloggen beëindigt de volledige Rhadix-sessie.

Achtergrond (bevindingen 9 en 10 uit het bevindingenregister):

  9.  Uitloggen vanuit Uitvraag of CRM laat de gebruiker achter op de applicatie-URL
      in plaats van op het centrale Platform.
  10. Na uitloggen geeft browser-terug, verversen of de URL opnieuw openen weer
      toegang: het centrale SSO-cookie bleef staan.

Beide komen uit dezelfde oorzaak: uitloggen was uitsluitend een handeling in de
frontend. Het `rhadix_sso`-cookie op `.rhadix.nl` — dat de resource-apps als
volwaardig bewijs van identiteit accepteren — werd nooit ongeldig gemaakt.

Datavalidatie is de uitgever van dat cookie en daarmee de enige plek die het kan
intrekken. Deze suite legt het contract van die centrale uitgang vast:

  * POST /api/auth/logout — programmatisch; wist het cookie, is idempotent.
  * GET  /api/auth/logout — navigeerbaar vanuit elke applicatie; wist het cookie
    en stuurt door naar het Platform.

De vier frontends gebruiken de GET-variant. Daarmee is er één implementatie van
uitloggen in plaats van vier, en lossen beide bevindingen in één keer op.
"""
import os

import pytest

# Naam zoals login hem zet; per omgeving instelbaar via SSO_COOKIE_NAME.
COOKIE = os.getenv("SSO_COOKIE_NAME", "rhadix_sso")


def _set_cookie_headers(res):
    """Alle Set-Cookie-headers uit een response (httpx houdt er meerdere apart)."""
    return res.headers.get_list("set-cookie")


def _wist_cookie(res, naam=COOKIE):
    """Bevat de response een Set-Cookie die `naam` intrekt?

    Een cookie wordt ingetrokken door hem opnieuw te zetten met een lege waarde en
    een vervaldatum in het verleden (of Max-Age=0). Beide vormen accepteren we.
    """
    for h in _set_cookie_headers(res):
        if not h.startswith(f"{naam}="):
            continue
        laag = h.lower()
        if "max-age=0" in laag or "expires=thu, 01 jan 1970" in laag:
            return True
        # Lege waarde met een expires in het verleden telt ook.
        if h.startswith(f"{naam}=;") or h.startswith(f'{naam}="";'):
            return True
    return False


# ── POST /auth/logout — programmatisch uitloggen ────────────────────────────

class TestPostLogout:

    def test_wist_het_sso_cookie(self, client, token_org_user):
        """De kern van bevinding 10: uitloggen moet het centrale cookie intrekken."""
        res = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token_org_user}"})
        assert res.status_code == 204, res.text
        assert _wist_cookie(res), (
            "logout trekt het SSO-cookie niet in; "
            f"Set-Cookie-headers: {_set_cookie_headers(res)!r}"
        )

    def test_werkt_met_alleen_het_cookie(self, client, token_org_user):
        """Uitloggen moet ook lukken als de frontend geen token in het geheugen heeft."""
        res = client.post("/api/auth/logout", cookies={COOKIE: token_org_user})
        assert res.status_code == 204, res.text
        assert _wist_cookie(res)

    def test_is_idempotent_zonder_sessie(self, client):
        """Twee keer uitloggen, of uitloggen na een verlopen sessie, mag niet stuklopen."""
        res = client.post("/api/auth/logout")
        assert res.status_code == 204, res.text
        assert _wist_cookie(res)


# ── GET /auth/logout — de centrale uitgang voor alle vier de applicaties ────

class TestGetLogout:

    def test_stuurt_door_naar_het_platform(self, client, token_org_user, monkeypatch):
        """Bevinding 9: na uitloggen hoort de gebruiker op het Platform te staan."""
        monkeypatch.setenv("PUBLIC_BASE_URL", "https://app-staging.rhadix.nl")
        res = client.get("/api/auth/logout",
                         headers={"Authorization": f"Bearer {token_org_user}"},
                         follow_redirects=False)
        assert res.status_code in (302, 303), res.text
        assert res.headers["location"] == "https://app-staging.rhadix.nl/"

    def test_wist_het_cookie(self, client, token_org_user):
        res = client.get("/api/auth/logout",
                         cookies={COOKIE: token_org_user},
                         follow_redirects=False)
        assert res.status_code in (302, 303)
        assert _wist_cookie(res)

    def test_werkt_zonder_sessie(self, client):
        """Een gebruiker die al uitgelogd is, hoort gewoon op het Platform te belanden."""
        res = client.get("/api/auth/logout", follow_redirects=False)
        assert res.status_code in (302, 303), res.text
        assert _wist_cookie(res)

    def test_negeert_een_meegegeven_doel(self, client, monkeypatch):
        """Geen open redirect: het doel komt uit de configuratie, niet uit de URL."""
        monkeypatch.setenv("PUBLIC_BASE_URL", "https://app-staging.rhadix.nl")
        res = client.get("/api/auth/logout?next=https://kwaadaardig.example",
                         follow_redirects=False)
        assert res.headers["location"] == "https://app-staging.rhadix.nl/"


# ── Het gedrag dat de gebruiker merkt ───────────────────────────────────────

class TestSessieIsEchtBeeindigd:
    """Browser-terug, verversen, nieuw tabblad en directe URL na uitloggen.

    Al die gevallen komen op hetzelfde neer: de browser doet opnieuw een verzoek
    en stuurt daarbij zijn cookies mee. Slaagt dat verzoek, dan is de gebruiker
    weer binnen. De test bootst dat na met de cookiejar van de testclient: die
    verwerkt Set-Cookie precies zoals een browser dat doet.
    """

    def _login_via_cookie(self, client, token):
        """Zet het cookie in de jar zoals een browser dat na login zou doen.

        Het domein is bewust 'testserver.local': `http.cookiejar` plakt '.local'
        achter een hostnaam zonder punt, en alleen met die schrijfwijze gedraagt de
        jar zich als een echte browser — het cookie gaat mee én een intrekking
        vanuit de server komt aan.
        """
        client.cookies.set(COOKIE, token, domain="testserver.local", path="/")

    def test_voor_uitloggen_geeft_het_cookie_toegang(self, client, token_org_user, user_org_user):
        """Vertrekpunt: met het cookie komt de gebruiker binnen zonder opnieuw in te loggen."""
        self._login_via_cookie(client, token_org_user)
        res = client.get("/api/auth/me")
        assert res.status_code == 200, res.text
        assert res.json()["email"] == user_org_user.email

    def test_na_uitloggen_geeft_het_cookie_geen_toegang_meer(self, client, token_org_user):
        """Bevinding 10 in één test: na uitloggen is er geen bruikbare sessie meer.

        Dit dekt browser-terug, verversen, een nieuw tabblad én het opnieuw openen
        van de URL: geen van die handelingen levert nog een geldig cookie op.
        """
        self._login_via_cookie(client, token_org_user)
        assert client.get("/api/auth/me").status_code == 200

        uit = client.get("/api/auth/logout", follow_redirects=False)
        assert uit.status_code in (302, 303), uit.text

        # De cookiejar heeft de intrekking verwerkt — net als een browser.
        assert COOKIE not in client.cookies, (
            f"cookie staat er nog: {dict(client.cookies)!r}"
        )
        opnieuw = client.get("/api/auth/me")
        assert opnieuw.status_code == 401, (
            "na uitloggen geeft het cookie nog steeds toegang — "
            f"status {opnieuw.status_code}"
        )

    def test_opnieuw_inloggen_werkt_daarna_gewoon(self, client, db, tenant_a):
        """De normale SSO-login moet na uitloggen ongewijzigd werken."""
        import uuid as _uuid
        from app.auth.security import hash_password
        from app.models.auth_models import User, UserRole

        wachtwoord = "EenVoldoendeLangWachtwoord1!"
        gebruiker = User(
            id=_uuid.uuid4(), tenant_id=tenant_a.id,
            email="uitlogtest@example.org", full_name="Uitlog Test",
            password_hash=hash_password(wachtwoord),
            role=UserRole.ORG_USER, is_active=True,
        )
        db.add(gebruiker); db.commit()

        client.get("/api/auth/logout", follow_redirects=False)
        res = client.post("/api/auth/login",
                          json={"email": "uitlogtest@example.org", "password": wachtwoord})
        assert res.status_code == 200, res.text
        assert res.json()["access_token"]


# ── Wat niet mag veranderen ─────────────────────────────────────────────────

class TestGeenNevenschade:
    """De autorisatiekant blijft ongemoeid: apps-claim, toewijzingen, /auth/me."""

    def test_me_zonder_sessie_blijft_401(self, client):
        assert client.get("/api/auth/me").status_code == 401

    def test_me_met_bearer_blijft_werken(self, client, token_org_user):
        res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_org_user}"})
        assert res.status_code == 200

    def test_me_met_cookie_blijft_werken(self, client, token_org_user):
        res = client.get("/api/auth/me", cookies={COOKIE: token_org_user})
        assert res.status_code == 200

    def test_claim_blijft_uit_de_toewijzingen_komen(self, client, token_org_user, db, tenant_a):
        """Uitloggen raakt de apps-claim niet: dezelfde bron, dezelfde uitkomst."""
        import uuid as _uuid
        from app.models.auth_models import Application, TenantApplication

        app_rij = db.query(Application).filter(Application.slug == "datavalidatie").first()
        if app_rij is None:
            app_rij = Application(id=_uuid.uuid4(), slug="datavalidatie",
                                  name="Rhadix Datavalidatie", is_active=True)
            db.add(app_rij); db.flush()
        ta = TenantApplication(id=_uuid.uuid4(), tenant_id=tenant_a.id,
                               application_id=app_rij.id)
        db.add(ta)
        db.flush()
        # Sinds bevinding 8/11 is de claim de doorsnede: de organisatietoewijzing maakt
        # de applicatie beschikbaar, de persoonlijke toewijzing geeft toegang.
        from app.auth.app_toegang import wijs_toe_aan_bestaande_gebruikers
        wijs_toe_aan_bestaande_gebruikers(db, ta)
        db.commit()

        res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_org_user}"})
        assert res.status_code == 200
        assert "datavalidatie" in res.json()["assigned_app_slugs"]
