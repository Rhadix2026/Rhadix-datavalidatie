"""
test_readiness_endpoint.py — Het publieke endpoint /api/readiness/report.

Getoetst worden de werking (geslaagde doorloop, herhaling, honeypot), de
invoervalidatie, de begrenzing en — het belangrijkst — de **isolatie**: dat dit
endpoint geen enkele productiegegevens kan raken en geen door de browser
meegestuurde score overneemt.

Mail wordt altijd gemockt; er gaat tijdens de tests niets de deur uit.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import readiness_limiet as limiet
from app.services import readiness_mail

client = TestClient(app)
PAD = "/api/readiness/report"


def geldig(**overschrijf):
    basis = {
        "check": "data",
        "antwoorden": [2, 1, 0, 3, 3, 3, 1, 1, 1, 2, 2, 2, 0, 0, 3],
        "naam": "Jan de Vries",
        "organisatie": "Zorggroep Voorbeeld",
        "email": "jan@voorbeeld.nl",
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
    """Vangt beide mails op in plaats van ze te versturen."""
    opgevangen = {"rapport": [], "signaal": []}

    def nep_rapport(rapport, email, pdf):
        opgevangen["rapport"].append({"rapport": rapport, "email": email, "pdf": pdf})
        return True

    def nep_signaal(rapport, email):
        opgevangen["signaal"].append({"rapport": rapport, "email": email})
        return True

    monkeypatch.setattr("app.routers.readiness.mail.verstuur_rapport", nep_rapport)
    monkeypatch.setattr("app.routers.readiness.mail.verstuur_signaal", nep_signaal)
    return opgevangen


# ── Geslaagde doorloop ────────────────────────────────────────────────────────

def test_volledige_doorloop(verstuurd):
    r = client.post(PAD, json=geldig())
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["verzonden"] is True
    assert body["herhaling"] is False
    assert body["totaal"] == 53
    assert body["categorie"] == "In ontwikkeling"
    assert [d["score"] for d in body["dimensies"]] == [33, 100, 33, 67, 33]

    assert len(verstuurd["rapport"]) == 1
    assert len(verstuurd["signaal"]) == 1
    verzonden = verstuurd["rapport"][0]
    assert verzonden["email"] == "jan@voorbeeld.nl"
    assert verzonden["pdf"][:5] == b"%PDF-"
    assert verzonden["rapport"].organisatie == "Zorggroep Voorbeeld"
    assert verzonden["rapport"].titel == "Indicatief Readiness-rapport op basis van uw antwoorden"


def test_signaalmail_draagt_geen_bijlage(verstuurd):
    """De interne melding is kort; het volledige rapport gaat intern niet mee."""
    client.post(PAD, json=geldig())
    signaal = verstuurd["signaal"][0]
    assert set(signaal) == {"rapport", "email"}, "verstuur_signaal kent geen pdf-parameter"


@pytest.mark.parametrize("check, verwacht", [("data", "Datagereed"), ("kikv", "KIK-V-gereed")])
def test_beide_checks_werken(verstuurd, check, verwacht):
    r = client.post(PAD, json=geldig(check=check, antwoorden=[3] * 15,
                                     email=f"{check}@voorbeeld.nl"))
    assert r.status_code == 200
    assert r.json()["totaal"] == 100
    assert r.json()["categorie"] == verwacht


def test_mislukte_verzending_geeft_502_en_legt_niets_vast(monkeypatch):
    monkeypatch.setattr("app.routers.readiness.mail.verstuur_rapport",
                        lambda *a, **k: False)
    monkeypatch.setattr("app.routers.readiness.mail.verstuur_signaal",
                        lambda *a, **k: True)
    r = client.post(PAD, json=geldig())
    assert r.status_code == 502
    # Niets vastgelegd, dus opnieuw proberen moet kunnen
    assert not limiet.is_herhaling(
        limiet.vingerafdruk("jan@voorbeeld.nl", "data", geldig()["antwoorden"]))


def test_mislukte_signaalmail_laat_het_rapport_staan(monkeypatch):
    monkeypatch.setattr("app.routers.readiness.mail.verstuur_rapport", lambda *a, **k: True)
    monkeypatch.setattr("app.routers.readiness.mail.verstuur_signaal", lambda *a, **k: False)
    r = client.post(PAD, json=geldig())
    assert r.status_code == 200, "de bezoeker mag hier geen last van hebben"
    assert r.json()["verzonden"] is True


# ── Honeypot ──────────────────────────────────────────────────────────────────

def test_honeypot_wordt_stil_weggegooid(verstuurd):
    r = client.post(PAD, json=geldig(website="http://spam.example"))
    assert r.status_code == 202
    assert r.json()["verzonden"] is False
    assert verstuurd["rapport"] == [] and verstuurd["signaal"] == []


def test_leeg_honeypotveld_is_normaal(verstuurd):
    r = client.post(PAD, json=geldig(website="   "))
    assert r.status_code == 200
    assert len(verstuurd["rapport"]) == 1


# ── Invoervalidatie ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("wijziging", [
    {"antwoorden": [0] * 14},
    {"antwoorden": [0] * 16},
    {"antwoorden": [0] * 14 + [9]},
    {"antwoorden": [0] * 14 + [-1]},
    {"check": "onbekend"},
    {"email": "geen-adres"},
    {"naam": "J"},
    {"organisatie": " "},
])
def test_ongeldige_invoer_geeft_422(verstuurd, wijziging):
    r = client.post(PAD, json=geldig(**wijziging))
    assert r.status_code == 422
    assert verstuurd["rapport"] == []


def test_ontbrekende_velden_geven_422(verstuurd):
    assert client.post(PAD, json={"check": "data"}).status_code == 422
    assert verstuurd["rapport"] == []


def test_meegestuurde_score_wordt_geweigerd(verstuurd):
    """Een verzoek met een eigen totaalscore erin wordt niet geaccepteerd."""
    r = client.post(PAD, json=geldig(totaal=100, dimensies=[100] * 5))
    assert r.status_code == 422, "onbekende velden zijn verboden"
    assert verstuurd["rapport"] == []


def test_score_komt_altijd_uit_de_antwoorden(verstuurd):
    """Ook zonder smokkelveld: de uitkomst hoort bij de antwoorden, niet bij
    wat de client zou willen."""
    r = client.post(PAD, json=geldig(antwoorden=[0] * 15))
    assert r.json()["totaal"] == 0
    assert r.json()["categorie"] == "Basis op orde brengen"


def test_naam_en_organisatie_worden_genormaliseerd(verstuurd):
    client.post(PAD, json=geldig(naam="  Jan   de   Vries ", organisatie=" Zorg  BV "))
    rapport = verstuurd["rapport"][0]["rapport"]
    assert rapport.naam == "Jan de Vries"
    assert rapport.organisatie == "Zorg BV"


# ── Begrenzing ────────────────────────────────────────────────────────────────

def test_dezelfde_aanvraag_levert_geen_tweede_mail(verstuurd):
    eerste = client.post(PAD, json=geldig())
    tweede = client.post(PAD, json=geldig())
    assert eerste.json()["verzonden"] is True
    assert tweede.status_code == 200
    assert tweede.json()["verzonden"] is False
    assert tweede.json()["herhaling"] is True
    assert tweede.json()["totaal"] == eerste.json()["totaal"]
    assert len(verstuurd["rapport"]) == 1, "precies één mail"


def test_andere_antwoorden_leveren_wel_een_nieuw_rapport(verstuurd):
    client.post(PAD, json=geldig())
    anders = geldig()
    anders["antwoorden"] = [3] * 15
    r = client.post(PAD, json=anders)
    assert r.json()["verzonden"] is True
    assert len(verstuurd["rapport"]) == 2


def test_te_veel_aanvragen_voor_een_adres_geeft_429(verstuurd, monkeypatch):
    monkeypatch.setattr(limiet, "MAX_PER_ADRES", 3)
    for i in range(3):
        punten = [0] * 15
        punten[i] = 3
        assert client.post(PAD, json=geldig(antwoorden=punten)).status_code == 200
    punten = [0] * 15
    punten[7] = 3
    r = client.post(PAD, json=geldig(antwoorden=punten))
    assert r.status_code == 429
    assert len(verstuurd["rapport"]) == 3


def test_ander_adres_heeft_een_eigen_teller(verstuurd, monkeypatch):
    monkeypatch.setattr(limiet, "MAX_PER_ADRES", 1)
    assert client.post(PAD, json=geldig(email="een@voorbeeld.nl")).status_code == 200
    assert client.post(PAD, json=geldig(email="twee@voorbeeld.nl",
                                        antwoorden=[3] * 15)).status_code == 200


def test_hoofdletters_in_het_adres_omzeilen_de_teller_niet():
    a = limiet.vingerafdruk("Jan@Voorbeeld.NL", "data", [0] * 15)
    b = limiet.vingerafdruk("jan@voorbeeld.nl", "data", [0] * 15)
    assert a == b


def test_vingerafdruk_bevat_het_adres_niet_leesbaar():
    afdruk = limiet.vingerafdruk("jan@voorbeeld.nl", "data", [0] * 15)
    assert "jan" not in afdruk and "@" not in afdruk
    assert len(afdruk) == 64


# ── Isolatie ──────────────────────────────────────────────────────────────────

def _route():
    for r in app.routes:
        if getattr(r, "path", None) == PAD:
            return r
    raise AssertionError(f"route {PAD} niet gevonden")


def test_route_heeft_geen_enkele_dependency():
    """De belangrijkste waarborg, en wel op de route zelf in plaats van op de
    brontekst: geen `Depends(...)` betekent geen databasesessie, geen gebruiker,
    geen tenant. Deze route kan dus niets in de productiegegevens lezen of
    wijzigen."""
    afhankelijk = _route().dependant
    assert afhankelijk.dependencies == []
    assert afhankelijk.security_requirements == []
    # Alleen het verzoekmodel en het antwoordobject, geen ingespoten sessie.
    assert [p for p in afhankelijk.query_params + afhankelijk.path_params
            + afhankelijk.header_params + afhankelijk.cookie_params] == []


def test_module_kent_de_database_niet():
    """Geen enkele database- of modelmodule is bereikbaar vanuit deze router."""
    import types

    from app.routers import readiness as mod

    for naam, waarde in vars(mod).items():
        if isinstance(waarde, types.ModuleType):
            assert not waarde.__name__.startswith(("app.models", "app.database", "sqlalchemy")), \
                f"readiness.py importeert {waarde.__name__} als {naam}"
        assert naam not in ("get_db", "SessionLocal", "engine", "Base"), \
            f"readiness.py heeft {naam} in zijn namespace"


def test_module_kent_geen_authenticatie():
    import types

    from app.routers import readiness as mod

    for naam, waarde in vars(mod).items():
        if isinstance(waarde, types.ModuleType):
            assert not waarde.__name__.startswith("app.auth"), \
                f"readiness.py importeert {waarde.__name__}"
        assert naam not in ("get_current_user", "get_optional_user", "require_app_access"), \
            f"readiness.py heeft {naam} in zijn namespace"


def test_verzoekmodel_weigert_onbekende_velden():
    """Voorkomt dat er ooit stilzwijgend een tenant, rol of score in glipt."""
    from app.routers.readiness import RapportVerzoek

    assert RapportVerzoek.model_config.get("extra") == "forbid"
    assert set(RapportVerzoek.model_fields) == {
        "check", "antwoorden", "naam", "organisatie", "email", "website",
        # Campagneherkomst voor de CRM-opvolging. Geen persoonsgegevens, en ze
        # raken de uitslag niet — zie test_readiness_crm.py.
        "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term"}
    # Wat er nadrukkelijk níét in mag: een door de browser bepaalde uitslag.
    for verboden in ("totaal", "score", "dimensies", "categorie", "tenant_id"):
        assert verboden not in RapportVerzoek.model_fields


def test_endpoint_werkt_zonder_enige_authenticatie(verstuurd):
    r = client.post(PAD, json=geldig())
    assert r.status_code == 200
    assert "authorization" not in {k.lower() for k in r.request.headers}


def test_alleen_post_is_toegestaan():
    assert client.get(PAD).status_code == 405
    assert client.delete(PAD).status_code == 405
