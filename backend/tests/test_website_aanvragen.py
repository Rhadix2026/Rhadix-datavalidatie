"""
test_website_aanvragen.py — Eerst vastleggen, dan verwerken.

Getoetst wordt wat de structurele verbetering moet waarmaken:

* een aanvraag staat vast vóórdat er iets wordt verstuurd;
* een mislukte mail of een haperend CRM kost geen aanvraag, en de herhaaltaak
  maakt het later alsnog af;
* het CRM wordt niet dubbel bijgewerkt bij een nieuwe poging;
* een ontbrekend of ongeldig intern adres wordt gemeld en houdt de melding vast
  tot het adres er is;
* het antwoord aan de browser zegt wat er werkelijk gelukt is;
* de opslag kent alleen zijn eigen tabellen.

Mail en CRM worden steeds vervangen; er gaat niets de deur uit.
"""
import logging
import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import readiness_crm as crm
from app.services import readiness_limiet as limiet
from app.services.readiness_scoring import bereken
from app.website import instellingen, opslag, verwerking

from test_readiness_crm import NepCRM

client = TestClient(app)
RAPPORT = "/api/readiness/report"
CONTACT = "/api/contact"
ANTWOORDEN = [2, 1, 0, 3, 3, 3, 1, 1, 1, 2, 2, 2, 0, 0, 3]


def rapport_verzoek(**kw):
    basis = {"check": "data", "antwoorden": ANTWOORDEN, "naam": "Jan de Vries",
             "organisatie": "Zorggroep Voorbeeld", "email": "jan@voorbeeld.nl"}
    basis.update(kw)
    return basis


def contact_verzoek(**kw):
    basis = {"naam": "Jan de Vries", "email": "jan@voorbeeld.nl",
             "organisatie": "Zorggroep Voorbeeld", "bericht": "Graag een gesprek."}
    basis.update(kw)
    return basis


@pytest.fixture(autouse=True)
def schoon(website_mail):
    limiet.wis_alles()
    yield
    limiet.wis_alles()


class Post:
    """Vervangt de drie verzendpunten en houdt bij wat er langskwam."""

    def __init__(self, monkeypatch):
        self.rapport, self.signaal, self.contact, self.crm = [], [], [], []
        self.rapport_lukt = self.signaal_lukt = self.contact_lukt = True
        self.crm_lukt = True
        m = "app.website.verwerking"
        monkeypatch.setattr(f"{m}.readiness_mail.verstuur_rapport", self._rapport)
        monkeypatch.setattr(f"{m}.readiness_mail.verstuur_signaal", self._signaal)
        monkeypatch.setattr(f"{m}.contact_mail.verstuur", self._contact)
        monkeypatch.setattr(crm, "ingeschakeld", lambda: True)
        monkeypatch.setattr(crm, "zoek_activiteit", lambda aanvraag_id: next(
            (a for a in self.crm if a["aanvraag_id"] == aanvraag_id and a["bestaat"]), None))
        monkeypatch.setattr(crm, "registreer", self._crm)
        monkeypatch.setattr(crm, "registreer_bericht", self._crm)

    def _rapport(self, opzet, email, pdf):
        self.rapport.append(email)
        return self.rapport_lukt

    def _signaal(self, opzet, email, aanvraag_id=None):
        self.signaal.append(aanvraag_id)
        return self.signaal_lukt

    def _contact(self, aanvraag_id=None, **kw):
        self.contact.append(aanvraag_id)
        return self.contact_lukt

    def _crm(self, *a, aanvraag_id=None, **kw):
        # crm_lukt = "timeout": de activiteit bestaat wél, maar het antwoord
        # kwam niet aan. Precies het geval dat dubbel registreren uitlokt.
        bestaat = self.crm_lukt in (True, "timeout")
        self.crm.append({"aanvraag_id": aanvraag_id, "id": f"act-{len(self.crm) + 1}",
                         "bestaat": bestaat})
        return {"id": self.crm[-1]["id"]} if self.crm_lukt is True else None


@pytest.fixture
def post(monkeypatch):
    return Post(monkeypatch)


def stappen(aanvraag_id):
    _, rijen = opslag.haal(aanvraag_id)
    return {k: (v.status, v.pogingen) for k, v in rijen.items()}


def maak_verschuldigd(aanvraag_id=None):
    """Zet de geplande tijd van open stappen in het verleden, alsof het
    wachten voorbij is."""
    with opslag.sessie() as s:
        q = s.query(opslag.Stap)
        if aanvraag_id:
            q = q.filter(opslag.Stap.aanvraag_id == aanvraag_id)
        q.update({opslag.Stap.volgende_poging_op: opslag.nu() - timedelta(seconds=1)},
                 synchronize_session=False)


# ── Vastleggen vóór versturen ─────────────────────────────────────────────────

def test_rapport_wordt_vastgelegd_en_verwerkt(post):
    r = client.post(RAPPORT, json=rapport_verzoek())
    assert r.status_code == 200
    body = r.json()
    assert body["opgeslagen"] is True and body["rapport"] == "verzonden"
    assert body["verzonden"] is True
    assert stappen(body["aanvraag_id"]) == {
        "mail_bezoeker": ("gelukt", 1), "mail_intern": ("gelukt", 1), "crm": ("gelukt", 1)}
    aanvraag, _ = opslag.haal(body["aanvraag_id"])
    assert aanvraag.soort == "rapport" and aanvraag.check_soort == "data"
    assert aanvraag.gegevens["antwoorden"] == ANTWOORDEN, "nodig om de PDF opnieuw te maken"


def test_aanvraag_staat_vast_voordat_er_iets_wordt_verstuurd(post, monkeypatch):
    gezien = {}

    def rapport(opzet, email, pdf):
        with opslag.sessie() as s:
            gezien["aantal"] = s.query(opslag.Aanvraag).count()
        return True
    monkeypatch.setattr("app.website.verwerking.readiness_mail.verstuur_rapport", rapport)
    client.post(RAPPORT, json=rapport_verzoek())
    assert gezien["aantal"] == 1


def test_mislukte_rapportmail_kost_de_aanvraag_niet(post):
    post.rapport_lukt = False
    r = client.post(RAPPORT, json=rapport_verzoek())
    assert r.status_code == 200, "vastgelegd is ontvangen; de mail volgt"
    body = r.json()
    assert body["opgeslagen"] is True
    assert body["verzonden"] is False and body["rapport"] == "in_wachtrij"
    # De andere stappen staan los van de mail aan de bezoeker.
    assert stappen(body["aanvraag_id"]) == {
        "mail_bezoeker": ("mislukt", 1), "mail_intern": ("gelukt", 1), "crm": ("gelukt", 1)}


def test_herhaaltaak_maakt_de_mislukte_mail_alsnog_af(post):
    post.rapport_lukt = False
    aanvraag_id = client.post(RAPPORT, json=rapport_verzoek()).json()["aanvraag_id"]

    assert verwerking.verwerk_achterstand() == 0, "eerst de wachttijd"
    post.rapport_lukt = True
    maak_verschuldigd(aanvraag_id)
    assert verwerking.verwerk_achterstand() == 1
    assert stappen(aanvraag_id)["mail_bezoeker"] == ("gelukt", 2)
    assert post.rapport == ["jan@voorbeeld.nl"] * 2


def test_wachttijd_loopt_op_en_stap_wordt_opgegeven(post, monkeypatch, caplog):
    monkeypatch.setenv("WEBSITE_MAX_POGINGEN", "3")
    post.signaal_lukt = False
    aanvraag_id = client.post(RAPPORT, json=rapport_verzoek()).json()["aanvraag_id"]
    for _ in range(2):
        maak_verschuldigd(aanvraag_id)
        with caplog.at_level(logging.ERROR, logger="rhadix.website"):
            verwerking.verwerk_achterstand()
    assert stappen(aanvraag_id)["mail_intern"] == ("opgegeven", 3)
    assert "opgegeven na 3 pogingen" in caplog.text
    assert aanvraag_id in caplog.text and "jan@voorbeeld.nl" not in caplog.text
    maak_verschuldigd(aanvraag_id)
    assert verwerking.verwerk_achterstand() == 0, "opgegeven is afgerond"


def test_contactbericht_blijft_bewaard_als_de_melding_mislukt(post):
    post.contact_lukt = False
    r = client.post(CONTACT, json=contact_verzoek())
    assert r.status_code == 200
    body = r.json()
    assert body["opgeslagen"] is True and body["verzonden"] is False
    assert stappen(body["aanvraag_id"]) == {"mail_intern": ("mislukt", 1), "crm": ("gelukt", 1)}


# ── Ontbrekend intern adres ───────────────────────────────────────────────────

def test_zonder_intern_adres_blijft_de_melding_in_de_wachtrij(post, monkeypatch):
    monkeypatch.delenv("WEBSITE_INTERN_ADRES")
    r = client.post(CONTACT, json=contact_verzoek())
    body = r.json()
    assert r.status_code == 200 and body["opgeslagen"] is True and body["verzonden"] is False
    assert stappen(body["aanvraag_id"])["mail_intern"] == ("geblokkeerd", 0), \
        "telt niet als poging: er is niets misgegaan, er ontbreekt iets"
    assert post.contact == [], "er gaat niets naar een niet-ingesteld adres"

    # Adres ingesteld: de taak stuurt de melding alsnog.
    monkeypatch.setenv("WEBSITE_INTERN_ADRES", "nieuw@voorbeeld.nl")
    maak_verschuldigd(body["aanvraag_id"])
    verwerking.verwerk_achterstand()
    assert stappen(body["aanvraag_id"])["mail_intern"] == ("gelukt", 1)
    assert post.contact == [body["aanvraag_id"]]


def test_ongeldig_intern_adres_houdt_de_melding_vast(post, monkeypatch):
    monkeypatch.setenv("WEBSITE_INTERN_ADRES", "info@@rhoderlanden")
    body = client.post(CONTACT, json=contact_verzoek()).json()
    assert body["opgeslagen"] is True and body["verzonden"] is False
    assert stappen(body["aanvraag_id"])["mail_intern"] == ("geblokkeerd", 0)
    assert post.contact == []


def test_met_mail_uit_wordt_niets_verstuurd_maar_alles_bewaard(post, monkeypatch):
    monkeypatch.setenv("MAIL_ENABLED", "false")
    body = client.post(RAPPORT, json=rapport_verzoek()).json()
    assert body["opgeslagen"] is True and body["rapport"] == "in_wachtrij"
    assert stappen(body["aanvraag_id"])["mail_bezoeker"] == ("geblokkeerd", 0)
    assert post.rapport == []


# ── Dezelfde inzending, geen tweede aanvraag ──────────────────────────────────

def test_dezelfde_aanvraag_id_levert_geen_tweede_aanvraag(post):
    sleutel = str(uuid.uuid4())
    eerste = client.post(CONTACT, json=contact_verzoek(aanvraag_id=sleutel)).json()
    limiet.wis_alles()       # de geheugenrem buiten spel: dit is de duurzame rem
    tweede = client.post(CONTACT, json=contact_verzoek(aanvraag_id=sleutel)).json()
    assert eerste["aanvraag_id"] == tweede["aanvraag_id"] == sleutel
    assert eerste["herhaling"] is False and tweede["herhaling"] is True
    assert tweede["verzonden"] is True, "de stand van de eerste inzending"
    assert post.contact == [sleutel]
    with opslag.sessie() as s:
        assert s.query(opslag.Aanvraag).count() == 1


@pytest.mark.parametrize("fout", ["123", "geen-uuid", "x" * 36, "'; drop table--"])
def test_ongeldige_aanvraag_id_wordt_geweigerd(post, fout):
    assert client.post(CONTACT, json=contact_verzoek(aanvraag_id=fout)).status_code == 422
    assert client.post(RAPPORT, json=rapport_verzoek(aanvraag_id=fout)).status_code == 422


# ── CRM: betrouwbaar en niet dubbel ───────────────────────────────────────────

def test_crm_storing_wordt_later_alsnog_geregistreerd(post):
    post.crm_lukt = False
    aanvraag_id = client.post(CONTACT, json=contact_verzoek()).json()["aanvraag_id"]
    assert stappen(aanvraag_id)["crm"] == ("mislukt", 1)
    post.crm_lukt = True
    maak_verschuldigd(aanvraag_id)
    verwerking.verwerk_achterstand()
    assert stappen(aanvraag_id)["crm"] == ("gelukt", 2)
    _, rijen = opslag.haal(aanvraag_id)
    assert rijen["crm"].extern_id == "act-2"


def test_crm_wordt_niet_dubbel_bijgewerkt_na_een_timeout(post):
    """De activiteit is aangemaakt, maar het antwoord ging verloren. De nieuwe
    poging vindt hem terug aan de aanvraag-id en maakt er geen tweede."""
    post.crm_lukt = "timeout"
    aanvraag_id = client.post(CONTACT, json=contact_verzoek()).json()["aanvraag_id"]
    assert stappen(aanvraag_id)["crm"] == ("mislukt", 1)
    maak_verschuldigd(aanvraag_id)
    verwerking.verwerk_achterstand()
    assert stappen(aanvraag_id)["crm"] == ("gelukt", 2)
    assert len(post.crm) == 1, "geen tweede activiteit"


def test_zonder_crm_koppeling_wordt_de_stap_overgeslagen(post, monkeypatch):
    monkeypatch.setattr(crm, "ingeschakeld", lambda: False)
    aanvraag_id = client.post(CONTACT, json=contact_verzoek()).json()["aanvraag_id"]
    assert stappen(aanvraag_id)["crm"] == ("overgeslagen", 1)


def test_aanvraag_id_staat_in_de_crm_activiteit():
    rapport = crm._omschrijving(bereken("data", ANTWOORDEN), "Jan", "Zorg BV",
                                "jan@voorbeeld.nl", None, "abc-123")
    bericht = crm._omschrijving_bericht("Jan", "Zorg BV", "jan@voorbeeld.nl", "", "", "Hoi",
                                        "Contactformulier", "Algemeen", "", None, "def-456")
    assert rapport.endswith("Aanvraag-ID: abc-123")
    assert bericht.endswith("Aanvraag-ID: def-456")


def test_zoek_activiteit_vindt_hem_aan_de_aanvraag_id(monkeypatch):
    from test_readiness_crm import NepAntwoord
    lijst = [{"id": "act-1", "omschrijving": "Bron: x\n\nAanvraag-ID: andere"},
             {"id": "act-2", "omschrijving": "Bron: x\n\nAanvraag-ID: deze"}]
    monkeypatch.setattr(crm, "_aanroep", lambda m, p, **kw: lijst if (m, p) == (
        "GET", "/api/crm/activiteiten") else NepAntwoord(404))
    assert crm.zoek_activiteit("deze")["id"] == "act-2"
    assert crm.zoek_activiteit("onbekend") is None


# ── Data of KIK-V ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("check,titel,kanaal,pagina", [
    ("data", "Data Readiness Check – rapport aangevraagd", "Data Readiness Check", "data-readiness"),
    ("kikv", "KIK-V Readiness Check – rapport aangevraagd", "KIK-V Readiness Check", "kik-v-readiness"),
])
def test_check_wordt_als_juiste_soort_geregistreerd(check, titel, kanaal, pagina, monkeypatch):
    server = NepCRM()
    for sleutel, waarde in [("CRM_BASIS_URL", "https://crm.test"), ("CRM_LOGIN_URL", "https://app.test"),
                            ("CRM_SERVICE_EMAIL", "s@test"), ("CRM_SERVICE_WACHTWOORD", "g")]:
        monkeypatch.setenv(sleutel, waarde)
    crm._token["waarde"] = None
    crm._token["geldig_tot"] = 0.0
    monkeypatch.setattr(crm.requests, "post", server.post_login)
    monkeypatch.setattr(crm.requests, "request", server.request)

    assert crm.registreer(bereken(check, ANTWOORDEN), naam="Jan", organisatie="Zorg BV",
                          email="jan@voorbeeld.nl", aanvraag_id="a-1")
    activiteit = server.activiteiten[0]
    assert activiteit["titel"] == titel
    assert activiteit["kanaal"] == kanaal
    assert activiteit["bronpagina"] == pagina
    assert activiteit["omschrijving"].startswith(f"Bron: {kanaal} (website)")
    assert server.contacten[0]["bronpagina"] == pagina


def test_kikv_aanvraag_wordt_met_check_soort_bewaard(post):
    body = client.post(RAPPORT, json=rapport_verzoek(check="kikv")).json()
    aanvraag, _ = opslag.haal(body["aanvraag_id"])
    assert aanvraag.check_soort == "kikv"


def test_bespreek_mijn_uitslag_vanaf_de_kikv_pagina():
    from app.services import website_cta as cta
    kanaal, interesse, _status, pagina = cta.duiding("kik-v-readiness", "uitslag")
    assert (kanaal, interesse, pagina) == ("Kennismaking", "Readiness Check", "kik-v-readiness")


# ── Zonder opslag: de oude werkwijze ──────────────────────────────────────────

def test_onbereikbare_opslag_valt_terug_op_direct_verwerken(post, monkeypatch, caplog):
    def stuk(*a, **kw):
        raise ConnectionError("database weg")
    monkeypatch.setattr(opslag, "leg_vast", stuk)
    with caplog.at_level(logging.ERROR, logger="rhadix.website"):
        r = client.post(RAPPORT, json=rapport_verzoek())
    assert r.status_code == 200
    body = r.json()
    assert body["opgeslagen"] is False and body["aanvraag_id"] is None
    assert body["rapport"] == "verzonden"
    assert post.rapport and post.signaal and post.crm, "alle stappen in één keer"
    assert "zonder opslag" in caplog.text


def test_onbereikbare_opslag_en_mislukte_mail_geeft_502(post, monkeypatch):
    monkeypatch.setattr(opslag, "leg_vast", lambda *a, **kw: (_ for _ in ()).throw(OSError()))
    post.contact_lukt = False
    assert client.post(CONTACT, json=contact_verzoek()).status_code == 502


def test_opslag_uit_is_de_oude_werkwijze(post, monkeypatch):
    monkeypatch.setenv("WEBSITE_OPSLAG", "uit")
    body = client.post(CONTACT, json=contact_verzoek()).json()
    assert body["opgeslagen"] is False and body["verzonden"] is True
    with opslag.sessie() as s:
        assert s.query(opslag.Aanvraag).count() == 0
    assert verwerking.start() is False, "geen herhaaltaak zonder opslag"


def test_honeypot_wordt_niet_vastgelegd(post):
    r = client.post(CONTACT, json=contact_verzoek(website="http://spam.example"))
    assert r.status_code == 202 and r.json()["opgeslagen"] is False
    with opslag.sessie() as s:
        assert s.query(opslag.Aanvraag).count() == 0


# ── Mailconfiguratie zichtbaar ────────────────────────────────────────────────

def test_controle_meldt_ontbrekend_adres_en_mail_uit(monkeypatch):
    monkeypatch.delenv("WEBSITE_INTERN_ADRES")
    monkeypatch.setenv("MAIL_ENABLED", "false")
    problemen = instellingen.controleer()
    assert any("MAIL_ENABLED" in p for p in problemen)
    assert any("contactformulier" in p for p in problemen)
    assert any("Readiness-signaal" in p for p in problemen)


def test_controle_meldt_ongeldig_adres(monkeypatch):
    monkeypatch.setenv("WEBSITE_INTERN_ADRES", "info@@rhoderlanden")
    assert any("WEBSITE_INTERN_ADRES is ongeldig" in p for p in instellingen.controleer())


def test_controle_is_tevreden_met_een_volledige_configuratie():
    assert instellingen.controleer() == []


def test_specifieke_instelling_gaat_voor_de_centrale(monkeypatch):
    monkeypatch.setenv("CONTACT_ONTVANGER", "test@voorbeeld.nl")
    assert instellingen.intern_adres(instellingen.CONTACT) == "test@voorbeeld.nl"
    assert instellingen.intern_adres(instellingen.READINESS) == "intern@voorbeeld.nl"
    monkeypatch.setenv("WEBSITE_REPLY_TO", "antwoord@voorbeeld.nl")
    assert instellingen.antwoordadres() == "antwoord@voorbeeld.nl"


def test_meld_bij_start_logt_elk_probleem(monkeypatch, caplog):
    monkeypatch.delenv("WEBSITE_INTERN_ADRES")
    with caplog.at_level(logging.ERROR, logger="rhadix.website"):
        instellingen.meld_bij_start(dns=False)
    assert caplog.text.count("Website-mailconfiguratie") == 2


def test_health_toont_de_stand_zonder_adressen(monkeypatch):
    goed = client.get("/api/health").json()
    assert goed["status"] == "ok"
    assert goed["website"] == {"opslag": "aan", "mail": "ok", "crm": goed["website"]["crm"]}
    monkeypatch.delenv("WEBSITE_INTERN_ADRES")
    fout = client.get("/api/health")
    assert fout.json()["website"]["mail"] == "onvolledig"
    assert "@" not in fout.text, "geen adressen op een publiek endpoint"


# ── Overzicht, opruimen, logs ─────────────────────────────────────────────────

def test_overzicht_bevat_geen_persoonsgegevens(post):
    post.signaal_lukt = False
    aanvraag_id = client.post(RAPPORT, json=rapport_verzoek()).json()["aanvraag_id"]
    gevallen = opslag.probleemgevallen()
    assert [(g["aanvraag_id"], g["stap"], g["status"]) for g in gevallen] == \
        [(aanvraag_id, "mail_intern", "mislukt")]
    html = verwerking.overzicht_tekst(gevallen)
    assert aanvraag_id in html
    for persoonsgegeven in ("jan@voorbeeld.nl", "Jan de Vries", "Zorggroep Voorbeeld"):
        assert persoonsgegeven not in html


def test_overzicht_gaat_alleen_weg_als_er_iets_openstaat(post, monkeypatch):
    verstuurd = []
    monkeypatch.setattr(verwerking, "send_email", lambda *a, **kw: verstuurd.append(a) or True)
    client.post(RAPPORT, json=rapport_verzoek())
    assert verwerking.stuur_overzicht() is False and verstuurd == []
    post.signaal_lukt = False
    limiet.wis_alles()
    client.post(RAPPORT, json=rapport_verzoek(naam="Anna Bos"))
    assert verwerking.stuur_overzicht() is True
    assert verstuurd[0][0] == "intern@voorbeeld.nl"


def test_aanvragen_voorbij_de_bewaartermijn_worden_verwijderd(post):
    oud = client.post(CONTACT, json=contact_verzoek()).json()["aanvraag_id"]
    limiet.wis_alles()
    nieuw = client.post(CONTACT, json=contact_verzoek(bericht="Nog een vraag")).json()["aanvraag_id"]
    with opslag.sessie() as s:
        s.get(opslag.Aanvraag, oud).bewaar_tot = opslag.nu() - timedelta(days=1)
    assert opslag.ruim_op() == 1
    assert opslag.haal(oud) == (None, {})
    assert opslag.haal(nieuw)[0] is not None


def test_maskeer():
    assert instellingen.maskeer("jan@voorbeeld.nl") == "j***@voorbeeld.nl"
    assert instellingen.maskeer("") == "—"


# ── Afbakening ────────────────────────────────────────────────────────────────

def test_opslag_kent_alleen_zijn_eigen_tabellen():
    assert sorted(opslag.Basis.metadata.tables) == ["website.aanvraag_stappen", "website.aanvragen"]
    from app.database import Base
    assert opslag.Basis.metadata is not Base.metadata
    assert not set(opslag.Basis.metadata.tables) & set(Base.metadata.tables)


def test_website_pakket_importeert_datavalidatie_niet():
    import types

    from app.website import instellingen as i, opslag as o, verwerking as v
    for mod in (i, o, v):
        for naam, waarde in vars(mod).items():
            if isinstance(waarde, types.ModuleType):
                assert not waarde.__name__.startswith(("app.models", "app.database", "app.auth")), \
                    f"{mod.__name__} importeert {waarde.__name__}"
            assert naam not in ("get_db", "SessionLocal", "get_current_user")
