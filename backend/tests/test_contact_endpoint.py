"""
test_contact_endpoint.py — Het publieke contactendpoint /api/contact.

Tot dit endpoint bestond, vingen de formulieren op de website hun eigen
verzending af met een melding dat de site een prototype was: er ging nooit iets
weg. Deze tests leggen vast dat er nu werkelijk wordt verstuurd, en dat het
endpoint dezelfde afbakening en afweer heeft als het Readiness-endpoint.

Mail wordt altijd gemockt; er gaat tijdens de tests niets de deur uit.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import contact_mail
from app.services import readiness_limiet as limiet

client = TestClient(app)
PAD = "/api/contact"


def geldig(**overschrijf):
    basis = {
        "naam": "Jan de Vries",
        "email": "jan@voorbeeld.nl",
        "organisatie": "Zorggroep Voorbeeld",
        "telefoon": "0612345678",
        "bericht": "Graag een afspraak over de datagereedheidsscan.",
    }
    basis.update(overschrijf)
    return basis


@pytest.fixture(autouse=True)
def schone_limiet():
    limiet.wis_alles()
    yield
    limiet.wis_alles()


@pytest.fixture
def verstuurd(monkeypatch):
    opgevangen = []

    def nep(**kw):
        opgevangen.append(kw)
        return True

    monkeypatch.setattr("app.routers.contact.contact_mail.verstuur", nep)
    return opgevangen


# ── Geslaagde doorloop ────────────────────────────────────────────────────────

def test_bericht_wordt_verstuurd(verstuurd):
    r = client.post(PAD, json=geldig())
    assert r.status_code == 200
    assert r.json() == {"ok": True, "verzonden": True, "herhaling": False}

    assert len(verstuurd) == 1
    b = verstuurd[0]
    assert b["naam"] == "Jan de Vries"
    assert b["email"] == "jan@voorbeeld.nl"
    assert b["organisatie"] == "Zorggroep Voorbeeld"
    assert b["telefoon"] == "0612345678"
    assert "datagereedheidsscan" in b["bericht"]


def test_organisatie_en_telefoon_zijn_optioneel(verstuurd):
    r = client.post(PAD, json={"naam": "Anna Bos", "email": "anna@voorbeeld.nl",
                               "bericht": "Bel me even."})
    assert r.status_code == 200
    assert verstuurd[0]["organisatie"] == ""
    assert verstuurd[0]["telefoon"] == ""


def test_uitslag_bespreken_stuurt_de_samenvatting_mee(verstuurd):
    """Het blok 'Bespreek mijn uitslag' vult het bericht met de samenvatting en
    zet het type check als onderwerp."""
    samenvatting = ("Data Readiness Check — samenvatting\nTotaalscore: 53/100 "
                    "(In ontwikkeling)\n- Databeschikbaarheid: 33")
    r = client.post(PAD, json=geldig(bericht=samenvatting, onderwerp="Data Readiness Check"))
    assert r.status_code == 200
    assert verstuurd[0]["onderwerp"] == "Data Readiness Check"
    assert "Totaalscore: 53/100" in verstuurd[0]["bericht"]


def test_mislukte_verzending_geeft_502_en_legt_niets_vast(monkeypatch):
    monkeypatch.setattr("app.routers.contact.contact_mail.verstuur", lambda **kw: False)
    r = client.post(PAD, json=geldig())
    assert r.status_code == 502
    # Opnieuw proberen moet kunnen
    g = geldig()
    afdruk = limiet.vingerafdruk("jan@voorbeeld.nl", "contact",
                                 [g["naam"], g["organisatie"], "", g["bericht"]])
    assert not limiet.is_herhaling(afdruk)


# ── Honeypot ──────────────────────────────────────────────────────────────────

def test_honeypot_wordt_stil_weggegooid(verstuurd):
    r = client.post(PAD, json=geldig(website="http://spam.example"))
    assert r.status_code == 202
    assert r.json()["verzonden"] is False
    assert verstuurd == []


def test_leeg_honeypotveld_is_normaal(verstuurd):
    assert client.post(PAD, json=geldig(website="  ")).status_code == 200
    assert len(verstuurd) == 1


# ── Invoervalidatie ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("wijziging", [
    {"email": "geen-adres"},
    {"naam": "J"},
    {"naam": "   "},
    {"bericht": "x" * 5000},
])
def test_ongeldige_invoer_geeft_422(verstuurd, wijziging):
    assert client.post(PAD, json=geldig(**wijziging)).status_code == 422
    assert verstuurd == []


def test_leeg_bericht_zonder_onderwerp_wordt_geweigerd(verstuurd):
    r = client.post(PAD, json=geldig(bericht="   "))
    assert r.status_code == 422
    assert verstuurd == []


def test_onbekende_velden_worden_geweigerd(verstuurd):
    """Voorkomt dat er ooit stilzwijgend een veld in glipt dat hier niet hoort."""
    assert client.post(PAD, json=geldig(tenant_id="x")).status_code == 422
    assert verstuurd == []


def test_naam_en_organisatie_worden_genormaliseerd(verstuurd):
    client.post(PAD, json=geldig(naam="  Jan   de  Vries ", organisatie=" Zorg  BV "))
    assert verstuurd[0]["naam"] == "Jan de Vries"
    assert verstuurd[0]["organisatie"] == "Zorg BV"


# ── Begrenzing ────────────────────────────────────────────────────────────────

def test_hetzelfde_bericht_gaat_niet_twee_keer(verstuurd):
    eerste = client.post(PAD, json=geldig())
    tweede = client.post(PAD, json=geldig())
    assert eerste.json()["verzonden"] is True
    assert tweede.json() == {"ok": True, "verzonden": False, "herhaling": True}
    assert len(verstuurd) == 1


def test_berichten_van_gelijke_lengte_zijn_niet_hetzelfde(verstuurd):
    """De vingerafdruk gaat over de inhoud, niet over een afgeleide daarvan.
    Twee verschillende berichten van toevallig gelijke lengte moeten allebei
    aankomen."""
    assert client.post(PAD, json=geldig(bericht="Bericht nummer een...")).json()["verzonden"] is True
    assert client.post(PAD, json=geldig(bericht="Bericht nummer twee..")).json()["verzonden"] is True
    assert len(verstuurd) == 2


def test_een_ander_bericht_gaat_wel(verstuurd):
    client.post(PAD, json=geldig())
    assert client.post(PAD, json=geldig(bericht="Een heel ander bericht."))\
        .json()["verzonden"] is True
    assert len(verstuurd) == 2


def test_te_veel_berichten_vanaf_een_adres_geeft_429(verstuurd, monkeypatch):
    monkeypatch.setattr(limiet, "MAX_PER_ADRES", 3)
    for i in range(3):
        assert client.post(PAD, json=geldig(bericht=f"Bericht nummer {i}.")).status_code == 200
    assert client.post(PAD, json=geldig(bericht="En nog een keer.")).status_code == 429
    assert len(verstuurd) == 3


# ── Isolatie ──────────────────────────────────────────────────────────────────

def _route():
    for r in app.routes:
        if getattr(r, "path", None) == PAD:
            return r
    raise AssertionError(f"route {PAD} niet gevonden")


def test_route_heeft_geen_enkele_dependency():
    afhankelijk = _route().dependant
    assert afhankelijk.dependencies == []
    assert afhankelijk.security_requirements == []


def test_module_kent_database_noch_authenticatie():
    import types

    from app.routers import contact as mod

    for naam, waarde in vars(mod).items():
        if isinstance(waarde, types.ModuleType):
            assert not waarde.__name__.startswith(
                ("app.models", "app.database", "sqlalchemy", "app.auth")), waarde.__name__
        assert naam not in ("get_db", "SessionLocal", "engine", "Base", "get_current_user")


def test_alleen_post_is_toegestaan():
    assert client.get(PAD).status_code == 405
    assert client.delete(PAD).status_code == 405


# ── De mail zelf ──────────────────────────────────────────────────────────────

@pytest.fixture
def smtp(monkeypatch):
    for sleutel, waarde in [("MAIL_ENABLED", "true"), ("SMTP_HOST", "smtp.test"),
                            ("SMTP_FROM", "noreply@rhadix.nl"), ("SMTP_FROM_NAME", "Rhadix")]:
        monkeypatch.setenv(sleutel, waarde)
    monkeypatch.delenv("SMTP_REPLY_TO", raising=False)
    monkeypatch.delenv("CONTACT_ONTVANGER", raising=False)
    berichten = []

    class Nep:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def ehlo(self): pass
        def starttls(self, context=None): pass
        def login(self, *_): pass
        def send_message(self, msg): berichten.append(msg)

    from app.services import mailer
    monkeypatch.setattr(mailer.smtplib, "SMTP", lambda *a, **k: Nep())
    return berichten


def test_mail_gaat_naar_rhoderlanden_met_antwoord_naar_de_bezoeker(smtp):
    assert contact_mail.verstuur(naam="Jan de Vries", email="jan@voorbeeld.nl",
                                 organisatie="Zorg BV", bericht="Hallo") is True
    msg = smtp[0]
    assert msg["To"] == "info@rhoderlandengroep.nl"
    assert msg["From"] == "Rhoderlanden Groep <noreply@rhadix.nl>"
    assert msg["Reply-To"] == "jan@voorbeeld.nl"
    assert msg["Subject"] == "Website: bericht van Jan de Vries (Zorg BV)"
    assert list(msg.iter_attachments()) == []


def test_ontvanger_is_instelbaar(smtp, monkeypatch):
    monkeypatch.setenv("CONTACT_ONTVANGER", "test@voorbeeld.nl")
    contact_mail.verstuur(naam="Jan", email="jan@voorbeeld.nl", bericht="Hoi")
    assert smtp[0]["To"] == "test@voorbeeld.nl"


def test_lege_instelling_valt_terug_op_het_echte_adres(monkeypatch):
    monkeypatch.setenv("CONTACT_ONTVANGER", "   ")
    assert contact_mail.ontvanger() == "info@rhoderlandengroep.nl"


def test_regelovergangen_blijven_zichtbaar():
    html = contact_mail.opmaak("Jan", "jan@voorbeeld.nl", "", "", "Regel 1\nRegel 2", "")
    assert "Regel 1<br>Regel 2" in html


def test_html_uit_het_formulier_wordt_ontsnapt():
    html = contact_mail.opmaak('<script>alert(1)</script>', "jan@voorbeeld.nl",
                               "A & B", "", "<b>vet</b>", "")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "A &amp; B" in html
    assert "&lt;b&gt;vet&lt;/b&gt;" in html
