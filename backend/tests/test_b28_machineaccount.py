"""
test_b28_machineaccount.py — B-28 stap 2: machineaccounts in Datavalidatie.

Testcriteria uit het ontwerp: niet interactief, alleen de nodige rechten, kort
geldig met doelgroep en scope, veilig roteren en intrekken, aansluiting op B-16,
alles geaudit en geen geheim in log of antwoord (behalve één keer bij aanmaak).
"""
import json
import logging
import time
import uuid

import pytest
from jose import jwt

from app.auth import brute_force
from app.auth.security import decode_access_token
from app.models.revocation_models import SessionRevocation
from app.services import machine_auth as ma

from conftest import TestingSessionLocal  # noqa: E402

DOEL = "datastation-staging"


@pytest.fixture(autouse=True)
def _schoon(monkeypatch):
    monkeypatch.setenv("SESSION_REVOCATION", "off")
    monkeypatch.delenv("MACHINE_TOKEN_MINUTES", raising=False)
    brute_force.reset()
    from app.services import revocation_issuer as issuer
    issuer._laatst_bekend = None
    issuer._nog_op_te_slaan.clear()
    yield
    brute_force.reset()


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture()
def account(client, token_rhadix_admin):
    r = client.post("/api/admin/machine-accounts", headers=_h(token_rhadix_admin),
                    json={"naam": "uitvraag-staging", "doelgroepen": [DOEL],
                          "scopes": ["datastation:vragen", "datastation:resultaat"]})
    assert r.status_code == 201, r.text
    return r.json()


def _token(client, account, geheim=None, **extra):
    body = {"grant_type": "client_credentials", "client_id": account["client_id"],
            "client_secret": geheim or account["client_secret"], **extra}
    return client.post("/api/auth/machine-token", json=body)


def _audit(caplog, event):
    uit = []
    for r in caplog.records:
        if r.name == "rhadix.audit":
            try:
                d = json.loads(r.getMessage())
            except ValueError:
                continue
            if d.get("event") == event:
                uit.append(d)
    return uit


# ── uitgifte en vorm van het token ───────────────────────────────────────────
def test_aanmaken_geeft_geheim_eenmalig(client, token_rhadix_admin, account):
    assert account["client_secret"].startswith("rmx_") and len(account["client_secret"]) >= 40
    lijst = client.get("/api/admin/machine-accounts", headers=_h(token_rhadix_admin)).text
    assert account["client_secret"] not in lijst and account["client_secret"][:8] in lijst


def test_token_claims(client, account):
    r = _token(client, account)
    assert r.status_code == 200, r.text
    d = r.json()
    c = decode_access_token(d["access_token"])
    assert c["typ"] == "machine" and c["aud"] == DOEL and c["sub"] == account["client_id"]
    assert set(c["scope"].split()) == {"datastation:vragen", "datastation:resultaat"}
    assert c["apps"] == [] and c["jti"] and c["iat"]
    assert c["exp"] - c["iat"] <= 900 and d["expires_in"] <= 900


def test_levensduur_nooit_langer_dan_15_minuten(client, account, monkeypatch):
    monkeypatch.setenv("MACHINE_TOKEN_MINUTES", "120")
    c = decode_access_token(_token(client, account).json()["access_token"])
    assert c["exp"] - c["iat"] <= 900


def test_jti_uniek(client, account):
    a = decode_access_token(_token(client, account).json()["access_token"])["jti"]
    b = decode_access_token(_token(client, account).json()["access_token"])["jti"]
    assert a != b


def test_andere_doelgroep_geweigerd(client, account):
    assert _token(client, account, audience="datastation-productie").status_code == 401


@pytest.mark.parametrize("geheim", ["rmx_fout", "verkeerd", "", "rmx_" + "x" * 43])
def test_fout_geheim(client, account, geheim):
    assert _token(client, account, geheim=geheim or "rmx_").status_code == 401


def test_onbekend_account(client, account):
    body = {"client_id": str(uuid.uuid4()), "client_secret": account["client_secret"]}
    assert client.post("/api/auth/machine-token", json=body).status_code == 401


def test_begrenzing_na_herhaald_falen(client, account):
    codes = [_token(client, account, geheim="rmx_fout").status_code for _ in range(6)]
    assert codes[-1] == 429
    assert _token(client, account).status_code == 429, "ook met het juiste geheim tot de blokkade voorbij is"


# ── niet interactief en alleen de nodige rechten ─────────────────────────────
def test_kan_niet_inloggen(client, account):
    for email in (account["naam"], account["client_id"], f"{account['naam']}@rhadix.nl"):
        r = client.post("/api/auth/login", json={"email": email, "password": account["client_secret"]})
        assert r.status_code in (401, 422)


@pytest.mark.parametrize("pad", ["/api/auth/me", "/api/history/", "/api/admin/tenants", "/api/org/users",
                                 "/api/admin/machine-accounts"])
def test_machinetoken_geweigerd_in_datavalidatie(client, account, pad):
    tok = _token(client, account).json()["access_token"]
    assert client.get(pad, headers=_h(tok)).status_code in (401, 403)


def test_machinetoken_is_geen_optionele_sessie(account, client):
    from app.auth.dependencies import _optional_user
    from starlette.requests import Request
    tok = _token(client, account).json()["access_token"]
    req = Request({"type": "http", "headers": [(b"authorization", f"Bearer {tok}".encode())], "method": "GET",
                   "path": "/", "query_string": b""})
    with TestingSessionLocal() as db:
        assert _optional_user(req, None, db, intrekking=False) is None


def test_onbekende_scope_niet_toe_te_kennen(client, token_rhadix_admin):
    r = client.post("/api/admin/machine-accounts", headers=_h(token_rhadix_admin),
                    json={"naam": "te-veel", "doelgroepen": [DOEL], "scopes": ["admin:alles"]})
    assert r.status_code == 422


def test_beheer_alleen_rhadix_admin(client, token_org_admin):
    r = client.post("/api/admin/machine-accounts", headers=_h(token_org_admin),
                    json={"naam": "x-test", "doelgroepen": [DOEL], "scopes": ["datastation:vragen"]})
    assert r.status_code == 403


# ── rotatie en intrekking ────────────────────────────────────────────────────
def test_rotatie_zonder_onderbreking(client, token_rhadix_admin, account):
    aid = account["client_id"]
    nieuw = client.post(f"/api/admin/machine-accounts/{aid}/secrets", headers=_h(token_rhadix_admin)).json()
    assert _token(client, account).status_code == 200, "oude geheim werkt nog"
    assert _token(client, account, geheim=nieuw["client_secret"]).status_code == 200, "nieuwe ook"
    derde = client.post(f"/api/admin/machine-accounts/{aid}/secrets", headers=_h(token_rhadix_admin))
    assert derde.status_code == 409, "maximaal twee actief"
    oud_sid = [g["sid"] for g in client.get("/api/admin/machine-accounts", headers=_h(token_rhadix_admin))
               .json()["accounts"][0]["geheimen"] if g["sid"] != nieuw["sid"]][0]
    r = client.delete(f"/api/admin/machine-accounts/{aid}/secrets/{oud_sid}", headers=_h(token_rhadix_admin))
    assert r.status_code == 204
    assert _token(client, account).status_code == 401, "ingetrokken geheim geeft geen token meer"
    assert _token(client, account, geheim=nieuw["client_secret"]).status_code == 200


def test_intrekken_geheim_trekt_tokens_in(client, token_rhadix_admin, account):
    aid = account["client_id"]
    sid = account["geheimen"][0]["sid"]
    client.delete(f"/api/admin/machine-accounts/{aid}/secrets/{sid}", headers=_h(token_rhadix_admin))
    with TestingSessionLocal() as s:
        assert s.query(SessionRevocation).filter(SessionRevocation.sub == aid).count() == 1


def test_deactiveren(client, token_rhadix_admin, account, caplog):
    aid = account["client_id"]
    with caplog.at_level(logging.INFO, logger="rhadix.audit"):
        r = client.patch(f"/api/admin/machine-accounts/{aid}/active", headers=_h(token_rhadix_admin),
                         json={"is_active": False})
    assert r.status_code == 200 and r.json()["is_active"] is False
    assert _token(client, account).status_code == 401
    assert len(_audit(caplog, "machine_account_deactivated")) == 1
    with TestingSessionLocal() as s:
        assert s.query(SessionRevocation).filter(SessionRevocation.sub == aid).count() == 1
    client.patch(f"/api/admin/machine-accounts/{aid}/active", headers=_h(token_rhadix_admin), json={"is_active": True})
    assert _token(client, account).status_code == 200


def test_verlopen_geheim(client, account):
    from datetime import datetime, timedelta, timezone
    from app.models.machine_models import MachineSecret
    with TestingSessionLocal() as s:
        for g in s.query(MachineSecret).all():
            g.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        s.commit()
    assert _token(client, account).status_code == 401


# ── B-16: machinetokens vallen onder de intrekking ───────────────────────────
def test_machinetoken_onder_controle_b(account, client, monkeypatch):
    from datetime import datetime, timedelta, timezone
    from app.services import session_revocation as sr
    monkeypatch.setenv("SESSION_REVOCATION", "on")
    c = decode_access_token(_token(client, account).json()["access_token"])
    later = datetime.fromtimestamp(c["iat"], tz=timezone.utc) + timedelta(seconds=1)
    u = sr.controleer(c, ingetrokken_jtis=set(), logout_at_voor_sub=lambda s: later,
                      laatst_gehoord=datetime.now(timezone.utc))
    assert not u.toegestaan and u.grondslag == "B"


# ── audit en geen geheimen in de log ─────────────────────────────────────────
def test_audit_en_geen_geheim_in_log(client, account, caplog):
    with caplog.at_level(logging.INFO):
        ok = _token(client, account).json()["access_token"]
        _token(client, account, geheim="rmx_fout")
    uitgegeven = _audit(caplog, "machine_token_issued")
    geweigerd = _audit(caplog, "machine_token_denied")
    assert len(uitgegeven) == 1 and uitgegeven[0]["jti"] and uitgegeven[0]["aud"] == DOEL
    assert len(geweigerd) == 1 and geweigerd[0]["reden"] == "geheim onjuist"
    tekst = caplog.text
    assert account["client_secret"] not in tekst and ok not in tekst and "rmx_fout" not in tekst
