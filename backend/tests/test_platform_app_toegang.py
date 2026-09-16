"""
test_platform_app_toegang.py — applicatietoewijzing en navigatie vanaf het Platform.

Het Platform (Datavalidatie) is de centrale identity provider. Het bepaalt zelf geen
toegang tot de resource-apps: het geeft via `/api/auth/me` de `assigned_app_slugs`
door, en de portal hoort daarop te bepalen welke applicaties beschikbaar zijn. De
resource-apps handhaven vervolgens zelf op de `apps`-claim in het token
(APP_ACCESS_ENFORCE=on).

Deze tests dekken de Platform-kant van die keten: klopt de claim die de portal
krijgt, voor elk van de scenario's? Wat de portal er visueel mee doet is
frontend-gedrag en valt buiten deze suite — zie de rapportage bij deze wijziging.

Scenario's uit de opdracht en waar ze thuishoren:

  1. alleen datavalidatie -> Datavalidatie beschikbaar          → hier
  2. dezelfde gebruiker -> ds/crm/uitvraag niet beschikbaar     → hier (als claim-data)
  3. niet-toegewezen apps niet aanklikbaar                      → frontend (AppPortal.jsx)
  4. directe URL naar niet-toegewezen app -> 403                → resource-apps
                                                                  (test_app_access.py aldaar)
  5. vanuit 403 terug naar Platform zonder herlogin             → frontend (resource-apps)
  6. geldige toewijzing -> app normaal te openen                → hier
  7. PLATFORM_ADMIN behoudt toegang                             → hier (rol RHADIX_ADMIN)
"""
import uuid

from app.models.auth_models import (
    Application,
    TenantApplication,
    UserApplication,
    UserRole,
)

# Slugs van de resource-apps, exact zoals elke app die zelf vastlegt in
# auth/app_access.py. Let op de asymmetrie: alleen CRM heeft een 'rhadix-'-voorvoegsel.
SLUG_DV = "datavalidatie"
SLUG_DS = "datastation"
SLUG_CRM = "rhadix-crm"
SLUG_UV = "uitvraag"
RESOURCE_SLUGS = [SLUG_DS, SLUG_CRM, SLUG_UV]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def _app(db, slug, name=None):
    """Zorg dat de applicatie bestaat; geef hem terug."""
    a = db.query(Application).filter(Application.slug == slug).first()
    if not a:
        a = Application(id=uuid.uuid4(), slug=slug, name=name or slug, is_active=True)
        db.add(a)
        db.flush()
    return a


def _grant_tenant(db, tenant_id, slug, name=None, ook_aan_gebruikers=True):
    """Organisatiebrede toewijzing (TenantApplication).

    BIJGEWERKT bij bevinding 8/11: de claim is niet langer de vereniging maar de
    doorsnede van organisatie- en gebruikerstoewijzing. Een organisatietoewijzing maakt
    een applicatie BESCHIKBAAR; toegang ontstaat door de persoonlijke toewijzing.

    `ook_aan_gebruikers` bootst het standaardgedrag van de beheerroute na, zodat deze
    helper blijft betekenen wat hij hier altijd betekende: "de organisatie heeft deze
    applicatie en de gebruikers kunnen erin". Zet hem op False om alleen beschikbaar te
    maken.
    """
    from app.auth.app_toegang import wijs_toe_aan_bestaande_gebruikers

    a = _app(db, slug, name)
    ta = TenantApplication(id=uuid.uuid4(), tenant_id=tenant_id, application_id=a.id)
    db.add(ta)
    db.flush()
    if ook_aan_gebruikers:
        wijs_toe_aan_bestaande_gebruikers(db, ta)
    db.commit()
    return ta


def _grant_user(db, user_id, tenant_id, slug, name=None):
    """Persoonlijke toewijzing (UserApplication).

    Let op het datamodel: `UserApplication.tenant_application_id` is NOT NULL. Een
    persoonlijke toewijzing kan dus uitsluitend bestaan ónder een bestaande
    organisatietoewijzing — precies zoals de beheerroute in `routers/org.py` het doet.
    """
    ta = (
        db.query(TenantApplication)
        .join(Application, Application.id == TenantApplication.application_id)
        .filter(TenantApplication.tenant_id == tenant_id, Application.slug == slug)
        .first()
    )
    if ta is None:
        ta = _grant_tenant(db, tenant_id, slug, name)
    db.add(
        UserApplication(
            id=uuid.uuid4(),
            user_id=user_id,
            application_id=ta.application_id,
            tenant_application_id=ta.id,
        )
    )
    db.commit()
    return ta


def _slugs(client, token):
    r = client.get("/api/auth/me", headers=auth(token))
    assert r.status_code == 200, r.text
    return r.json()["assigned_app_slugs"]


class TestScenario1EnkelDatavalidatie:
    """Scenario 1 en 2 — de claim van een gebruiker met uitsluitend Datavalidatie."""

    def test_1_datavalidatie_zit_in_de_claim(self, client, db, tenant_a, token_org_user):
        _grant_tenant(db, tenant_a.id, SLUG_DV, "Rhadix Datavalidatie")
        assert SLUG_DV in _slugs(client, token_org_user)

    def test_2_resource_apps_zitten_niet_in_de_claim(self, client, db, tenant_a, token_org_user):
        """De portal heeft hiermee de gegevens om ds/crm/uitvraag als niet-beschikbaar te tonen."""
        _grant_tenant(db, tenant_a.id, SLUG_DV, "Rhadix Datavalidatie")
        # De resource-apps bestaan wél als applicatie, maar zijn niet toegewezen.
        for slug in RESOURCE_SLUGS:
            _app(db, slug)
        db.commit()

        claim = _slugs(client, token_org_user)
        assert SLUG_DV in claim
        for slug in RESOURCE_SLUGS:
            assert slug not in claim, f"{slug} hoort niet in de claim te zitten"

    def test_2b_claim_bevat_uitsluitend_het_toegewezene(self, client, db, tenant_a, token_org_user):
        """Geen impliciete extra's: precies één slug bij één toewijzing."""
        _grant_tenant(db, tenant_a.id, SLUG_DV, "Rhadix Datavalidatie")
        for slug in RESOURCE_SLUGS:
            _app(db, slug)
        db.commit()
        assert sorted(_slugs(client, token_org_user)) == [SLUG_DV]


class TestScenario6GeldigeToewijzing:
    """Scenario 6 — met een geldige toewijzing hoort de app gewoon te openen."""

    def test_6_organisatiebrede_toewijzing_geeft_de_slug(self, client, db, tenant_a, token_org_user):
        """Standaardgedrag: toewijzen aan de organisatie kent ook aan de gebruikers toe."""
        _grant_tenant(db, tenant_a.id, SLUG_DS, "Rhadix Datastation")
        assert SLUG_DS in _slugs(client, token_org_user)

    def test_6e_alleen_beschikbaar_maken_geeft_nog_geen_toegang(self, client, db, tenant_a, token_org_user):
        """Bevinding 8: beschikbaar zijn en toegang hebben zijn twee dingen."""
        _grant_tenant(db, tenant_a.id, SLUG_DS, "Rhadix Datastation", ook_aan_gebruikers=False)
        assert SLUG_DS not in _slugs(client, token_org_user)

    def test_6b_persoonlijke_toewijzing_geeft_de_slug(
        self, client, db, tenant_a, user_org_user, token_org_user
    ):
        """Een persoonlijke toewijzing (onder de organisatielicentie) levert de slug op."""
        _grant_user(db, user_org_user.id, tenant_a.id, SLUG_CRM, "Rhadix CRM")
        assert SLUG_CRM in _slugs(client, token_org_user)

    def test_6c_organisatie_en_persoonlijk_worden_samengevoegd(
        self, client, db, tenant_a, user_org_user, token_org_user
    ):
        _grant_tenant(db, tenant_a.id, SLUG_DV, "Rhadix Datavalidatie")
        _grant_user(db, user_org_user.id, tenant_a.id, SLUG_UV, "Rhadix Uitvraag")
        claim = _slugs(client, token_org_user)
        assert SLUG_DV in claim and SLUG_UV in claim
        assert SLUG_DS not in claim and SLUG_CRM not in claim

    def test_6d_toewijzing_van_andere_organisatie_lekt_niet(
        self, client, db, tenant_b, token_org_user
    ):
        """Een toewijzing aan tenant B mag niet in de claim van tenant A opduiken."""
        _grant_tenant(db, tenant_b.id, SLUG_DS, "Rhadix Datastation")
        assert SLUG_DS not in _slugs(client, token_org_user)


class TestScenario7PlatformAdmin:
    """Scenario 7 — de platformbeheerder (rol RHADIX_ADMIN) behoudt toegang.

    Conform het vastgelegde model: voor deze rol vervangt de issuer de claim door
    alle ACTIEVE applicaties, ongeacht wat er is toegewezen. De resource-apps kennen
    zelf geen rol-bypass; de beheerder komt binnen via de claim.
    """

    def test_7_admin_krijgt_alle_actieve_apps_zonder_toewijzing(
        self, client, db, token_rhadix_admin
    ):
        for slug in [SLUG_DV] + RESOURCE_SLUGS:
            _app(db, slug)
        db.commit()

        claim = _slugs(client, token_rhadix_admin)
        for slug in [SLUG_DV] + RESOURCE_SLUGS:
            assert slug in claim, f"{slug} hoort in de claim van een RHADIX_ADMIN te zitten"

    def test_7b_admin_krijgt_geen_inactieve_apps(self, client, db, token_rhadix_admin):
        """Alleen actieve applicaties; een uitgezette app blijft buiten de claim."""
        a = _app(db, "uitgezette-app", "Uitgezette App")
        a.is_active = False
        db.commit()
        assert "uitgezette-app" not in _slugs(client, token_rhadix_admin)

    def test_7c_gewone_gebruiker_krijgt_geen_admin_behandeling(
        self, client, db, user_org_user, token_org_user
    ):
        """Tegenproef: zonder toewijzing blijft de claim leeg, ongeacht bestaande apps."""
        assert user_org_user.role != UserRole.RHADIX_ADMIN
        for slug in [SLUG_DV] + RESOURCE_SLUGS:
            _app(db, slug)
        db.commit()
        assert _slugs(client, token_org_user) == []
