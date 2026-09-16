"""
test_applicatie_naamgeving.py — de weergavenamen van de product-applicaties.

Bevinding 5 uit het bevindingenregister: alle applicaties heetten 'Rhadix …' behalve
'Reconciliation Engine'. Dat is een weergavenaam en verder niets — de SLUG is waarop de
resource-apps de apps-claim beoordelen. Deze suite legt beide kanten vast: de naamgeving
is consistent, én de slugs blijven onaangeroerd.
"""
import uuid

import pytest

from app.main import (
    NAAMCORRECTIES,
    PRODUCT_APPS,
    corrigeer_applicatienamen,
)
from app.models.auth_models import Application

VOORVOEGSEL = "Rhadix "

# De slugs zoals elke resource-app die zelf vastlegt in auth/app_access.py. Alleen CRM
# heeft een 'rhadix-'-voorvoegsel; dat is geen afleidbare conventie en moet zo blijven.
VERWACHTE_SLUGS = {
    "datavalidatie",
    "uitvraag",
    "datastation",
    "rhadix-crm",
    "reconciliation-engine",
}


class TestNaamgeving:

    def test_alle_applicaties_dragen_de_rhadix_naam(self):
        afwijkend = [naam for _, naam, _, _ in PRODUCT_APPS if not naam.startswith(VOORVOEGSEL)]
        assert afwijkend == [], f"deze namen vallen buiten de Rhadix-naamgeving: {afwijkend}"

    def test_reconciliatie_heet_rhadix_reconciliatie(self):
        namen = {slug: naam for slug, naam, _, _ in PRODUCT_APPS}
        assert namen["reconciliation-engine"] == "Rhadix Reconciliatie"

    def test_namen_zijn_uniek(self):
        namen = [naam for _, naam, _, _ in PRODUCT_APPS]
        assert len(namen) == len(set(namen))


class TestSlugsBlijvenOngemoeid:
    """De hernoeming mag de sleutel van de autorisatie niet raken."""

    def test_slugs_zijn_ongewijzigd(self):
        assert {slug for slug, _, _, _ in PRODUCT_APPS} == VERWACHTE_SLUGS

    def test_naamcorrecties_wijzigen_alleen_namen(self):
        """Een correctie is per definitie een naamwissel; de sleutel staat er niet in."""
        for slug, (oud, nieuw) in NAAMCORRECTIES.items():
            assert slug in VERWACHTE_SLUGS
            assert oud != nieuw
            assert nieuw.startswith(VOORVOEGSEL)


class TestNaamcorrectie:
    """Bestaande omgevingen: de seed maakt alleen ontbrekende rijen aan.

    Zonder correctie zou de oude naam in elke bestaande database blijven staan, want
    'reconciliation-engine' bestaat daar al.
    """

    @pytest.fixture()
    def app_rij(self, db):
        rij = db.query(Application).filter(Application.slug == "reconciliation-engine").first()
        if rij is None:
            rij = Application(id=uuid.uuid4(), slug="reconciliation-engine",
                              name="Reconciliation Engine", is_active=True, sort_order=14)
            db.add(rij)
        else:
            rij.name = "Reconciliation Engine"
        db.commit()
        return rij

    def test_hernoemt_de_oude_naam(self, db, app_rij):
        assert corrigeer_applicatienamen(db) == ["reconciliation-engine"]
        db.refresh(app_rij)
        assert app_rij.name == "Rhadix Reconciliatie"

    def test_laat_slug_en_status_ongemoeid(self, db, app_rij):
        corrigeer_applicatienamen(db)
        db.refresh(app_rij)
        assert app_rij.slug == "reconciliation-engine"
        assert app_rij.is_active is True

    def test_is_idempotent(self, db, app_rij):
        corrigeer_applicatienamen(db)
        assert corrigeer_applicatienamen(db) == []
        db.refresh(app_rij)
        assert app_rij.name == "Rhadix Reconciliatie"

    def test_respecteert_een_bewuste_hernoeming(self, db, app_rij):
        """Heeft een beheerder de naam zelf aangepast, dan blijft die staan."""
        app_rij.name = "Reconciliatie (eigen naam)"
        db.commit()

        assert corrigeer_applicatienamen(db) == []
        db.refresh(app_rij)
        assert app_rij.name == "Reconciliatie (eigen naam)"
