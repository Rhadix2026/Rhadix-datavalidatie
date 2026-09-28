"""
test_readiness_crm.py — De CRM-registratie van een rapportaanvraag.

Het CRM wordt hier nagebootst: elke aanroep wordt opgevangen en beantwoord
alsof het echte CRM antwoordt. Daarmee is te toetsen wat er precies gebeurt bij
een nieuw contact, een bestaand contact, een tweede check, en bij storingen —
zonder ook maar iets aan te raken.

De harde eis die overal doorheen loopt: **de CRM-koppeling mag de bezoeker
nooit zijn rapport kosten.**
"""
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import readiness_crm as crm
from app.services import readiness_limiet as limiet
from app.services.readiness_scoring import bereken

client = TestClient(app)
PAD = "/api/readiness/report"

GEMENGD = [2, 1, 0, 3, 3, 3, 1, 1, 1, 2, 2, 2, 0, 0, 3]


class NepAntwoord:
    def __init__(self, status_code=200, data=None, tekst=""):
        self.status_code = status_code
        self._data = data if data is not None else {}
        self.text = tekst or json.dumps(self._data)
        self.content = b"x"

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"status {self.status_code}")


class NepCRM:
    """Houdt bij wat er is aangeroepen en welke gegevens erin zijn gezet."""

    def __init__(self, contacten=None, organisaties=None, faal_op=None, login_faalt=False):
        self.contacten = list(contacten or [])
        self.organisaties = list(organisaties or [])
        self.faal_op = faal_op or set()
        self.login_faalt = login_faalt
        self.aanroepen = []
        self.activiteiten = []

    # ── de twee functies die readiness_crm gebruikt ──────────────────────────
    def post_login(self, url, json=None, timeout=None):
        self.aanroepen.append(("POST", "login"))
        if self.login_faalt:
            return NepAntwoord(401, {"detail": "nee"})
        # Token met een payload die een exp bevat; handtekening doet er niet toe.
        import base64
        payload = base64.urlsafe_b64encode(b'{"exp":99999999999}').decode().rstrip("=")
        return NepAntwoord(200, {"access_token": f"kop.{payload}.handtekening"})

    def request(self, methode, url, headers=None, timeout=None, params=None, json=None):
        pad = url.split("/api/crm")[-1].split("?")[0]
        self.aanroepen.append((methode, pad))
        if pad in self.faal_op:
            return NepAntwoord(500, {}, "kapot")

        if methode == "GET" and pad == "/contactpersonen":
            return NepAntwoord(200, self.contacten)
        if methode == "GET" and pad == "/organisaties":
            zoek = (params or {}).get("q", "").lower()
            return NepAntwoord(200, [o for o in self.organisaties
                                     if zoek in (o.get("naam") or "").lower()])
        if methode == "POST" and pad == "/organisaties":
            nieuw = {"id": f"org-{len(self.organisaties) + 1}", **json}
            self.organisaties.append(nieuw)
            return NepAntwoord(201, nieuw)
        if methode == "POST" and pad == "/contactpersonen":
            nieuw = {"id": f"cp-{len(self.contacten) + 1}", **json}
            self.contacten.append(nieuw)
            return NepAntwoord(201, nieuw)
        if methode == "POST" and pad == "/activiteiten":
            nieuw = {"id": f"act-{len(self.activiteiten) + 1}", **json}
            self.activiteiten.append(nieuw)
            return NepAntwoord(201, nieuw)
        return NepAntwoord(404, {})

    def paden(self):
        return [p for _, p in self.aanroepen]


@pytest.fixture
def nep(monkeypatch):
    for sleutel, waarde in [
        ("CRM_BASIS_URL", "https://crm-staging.test"),
        ("CRM_LOGIN_URL", "https://app-staging.test"),
        ("CRM_SERVICE_EMAIL", "service@rhadix.nl"),
        ("CRM_SERVICE_WACHTWOORD", "geheim"),
    ]:
        monkeypatch.setenv(sleutel, waarde)
    crm._token["waarde"] = None
    crm._token["geldig_tot"] = 0.0

    server = NepCRM()

    def maak(server):
        monkeypatch.setattr(crm.requests, "post", server.post_login)
        monkeypatch.setattr(crm.requests, "request", server.request)
    maak(server)
    server._opnieuw = maak
    return server


def uitslag():
    return bereken("data", GEMENGD)


# ── Instellingen ──────────────────────────────────────────────────────────────

def test_zonder_serviceaccount_slaat_de_koppeling_over(monkeypatch):
    for sleutel in ("CRM_BASIS_URL", "CRM_SERVICE_EMAIL", "CRM_SERVICE_WACHTWOORD"):
        monkeypatch.delenv(sleutel, raising=False)
    assert crm.ingeschakeld() is False
    assert crm.registreer(uitslag(), naam="Jan", organisatie="Zorg BV",
                          email="jan@voorbeeld.nl") is None


def test_lege_instelling_telt_als_niet_ingesteld(monkeypatch):
    monkeypatch.setenv("CRM_SERVICE_EMAIL", "   ")
    monkeypatch.setenv("CRM_SERVICE_WACHTWOORD", "geheim")
    monkeypatch.setenv("CRM_BASIS_URL", "https://crm.test")
    assert crm.ingeschakeld() is False


# ── Nieuw contact ─────────────────────────────────────────────────────────────

def test_nieuw_contact_en_nieuwe_organisatie(nep):
    act = crm.registreer(uitslag(), naam="Jan de Vries",
                         organisatie="Zorggroep Voorbeeld", email="jan@voorbeeld.nl")
    assert act is not None
    assert "/organisaties" in nep.paden() and "/contactpersonen" in nep.paden()

    org = nep.organisaties[0]
    assert org["naam"] == "Zorggroep Voorbeeld"
    cp = nep.contacten[0]
    assert cp["email"] == "jan@voorbeeld.nl"
    assert cp["naam"] == "Jan de Vries"
    assert cp["organisatie_id"] == org["id"]
    assert cp["bron_type"] == "Data Readiness Check"


def test_activiteit_bevat_de_afgesproken_gegevens(nep):
    crm.registreer(uitslag(), naam="Jan de Vries", organisatie="Zorggroep Voorbeeld",
                   email="jan@voorbeeld.nl",
                   campagne={"utm_source": "linkedin", "utm_campaign": "datagereedheid-2026-10"})
    a = nep.activiteiten[0]
    assert a["titel"] == "Data Readiness Check – rapport aangevraagd"
    assert a["soort"] == "notitie"
    assert a["datum"]
    assert a["contactpersoon_id"] and a["organisatie_id"]

    tekst = a["omschrijving"]
    for verwacht in ("Jan de Vries", "Zorggroep Voorbeeld", "jan@voorbeeld.nl",
                     "Totaalscore: 53 van 100", "In ontwikkeling",
                     "Data Readiness Check", "linkedin", "datagereedheid-2026-10"):
        assert verwacht in tekst
    for naam, score in [("Databeschikbaarheid", 33), ("Datakwaliteit", 100),
                        ("Governance & eigenaarschap", 67)]:
        assert f"{naam}: {score}" in tekst


def test_de_vijftien_antwoorden_gaan_niet_mee(nep):
    """Afgesproken: de losse antwoorden worden niet vastgelegd."""
    crm.registreer(uitslag(), naam="Jan", organisatie="Zorg BV", email="jan@voorbeeld.nl")
    tekst = nep.activiteiten[0]["omschrijving"]
    assert "Heeft uw organisatie inzicht" not in tekst
    assert "Aantoonbaar geregeld" not in tekst
    assert "worden niet vastgelegd" in tekst


# ── Bestaand contact, geen duplicaten ─────────────────────────────────────────

def test_bestaand_contact_wordt_hergebruikt(nep):
    nep.contacten.append({"id": "cp-bestaand", "email": "Jan@Voorbeeld.NL", "naam": "J. de Vries"})
    nep.organisaties.append({"id": "org-bestaand", "naam": "Zorggroep Voorbeeld"})

    crm.registreer(uitslag(), naam="Jan de Vries", organisatie="Zorggroep Voorbeeld",
                   email="jan@voorbeeld.nl")

    assert nep.paden().count("/contactpersonen") == 1, "alleen opgehaald, niet aangemaakt"
    assert [m for m, p in nep.aanroepen if p == "/contactpersonen"] == ["GET"]
    assert [m for m, p in nep.aanroepen if p == "/organisaties"] == ["GET"]
    assert nep.activiteiten[0]["contactpersoon_id"] == "cp-bestaand"
    assert nep.activiteiten[0]["organisatie_id"] == "org-bestaand"


def test_e_mailadres_wordt_hoofdletterongevoelig_vergeleken(nep):
    nep.contacten.append({"id": "cp-1", "email": "  JAN@voorbeeld.nl  "})
    assert crm.zoek_contact("jan@Voorbeeld.NL")["id"] == "cp-1"


def test_organisatienaam_moet_exact_overeenkomen(nep):
    """Een deeltreffer van het CRM-zoekfilter is niet genoeg: 'Zorg' mag niet
    als 'Zorggroep Voorbeeld' worden gelezen."""
    nep.organisaties.append({"id": "org-1", "naam": "Zorggroep Voorbeeld"})
    assert crm.zoek_organisatie("Zorggroep Voorbeeld")["id"] == "org-1"
    assert crm.zoek_organisatie("Zorggroep") is None


def test_tweede_check_geeft_een_tweede_activiteit(nep):
    for _ in range(2):
        crm.registreer(uitslag(), naam="Jan de Vries", organisatie="Zorggroep Voorbeeld",
                       email="jan@voorbeeld.nl")
    assert len(nep.activiteiten) == 2, "elke check blijft als eigen interactie zichtbaar"
    assert len(nep.contacten) == 1, "geen duplicaat contact"
    assert len(nep.organisaties) == 1, "geen duplicaat organisatie"


# ── Het rapport zelf ──────────────────────────────────────────────────────────

def test_pdf_wordt_niet_geupload_want_het_crm_kent_geen_bijlagen(nep, caplog):
    import logging
    with caplog.at_level(logging.INFO, logger="rhadix.readiness.crm"):
        crm.registreer(uitslag(), naam="Jan", organisatie="Zorg BV",
                       email="jan@voorbeeld.nl", pdf=b"%PDF-1.4 rapport")
    assert not any("document" in p or "bijlage" in p for _, p in nep.aanroepen)
    assert "geen bijlagen ondersteunt" in caplog.text


# ── Storingen ─────────────────────────────────────────────────────────────────

def test_mislukte_login_werpt_niets(nep, monkeypatch):
    kapot = NepCRM(login_faalt=True)
    nep._opnieuw(kapot)
    assert crm.registreer(uitslag(), naam="Jan", organisatie="Zorg BV",
                          email="jan@voorbeeld.nl") is None


def test_mislukte_activiteit_wordt_gelogd_met_herstelgegevens(nep, caplog):
    import logging
    kapot = NepCRM(faal_op={"/activiteiten"})
    nep._opnieuw(kapot)
    with caplog.at_level(logging.ERROR, logger="rhadix.readiness.crm"):
        assert crm.registreer(uitslag(), naam="Jan", organisatie="Zorg BV",
                              email="jan@voorbeeld.nl") is None
    assert "jan@voorbeeld.nl" in caplog.text and "Zorg BV" in caplog.text
    assert "53" in caplog.text, "de score hoort erbij om het later te kunnen herstellen"


def test_onbereikbaar_crm_werpt_niets(nep, monkeypatch):
    def stuk(*a, **kw):
        raise ConnectionError("geen verbinding")
    monkeypatch.setattr(crm.requests, "request", stuk)
    assert crm.registreer(uitslag(), naam="Jan", organisatie="Zorg BV",
                          email="jan@voorbeeld.nl") is None


# ── Samenspel met de rapportaanvraag ──────────────────────────────────────────

@pytest.fixture(autouse=True)
def schone_limiet():
    limiet.wis_alles()
    yield
    limiet.wis_alles()


def _verzoek(**kw):
    basis = {"check": "data", "antwoorden": GEMENGD, "naam": "Jan de Vries",
             "organisatie": "Zorggroep Voorbeeld", "email": "jan@voorbeeld.nl"}
    basis.update(kw)
    return basis


def test_crm_storing_kost_de_bezoeker_zijn_rapport_niet(monkeypatch, nep):
    """De echte registreer() loopt, met een CRM dat er niet is. De router vangt
    hier niets af — readiness_crm hoort dat zelf te doen."""
    monkeypatch.setattr("app.routers.readiness.mail.verstuur_rapport", lambda *a, **k: True)
    monkeypatch.setattr("app.routers.readiness.mail.verstuur_signaal", lambda *a, **k: True)

    def stuk(*a, **kw):
        raise ConnectionError("CRM plat")
    monkeypatch.setattr(crm.requests, "request", stuk)
    monkeypatch.setattr(crm.requests, "post", stuk)

    r = client.post(PAD, json=_verzoek())
    assert r.status_code == 200
    assert r.json()["verzonden"] is True
    assert r.json()["totaal"] == 53


def test_campagnegegevens_komen_bij_het_crm_terecht(monkeypatch):
    monkeypatch.setattr("app.routers.readiness.mail.verstuur_rapport", lambda *a, **k: True)
    monkeypatch.setattr("app.routers.readiness.mail.verstuur_signaal", lambda *a, **k: True)
    gezien = {}

    def vang(uitslag, naam, organisatie, email, pdf=None, campagne=None):
        gezien.update({"campagne": campagne, "pdf": pdf, "email": email})
        return {"id": "act-1"}
    monkeypatch.setattr("app.routers.readiness.crm.registreer", vang)

    r = client.post(PAD, json=_verzoek(utm_source="linkedin", utm_medium="social",
                                       utm_campaign="datagereedheid-2026-10"))
    assert r.status_code == 200
    assert gezien["campagne"] == {"utm_source": "linkedin", "utm_medium": "social",
                                  "utm_campaign": "datagereedheid-2026-10"}
    assert gezien["pdf"][:5] == b"%PDF-", "dezelfde PDF als de aanvrager kreeg"


def test_zonder_campagne_gaat_er_een_lege_verzameling_mee(monkeypatch):
    monkeypatch.setattr("app.routers.readiness.mail.verstuur_rapport", lambda *a, **k: True)
    monkeypatch.setattr("app.routers.readiness.mail.verstuur_signaal", lambda *a, **k: True)
    gezien = {}
    monkeypatch.setattr("app.routers.readiness.crm.registreer",
                        lambda *a, **k: gezien.update(k) or {"id": "x"})
    client.post(PAD, json=_verzoek())
    assert gezien["campagne"] == {}


def test_utm_velden_zijn_optioneel_en_veranderen_de_uitslag_niet(monkeypatch):
    monkeypatch.setattr("app.routers.readiness.mail.verstuur_rapport", lambda *a, **k: True)
    monkeypatch.setattr("app.routers.readiness.mail.verstuur_signaal", lambda *a, **k: True)
    monkeypatch.setattr("app.routers.readiness.crm.registreer", lambda *a, **k: None)

    zonder = client.post(PAD, json=_verzoek()).json()
    limiet.wis_alles()
    met = client.post(PAD, json=_verzoek(utm_source="linkedin")).json()
    assert zonder["totaal"] == met["totaal"] == 53
    assert zonder["dimensies"] == met["dimensies"]
