"""
test_session_revocation_stap3.py — B-16 stap 3: Datavalidatie's eigen controle.

  * get_optional_user en require_app_access sluiten aan op de intrekking, met
    behoud van hun bestaande regels (geen token → None; RHADIX_ADMIN-bypass).
  * Uitloggen landt ook als het beeld muf is (eigen dependency zonder controle).
  * De uitgever past de lijst in hetzelfde proces toe (REVOCATION_APPLY_LOCALLY).
  * De noodprocedure is alleen bruikbaar vanaf het interne netwerk.
"""
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.auth.dependencies import get_optional_user, require_app_access
from app.database import get_db
from app.models.auth_models import User
from app.models.revocation_models import RevocationState, RevokedSession, SessionRevocation
from app.routers import internal_revocation as ir
from app.services import revocation_issuer as issuer
from app.services import session_revocation as sr
from app.auth.security import decode_access_token

# De door pytest geladen conftest; `tests.conftest` zou een tweede, lege database openen.
from conftest import TestingSessionLocal, override_get_db  # noqa: E402

GEHEIM = "g" * 40
_ECHTE_INTERNE_BRON = ir.interne_bron   # vóór het patchen in de fixture
NU = lambda: datetime.now(timezone.utc)  # noqa: E731


def _hash(geheim):
    import hashlib
    return hashlib.sha256(geheim.encode()).hexdigest()


@pytest.fixture(autouse=True)
def _schoon(monkeypatch):
    monkeypatch.setenv("SESSION_REVOCATION", "off")
    monkeypatch.setenv("REVOCATION_FRESHNESS_BUDGET", "60")
    monkeypatch.setenv("REVOCATION_BREAKGLASS_SECRET_SHA256", _hash(GEHEIM))
    monkeypatch.delenv("REVOCATION_TARGETS", raising=False)
    monkeypatch.delenv("REVOCATION_APPLY_LOCALLY", raising=False)
    monkeypatch.delenv("REVOCATION_BREAKGLASS_NETWORKS", raising=False)
    monkeypatch.delenv("REVOCATION_REQUIRE_IAT_FROM", raising=False)
    issuer._laatst_bekend = None
    issuer._nog_op_te_slaan.clear()
    issuer._stand_per_doel.clear()
    from app.auth import brute_force, token_blocklist
    brute_force._attempts.clear()
    token_blocklist._blocklist.clear()
    # De TestClient heeft geen IP-adres. De directe-bron-eis staat hieronder apart
    # getest; de strengere eis voor de noodprocedure blijft hier ongepatcht.
    monkeypatch.setattr(ir, "interne_bron", lambda request: True)
    yield
    issuer._laatst_bekend = None


@pytest.fixture()
def aan(monkeypatch):
    monkeypatch.setenv("SESSION_REVOCATION", "on")


@pytest.fixture()
def lokaal(monkeypatch):
    monkeypatch.setenv("REVOCATION_APPLY_LOCALLY", "on")
    return lambda: issuer.stuur_hartslag(TestingSessionLocal)


@pytest.fixture()
def mini():
    """Een kale app met de twee dependencies, zodat hun gedrag los te meten is."""
    app = FastAPI()

    @app.get("/optioneel")
    def _o(u: Optional[User] = Depends(get_optional_user)):
        return {"user": str(u.id) if u else None}

    @app.get("/app")
    def _a(u: Optional[User] = Depends(require_app_access("kikv-validator"))):
        return {"user": str(u.id) if u else None}

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


def _trek_in(user, token, seconden_geleden_gehoord=5):
    """Zet een intrekking en een stand neer zoals een hartslag dat zou doen."""
    with TestingSessionLocal() as s:
        s.add(RevokedSession(id=uuid.uuid4(), jti=decode_access_token(token)["jti"],
                             sub=str(user.id), not_before=NU(),
                             expires_at=NU() + timedelta(hours=1)))
        s.commit()
    _gehoord(seconden_geleden_gehoord)


def _gehoord(seconden_geleden):
    with TestingSessionLocal() as s:
        st = s.get(RevocationState, 1) or RevocationState(id=1, grace_expiry_logged=False)
        st.last_heard_at = NU() - timedelta(seconds=seconden_geleden)
        s.merge(st)
        s.commit()


# ── get_optional_user ─────────────────────────────────────────────────────

def test_optional_zonder_token_blijft_none(aan, mini):
    assert mini.get("/optioneel").json() == {"user": None}


def test_optional_vers_en_niet_ingetrokken_geeft_gebruiker(aan, mini, user_org_user, token_org_user):
    _gehoord(5)
    assert mini.get("/optioneel", headers=_h(token_org_user)).json()["user"] == str(user_org_user.id)


def test_optional_ingetrokken_sessie_telt_als_geen_sessie(aan, mini, user_org_user, token_org_user):
    _trek_in(user_org_user, token_org_user)
    assert mini.get("/optioneel", headers=_h(token_org_user)).json() == {"user": None}


def test_optional_muf_beeld_telt_als_geen_sessie(aan, mini, token_org_user):
    _gehoord(120)
    assert mini.get("/optioneel", headers=_h(token_org_user)).json() == {"user": None}


def test_optional_uit_is_ongewijzigd(mini, user_org_user, token_org_user):
    _trek_in(user_org_user, token_org_user, seconden_geleden_gehoord=9999)
    assert mini.get("/optioneel", headers=_h(token_org_user)).json()["user"] == str(user_org_user.id)


def test_validate_gebruikt_get_optional_user():
    """De twee echte consumenten in /api/validate lopen via get_optional_user en
    erven daarmee het gedrag dat hierboven is vastgepind."""
    import app.routers.validate as v
    bron = open(v.__file__).read()
    assert bron.count("Depends(get_optional_user)") == 2


# ── require_app_access ────────────────────────────────────────────────────

def test_app_zonder_token_blijft_none(aan, mini):
    assert mini.get("/app").json() == {"user": None}


def test_app_ingetrokken_sessie_geeft_401(aan, mini, user_org_user, token_org_user):
    _trek_in(user_org_user, token_org_user)
    r = mini.get("/app", headers=_h(token_org_user))
    assert r.status_code == 401 and r.json()["detail"] == "Sessie is ingetrokken"


def test_app_muf_beeld_geeft_401(aan, mini, token_rhadix_admin):
    _gehoord(120)
    r = mini.get("/app", headers=_h(token_rhadix_admin))
    assert r.status_code == 401, "ook RHADIX_ADMIN: de bypass geldt voor app-toegang, niet voor intrekking"


def test_app_bestaande_regels_blijven_bij_vers_beeld(aan, mini, token_rhadix_admin, token_org_user):
    _gehoord(5)
    assert mini.get("/app", headers=_h(token_rhadix_admin)).status_code == 200   # bypass blijft
    assert mini.get("/app", headers=_h(token_org_user)).status_code == 403       # geen toewijzing


def test_app_uit_is_ongewijzigd(mini, user_org_user, token_org_user, token_rhadix_admin):
    _trek_in(user_org_user, token_org_user, seconden_geleden_gehoord=9999)
    assert mini.get("/app", headers=_h(token_org_user)).status_code == 403
    assert mini.get("/app", headers=_h(token_rhadix_admin)).status_code == 200


def test_app_machinetoken_niet_getoetst(aan, mini):
    from app.auth.security import create_access_token
    _gehoord(9999)
    tok = create_access_token({"sub": str(uuid.uuid4()), "typ": "client", "scope": "external"})
    # Geen intrekkingsweigering; wel de bestaande regel: onbekende gebruiker → 401.
    r = mini.get("/app", headers=_h(tok))
    assert r.status_code == 401 and r.json()["detail"] == "User not found or deactivated"


# ── uitloggen landt ook bij een muf beeld ─────────────────────────────────

def test_logout_bij_muf_beeld_wordt_toch_vastgelegd(aan, client, user_org_user, token_org_user):
    _gehoord(600)
    assert client.post("/api/auth/logout", headers=_h(token_org_user)).status_code == 204
    with TestingSessionLocal() as s:
        assert s.query(SessionRevocation).filter(
            SessionRevocation.sub == str(user_org_user.id)).count() == 1


def test_logout_van_al_ingetrokken_token_wordt_toch_vastgelegd(aan, client, user_org_user,
                                                              token_org_user):
    _trek_in(user_org_user, token_org_user)
    client.post("/api/auth/logout", headers=_h(token_org_user))
    with TestingSessionLocal() as s:
        assert s.query(SessionRevocation).count() == 1


# ── lokale toepassing (Datavalidatie als eigen ontvanger) ─────────────────

def test_lokaal_maakt_de_eigen_stand_vers(lokaal):
    assert lokaal() == 1
    with TestingSessionLocal() as s:
        st = s.get(RevocationState, 1)
        assert st.last_heard_at is not None


def test_lokaal_volledige_keten(aan, lokaal, client, user_org_user, token_org_user, token_org_admin):
    lokaal()
    assert client.get("/api/auth/me", headers=_h(token_org_user)).status_code == 200
    client.post("/api/auth/logout", headers=_h(token_org_user))
    from app.auth import token_blocklist
    token_blocklist._blocklist.clear()       # alleen het centrale mechanisme meten
    lokaal()
    r = client.get("/api/auth/me", headers=_h(token_org_user))
    assert r.status_code == 401 and r.json()["detail"] == "Sessie is ingetrokken"
    assert client.get("/api/auth/me", headers=_h(token_org_admin)).status_code == 200


def test_lokaal_zonder_lijst_doet_niets(lokaal):
    def kapot():
        raise RuntimeError("db weg")
    assert issuer.stuur_hartslag(kapot) == 0
    with TestingSessionLocal() as s:
        assert s.get(RevocationState, 1) is None


def test_lokaal_en_extern_tegelijk(lokaal, client, monkeypatch):
    monkeypatch.setenv("REVOCATION_TARGETS", "http://intern")
    monkeypatch.setattr("httpx.post",
                        lambda url, json=None, timeout=None: client.post(
                            url.replace("http://intern", ""), json=json))
    assert lokaal() == 2


def test_status_toont_lokaal(lokaal, client, token_rhadix_admin):
    lokaal()
    doelen = client.get("/api/internal/revocation-status",
                        headers=_h(token_rhadix_admin)).json()["uitgever"]["doelen"]
    assert doelen["lokaal"]["fout"] is None


def test_aan_zonder_lokaal_geeft_luide_waarschuwing(aan, caplog):
    caplog.set_level(logging.ERROR, logger="rhadix.revocation")
    assert issuer.start() is False
    assert any("REVOCATION_APPLY_LOCALLY" in r.message for r in caplog.records)


def test_staging_compose_zet_lokaal_aan_en_controle_uit():
    import pathlib
    yml = (pathlib.Path(__file__).parents[2] / "docker-compose.staging.yml").read_text()
    assert 'SESSION_REVOCATION:            "off"' in yml
    assert 'REVOCATION_APPLY_LOCALLY:      "on"' in yml
    prod = (pathlib.Path(__file__).parents[2] / "docker-compose.prod.yml").read_text()
    assert "REVOCATION" not in prod, "productie blijft ongemoeid"


# ── noodprocedure: alleen intern ──────────────────────────────────────────

def _verzoek(host, headers=None):
    scope = {"type": "http", "method": "POST", "path": "/", "client": (host, 1234),
             "headers": [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]}
    return Request(scope)


@pytest.mark.parametrize("host,headers,verwacht", [
    ("127.0.0.1", {}, True),
    ("::1", {}, True),
    ("172.20.0.1", {}, True),                                   # docker-gateway op de server
    ("172.20.0.1", {"X-Real-IP": "1.2.3.4"}, False),            # via nginx
    ("172.20.0.1", {"X-Forwarded-For": "1.2.3.4"}, False),
    ("127.0.0.1", {"CF-Connecting-IP": "1.2.3.4"}, False),      # via Cloudflare
    ("127.0.0.1", {"Forwarded": "for=1.2.3.4"}, False),
    ("8.8.8.8", {}, False),                                     # rechtstreeks op de poort
    ("192.168.1.10", {}, False),
    ("testclient", {}, False),
])
def test_intern_verzoek(host, headers, verwacht):
    assert ir.intern_verzoek(_verzoek(host, headers)) is verwacht


@pytest.mark.parametrize("host,headers,verwacht", [
    ("172.20.0.1", {"X-Real-IP": "1.2.3.4"}, True),             # via nginx: bron is intern
    ("127.0.0.1", {}, True),
    ("8.8.8.8", {}, False),                                     # rechtstreeks op de poort
    ("8.8.8.8", {"X-Real-IP": "172.20.0.1"}, False),            # kop vervalsen helpt niet
])
def test_interne_bron(host, headers, verwacht):
    assert _ECHTE_INTERNE_BRON(_verzoek(host, headers)) is verwacht


def test_interne_endpoints_weigeren_een_externe_bron(client, monkeypatch, token_rhadix_admin):
    monkeypatch.setattr(ir, "interne_bron", lambda request: False)
    assert client.post("/api/internal/revocations", json={"token": "x"}).status_code == 403
    assert client.get("/api/internal/revocation-status",
                      headers=_h(token_rhadix_admin)).status_code == 403


def test_netten_zijn_instelbaar(monkeypatch):
    monkeypatch.setenv("REVOCATION_BREAKGLASS_NETWORKS", "10.0.0.0/8")
    assert ir.intern_verzoek(_verzoek("10.1.2.3"))
    assert not ir.intern_verzoek(_verzoek("127.0.0.1"))


GELDIG = {"duur_minuten": 5, "reden": "Uitgever onbereikbaar tijdens storing", "uitgevoerd_door": "T1"}


def test_extern_met_juist_geheim_wordt_geweigerd(client):
    r = client.post("/api/internal/revocation-grace", json=GELDIG,
                    headers={"X-Revocation-Breakglass": GEHEIM})
    assert r.status_code == 403
    with TestingSessionLocal() as s:
        assert s.get(RevocationState, 1) is None, "niets geactiveerd"


def test_extern_verraadt_niet_of_het_geheim_is_ingericht(client, monkeypatch):
    monkeypatch.setenv("REVOCATION_BREAKGLASS_SECRET_SHA256", "")
    r = client.post("/api/internal/revocation-grace", json=GELDIG,
                    headers={"X-Revocation-Breakglass": GEHEIM})
    assert r.status_code == 403


def test_extern_telt_niet_mee_voor_de_raadteller(client):
    from app.auth import brute_force
    client.post("/api/internal/revocation-grace", json=GELDIG,
                headers={"X-Revocation-Breakglass": "fout"})
    assert not brute_force._attempts


def test_status_met_geheim_alleen_intern_als_admin_overal(client, token_rhadix_admin):
    assert client.get("/api/internal/revocation-status",
                      headers={"X-Revocation-Breakglass": GEHEIM}).status_code == 403
    assert client.get("/api/internal/revocation-status",
                      headers=_h(token_rhadix_admin)).status_code == 200


def test_geheim_komt_niet_in_de_log(client, caplog, monkeypatch):
    caplog.set_level(logging.DEBUG)
    monkeypatch.setattr(ir, "intern_verzoek", lambda request: True)
    client.post("/api/internal/revocation-grace", json=GELDIG,
                headers={"X-Revocation-Breakglass": GEHEIM})
    client.post("/api/internal/revocation-grace", json=GELDIG,
                headers={"X-Revocation-Breakglass": "fout" + GEHEIM})
    assert all(GEHEIM not in r.getMessage() for r in caplog.records)
