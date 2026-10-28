"""
test_session_revocation_stap2.py — B-16 stap 2: opslag, hartslag, push, de drie
endpoints en de aansluiting op get_current_user en logout.

De keten wordt hier volledig doorlopen zonder netwerk: de hartslag van de
uitgever wordt via de TestClient op het eigen ontvangst-endpoint afgeleverd.
De nummers in de testnamen verwijzen naar de acceptatiecriteria in
TESTCYCLUS-RHADIX-2026-10.md, sectie 12.
"""
import time
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.auth.security import create_access_token, decode_access_token
from app.models.auth_models import User
from app.models.revocation_models import RevocationState, RevokedSession, SessionRevocation
from app.services import revocation_issuer as issuer
from app.services import revocation_receiver as receiver
from app.services import session_revocation as sr
# De door pytest geladen conftest; `tests.conftest` zou een tweede, lege database openen.
from conftest import TestingSessionLocal  # noqa: E402

GEHEIM = "x" * 40
HDR = {"X-Revocation-Breakglass": GEHEIM}
NU = lambda: datetime.now(timezone.utc)  # noqa: E731


@pytest.fixture(autouse=True)
def _schoon(monkeypatch):
    monkeypatch.setenv("REVOCATION_FRESHNESS_BUDGET", "60")
    monkeypatch.setenv("REVOCATION_HEARTBEAT_INTERVAL", "15")
    monkeypatch.setenv("REVOCATION_BREAKGLASS_SECRET", GEHEIM)
    monkeypatch.delenv("REVOCATION_REQUIRE_IAT_FROM", raising=False)
    monkeypatch.delenv("REVOCATION_TARGETS", raising=False)
    monkeypatch.setenv("SESSION_REVOCATION", "off")
    issuer._laatst_bekend = None
    issuer._nog_op_te_slaan.clear()
    issuer._stand_per_doel.clear()
    from app.auth import brute_force
    brute_force._attempts.clear()
    # De TestClient heeft geen IP-adres; de netwerkgrens zelf staat in stap 3.
    from app.routers import internal_revocation
    monkeypatch.setattr(internal_revocation, "intern_verzoek", lambda request: True)
    yield
    issuer._laatst_bekend = None
    issuer._nog_op_te_slaan.clear()


@pytest.fixture()
def aan(monkeypatch):
    monkeypatch.setenv("SESSION_REVOCATION", "on")


@pytest.fixture()
def keten(client, monkeypatch):
    """Laat de hartslag van de uitgever via de TestClient bij de eigen ontvanger
    aankomen. Geeft een functie die één hartslagronde draait."""
    monkeypatch.setenv("REVOCATION_TARGETS", "http://intern")
    geblokkeerd = {"aan": False}

    def _post(url, json=None, timeout=None):
        if geblokkeerd["aan"]:
            raise ConnectionError("geblokkeerd")
        pad = url.replace("http://intern", "")
        return client.post(pad, json=json)

    monkeypatch.setattr("httpx.post", _post)

    def ronde():
        return issuer.stuur_hartslag(TestingSessionLocal)

    ronde.blokkeer = lambda b=True: geblokkeerd.__setitem__("aan", b)
    return ronde


def _zoals_een_resource_app():
    """Wis de procesinterne blocklist van Datavalidatie. Die blokkeert hetzelfde
    token hier al; Uitvraag, Datastation en CRM hebben hem niet. Zo meten we
    uitsluitend het centrale mechanisme."""
    from app.auth import token_blocklist
    token_blocklist._blocklist.clear()


def _me(client, token):
    return client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})


def _stand():
    with TestingSessionLocal() as s:
        return s.query(RevocationState).filter(RevocationState.id == 1).first()


def _zet_gehoord(seconden_geleden):
    with TestingSessionLocal() as s:
        st = s.query(RevocationState).filter(RevocationState.id == 1).first()
        if st is None:
            st = RevocationState(id=1, grace_expiry_logged=False)
            s.add(st)
        st.last_heard_at = NU() - timedelta(seconds=seconden_geleden)
        s.commit()


# ── schema en persistentie ────────────────────────────────────────────────

def test_migratie_0006_volgt_op_0005_en_is_idempotent():
    import pathlib
    # Als tekst gelezen: de map backend/alembic overschaduwt het alembic-pakket.
    pad = pathlib.Path(__file__).parents[1] / "alembic/versions/0006_session_revocation.py"
    bron = pad.read_text()
    assert 'revision: str = "0006"' in bron
    assert 'down_revision: Union[str, None] = "0005"' in bron
    assert "ADD COLUMN IF NOT EXISTS logout_at" in bron
    assert "CREATE TABLE IF NOT EXISTS {tabel}" in bron
    for tabel in ("session_revocations", "revoked_sessions", "revocation_state"):
        assert tabel in bron


def test_logout_at_is_deferred_zodat_een_mislukte_migratie_inloggen_niet_breekt():
    from sqlalchemy import select
    sql = str(select(User).compile())
    assert "logout_at" not in sql


def test_startup_vangnet_bestaat_en_is_aangeroepen():
    import app.main as main
    assert callable(main._ensure_revocation_schema)
    bron = open(main.__file__).read()
    assert "\n_ensure_revocation_schema()\n" in bron


# ── logout schrijft de intrekking ─────────────────────────────────────────

def test_logout_legt_intrekking_en_logout_at_vast(client, user_org_user, token_org_user):
    jti = decode_access_token(token_org_user)["jti"]
    res = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token_org_user}"})
    assert res.status_code == 204
    with TestingSessionLocal() as s:
        rij = s.query(SessionRevocation).one()
        assert rij.sub == str(user_org_user.id) and rij.jti == jti
        assert rij.not_before is not None
        levensduur = rij.expires_at.replace(tzinfo=None) - rij.not_before.replace(tzinfo=None)
        assert levensduur >= timedelta(minutes=60), "intrekking moet de tokenlevensduur overleven"
        u = s.get(User, user_org_user.id)
        assert u.logout_at is not None


def test_get_logout_legt_ook_vast(client, user_org_user, token_org_user):
    res = client.get("/api/auth/logout", headers={"Authorization": f"Bearer {token_org_user}"},
                     follow_redirects=False)
    assert res.status_code == 303
    with TestingSessionLocal() as s:
        assert s.query(SessionRevocation).count() == 1


def test_logout_zonder_token_blijft_idempotent_en_schrijft_niets(client):
    assert client.post("/api/auth/logout").status_code == 204
    with TestingSessionLocal() as s:
        assert s.query(SessionRevocation).count() == 0


def test_logout_slaagt_ook_als_de_database_faalt(client, user_org_user, token_org_user, monkeypatch):
    from sqlalchemy.orm import Session as _S
    echt = _S.commit

    def _faal(self):
        if any(isinstance(o, SessionRevocation) for o in self.new):
            raise RuntimeError("db weg")
        return echt(self)
    monkeypatch.setattr(_S, "commit", _faal)
    res = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token_org_user}"})
    assert res.status_code == 204
    assert len(issuer._nog_op_te_slaan) == 1, "intrekking moet in de achterstand staan"


def test_logout_wekt_de_hartslag(client, user_org_user, token_org_user):
    issuer._wek.clear()
    client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token_org_user}"})
    assert issuer._wek.is_set()


# ── het lijstbericht en de push-authenticatie ─────────────────────────────

def test_lijstbericht_rondreis():
    claims = sr.lees_lijst(sr.teken_lijst({"generated_at": NU().isoformat(), "revocations": []}))
    assert claims["typ"] == sr.LIJST_TYP and claims["aud"] == sr.LIJST_AUD


def test_toegangstoken_is_geen_lijstbericht(token_org_user):
    with pytest.raises(ValueError):
        sr.lees_lijst(token_org_user)


def test_lijstbericht_is_geen_toegangstoken(client):
    bericht = sr.teken_lijst({"generated_at": NU().isoformat(), "revocations": []})
    assert _me(client, bericht).status_code == 401


def test_vervalst_lijstbericht_wordt_geweigerd(client):
    from jose import jwt
    nep = jwt.encode({"aud": sr.LIJST_AUD, "typ": sr.LIJST_TYP, "iss": "suresync-id",
                      "generated_at": NU().isoformat(), "revocations": [],
                      "exp": int(time.time()) + 60}, "ander-geheim", algorithm="HS256")
    assert client.post("/api/internal/revocations", json={"token": nep}).status_code == 401


def test_verlopen_lijstbericht_wordt_geweigerd(client, monkeypatch):
    from jose import jwt
    from app.auth import security
    oud = jwt.encode({"aud": sr.LIJST_AUD, "typ": sr.LIJST_TYP, "iss": security.ISSUER,
                      "generated_at": NU().isoformat(), "revocations": [],
                      "exp": int(time.time()) - 1}, security.SECRET_KEY, algorithm="HS256")
    assert client.post("/api/internal/revocations", json={"token": oud}).status_code == 401


def test_met_rs256_wordt_een_hs256_lijst_geweigerd(monkeypatch):
    """Algoritme volgt uit de configuratie, niet uit de header (alg-verwarring)."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from app.auth import security
    k = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv = k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                           serialization.NoEncryption()).decode()
    pub = k.public_key().public_bytes(serialization.Encoding.PEM,
                                      serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    hs = sr.teken_lijst({"generated_at": NU().isoformat(), "revocations": []})
    monkeypatch.setattr(security, "USE_RS256", True)
    monkeypatch.setattr(security, "PRIVATE_KEY", priv)
    monkeypatch.setattr(security, "PUBLIC_KEY", pub)
    rs = sr.teken_lijst({"generated_at": NU().isoformat(), "revocations": []})
    assert sr.lees_lijst(rs)["typ"] == sr.LIJST_TYP
    with pytest.raises(ValueError):
        sr.lees_lijst(hs)


def test_verouderde_lijst_wordt_niet_toegepast(client):
    nieuw = NU()
    oud = nieuw - timedelta(seconds=30)
    b1 = sr.teken_lijst({"generated_at": nieuw.isoformat(), "revocations": []})
    b2 = sr.teken_lijst({"generated_at": oud.isoformat(), "revocations": []})
    assert client.post("/api/internal/revocations", json={"token": b1}).status_code == 200
    assert client.post("/api/internal/revocations", json={"token": b2}).status_code == 409


def test_lijst_uit_de_toekomst_wordt_geweigerd(client):
    b = sr.teken_lijst({"generated_at": (NU() + timedelta(minutes=5)).isoformat(),
                        "revocations": []})
    assert client.post("/api/internal/revocations", json={"token": b}).status_code == 400


# ── criteria 1–3: normale werking ─────────────────────────────────────────

def test_1_2_uitloggen_maakt_hetzelfde_token_ongeldig_via_push(
        aan, keten, client, user_org_user, token_org_user):
    keten()
    assert _me(client, token_org_user).status_code == 200
    client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token_org_user}"})
    _zoals_een_resource_app()
    # De push is de door logout gewekte ronde; hier synchroon uitgevoerd.
    assert keten() == 1
    res = _me(client, token_org_user)
    assert res.status_code == 401 and res.json()["detail"] == "Sessie is ingetrokken"


def test_3_nieuwe_login_na_uitloggen_werkt_onmiddellijk(aan, keten, client, user_org_user):
    keten()
    login = lambda: client.post("/api/auth/login", json={  # noqa: E731
        "email": user_org_user.email, "password": "Correct-Password-123!"})
    oud = login().json()["access_token"]
    client.post("/api/auth/logout", headers={"Authorization": f"Bearer {oud}"})
    nieuw = login().json()["access_token"]
    keten()
    assert _me(client, oud).status_code == 401
    assert _me(client, nieuw).status_code == 200, "login in dezelfde seconde mag niet sneuvelen"


def test_3_andere_gebruiker_wordt_niet_geraakt(aan, keten, client, user_org_user,
                                               token_org_user, token_org_admin):
    client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token_org_user}"})
    keten()
    assert _me(client, token_org_admin).status_code == 200


# ── criteria 4–6: gemiste hartslagen ──────────────────────────────────────

def test_4_geblokkeerde_push_wordt_door_de_volgende_hartslag_hersteld(
        aan, keten, client, user_org_user, token_org_user):
    keten()
    keten.blokkeer()
    client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token_org_user}"})
    _zoals_een_resource_app()
    assert keten() == 0
    assert _me(client, token_org_user).status_code == 200, "push gemist: nog niet bekend"
    keten.blokkeer(False)
    keten()
    assert _me(client, token_org_user).status_code == 401


def test_5_drie_gemiste_hartslagen_weigeren_nog_niet(aan, client, token_org_user):
    _zet_gehoord(45)
    assert _me(client, token_org_user).status_code == 200


def test_6_na_het_budget_wordt_geweigerd(aan, client, token_org_user):
    _zet_gehoord(61)
    res = _me(client, token_org_user)
    assert res.status_code == 401 and res.json()["detail"] == "Intrekkingsstatus is niet actueel"


# ── criteria 7–9: langdurige storing ──────────────────────────────────────

def test_7_9_uitgever_weg_en_terug(aan, keten, client, token_org_user):
    _zet_gehoord(120)
    assert _me(client, token_org_user).status_code == 401
    keten()
    assert _me(client, token_org_user).status_code == 200


def test_hartslag_gaat_door_met_laatst_bekende_lijst_bij_databasestoring(keten, client):
    assert keten() == 1
    def kapot():
        raise RuntimeError("db weg")
    assert issuer.stuur_hartslag(kapot) == 1


def test_geen_hartslag_als_de_lijst_nooit_is_gelezen(keten):
    def kapot():
        raise RuntimeError("db weg")
    assert issuer.stuur_hartslag(kapot) == 0
    assert _stand() is None, "een lege lijst mag nooit als vers rondgaan"


def test_achterstand_wordt_alsnog_opgeslagen_en_meegestuurd(keten, user_org_user):
    nu = NU()
    issuer._nog_op_te_slaan.append(SimpleNamespace(
        jti="j1", sub=str(user_org_user.id), not_before=nu, expires_at=nu + timedelta(hours=1)))
    keten()
    assert not issuer._nog_op_te_slaan
    with TestingSessionLocal() as s:
        assert s.query(SessionRevocation).count() == 1
        assert s.query(RevokedSession).filter(RevokedSession.jti == "j1").count() == 1


# ── criteria 10–12: herstart ──────────────────────────────────────────────

def test_10_ingetrokken_token_blijft_401_na_herstart(aan, keten, client, user_org_user,
                                                     token_org_user):
    client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token_org_user}"})
    keten()
    # "Herstart": alle procesgeheugen weg, alleen de database blijft.
    issuer._laatst_bekend = None
    from app.auth import token_blocklist
    token_blocklist._blocklist.clear()
    assert _me(client, token_org_user).status_code == 401


def test_11_koude_start_zonder_hartslag_weigert(aan, client, token_org_user):
    assert _stand() is None
    assert _me(client, token_org_user).status_code == 401


def test_12_uitgever_herstart_levert_dezelfde_lijst(keten, client, user_org_user, token_org_user):
    client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token_org_user}"})
    voor = issuer.actuele_lijst(TestingSessionLocal)["revocations"]
    issuer._laatst_bekend = None
    na = issuer.actuele_lijst(TestingSessionLocal)["revocations"]
    assert voor == na and len(na) == 1


# ── criteria 13–16: noodprocedure ─────────────────────────────────────────

GELDIG = {"duur_minuten": 10, "reden": "Uitgever onbereikbaar, storing bij hosting",
          "uitgevoerd_door": "beheerder T1"}


def test_13_zonder_geheim_401_met_geheim_zonder_reden_400(client):
    assert client.post("/api/internal/revocation-grace", json=GELDIG).status_code == 401
    assert client.post("/api/internal/revocation-grace", json=GELDIG,
                       headers={"X-Revocation-Breakglass": "fout" * 10}).status_code == 401
    zonder = {k: v for k, v in GELDIG.items() if k != "reden"}
    assert client.post("/api/internal/revocation-grace", json=zonder, headers=HDR).status_code == 400
    kort = dict(GELDIG, reden="te kort")
    assert client.post("/api/internal/revocation-grace", json=kort, headers=HDR).status_code == 400


def test_13_duur_is_hard_begrensd(client):
    for duur in (0, 31, 600, "10", True):
        r = client.post("/api/internal/revocation-grace", json=dict(GELDIG, duur_minuten=duur),
                        headers=HDR)
        assert r.status_code == 400, duur


def test_13_niet_ingericht_geheim_sluit_de_nooduitgang(client, monkeypatch):
    monkeypatch.setenv("REVOCATION_BREAKGLASS_SECRET", "")
    assert client.post("/api/internal/revocation-grace", json=GELDIG, headers=HDR).status_code == 503
    monkeypatch.setenv("REVOCATION_BREAKGLASS_SECRET", "kort")
    assert client.post("/api/internal/revocation-grace", json=GELDIG,
                       headers={"X-Revocation-Breakglass": "kort"}).status_code == 503


def test_13_raden_wordt_begrensd(client):
    for _ in range(5):
        client.post("/api/internal/revocation-grace", json=GELDIG,
                    headers={"X-Revocation-Breakglass": "fout"})
    assert client.post("/api/internal/revocation-grace", json=GELDIG, headers=HDR).status_code == 429


def test_noodprocedure_laat_een_muf_beeld_door(aan, client, token_org_user):
    _zet_gehoord(600)
    assert _me(client, token_org_user).status_code == 401
    assert client.post("/api/internal/revocation-grace", json=GELDIG, headers=HDR).status_code == 200
    assert _me(client, token_org_user).status_code == 200


def test_14_tijdens_noodprocedure_blijft_ingetrokken_token_401(
        aan, keten, client, user_org_user, token_org_user, token_org_admin):
    client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token_org_user}"})
    keten()
    _zet_gehoord(600)
    client.post("/api/internal/revocation-grace", json=GELDIG, headers=HDR)
    assert _me(client, token_org_user).status_code == 401, "A/B mogen nooit versoepeld worden"
    assert _me(client, token_org_admin).status_code == 200


def test_15_noodprocedure_verloopt_vanzelf(aan, client, token_org_user):
    _zet_gehoord(600)
    client.post("/api/internal/revocation-grace", json=GELDIG, headers=HDR)
    with TestingSessionLocal() as s:
        st = s.get(RevocationState, 1)
        st.grace_until = NU() - timedelta(seconds=1)
        s.commit()
    assert _me(client, token_org_user).status_code == 401


def test_16_logging_en_status(aan, client, token_org_user, token_rhadix_admin, token_org_admin,
                              caplog):
    import logging
    caplog.set_level(logging.INFO, logger="rhadix.revocation")
    _zet_gehoord(600)
    client.post("/api/internal/revocation-grace", json=GELDIG, headers=HDR)
    assert any("NOODPROCEDURE GEACTIVEERD" in r.message for r in caplog.records)
    _me(client, token_org_user)
    assert any("noodprocedure actief" in r.message for r in caplog.records)

    st = client.get("/api/internal/revocation-status", headers=HDR).json()
    nood = st["noodprocedure"]
    assert nood["actief"] and nood["door"] == "beheerder T1" and nood["reden"] == GELDIG["reden"]
    assert nood["tot"]

    with TestingSessionLocal() as s:
        s.get(RevocationState, 1).grace_until = NU() - timedelta(seconds=1)
        s.commit()
    client.get("/api/internal/revocation-status", headers=HDR)
    assert any("noodprocedure verlopen" in r.message for r in caplog.records)


def test_status_autorisatie(client, token_rhadix_admin, token_org_admin):
    assert client.get("/api/internal/revocation-status").status_code == 401
    assert client.get("/api/internal/revocation-status",
                      headers={"Authorization": f"Bearer {token_org_admin}"}).status_code == 403
    r = client.get("/api/internal/revocation-status",
                   headers={"Authorization": f"Bearer {token_rhadix_admin}"})
    assert r.status_code == 200 and r.json()["session_revocation"] == "off"
    assert client.get("/api/internal/revocation-status",
                      headers={"X-Revocation-Breakglass": "fout"}).status_code == 401


# ── criteria 17–19: machine-to-machine ────────────────────────────────────

def test_17_19_machinetoken_wordt_nooit_getoetst():
    machine = {"sub": "client-1", "typ": "client", "scope": "external",
               "iat": int(time.time()) - 10, "jti": "m1"}

    class _Kapot:
        def query(self, *a, **k):
            raise AssertionError("machinetoken mag geen intrekkingsopzoeking doen")
    import os
    os.environ["SESSION_REVOCATION"] = "on"
    try:
        assert receiver.beoordeel(machine, _Kapot())          # muf, geen stand: toch door
    finally:
        os.environ["SESSION_REVOCATION"] = "off"


def test_18_logout_at_raakt_machineclient_van_dezelfde_tenant_niet(aan, keten, client,
                                                                   user_org_user, token_org_user):
    client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token_org_user}"})
    keten()
    with TestingSessionLocal() as s:
        machine = {"sub": str(user_org_user.id), "typ": "client", "iat": 1, "jti": "x"}
        assert receiver.beoordeel(machine, s)


# ── criteria 21–22: overgang ──────────────────────────────────────────────

def test_21_token_zonder_iat_voor_en_na_de_grens(aan, keten, client, user_org_user, monkeypatch):
    keten()
    zonder_iat = create_access_token({"sub": str(user_org_user.id)})
    from jose import jwt
    from app.auth import security
    claims = decode_access_token(zonder_iat)
    claims.pop("iat")
    tok = jwt.encode(claims, security.SECRET_KEY, algorithm="HS256")
    monkeypatch.setenv("REVOCATION_REQUIRE_IAT_FROM", (NU() + timedelta(hours=1)).isoformat())
    assert _me(client, tok).status_code == 200
    monkeypatch.setenv("REVOCATION_REQUIRE_IAT_FROM", (NU() - timedelta(seconds=1)).isoformat())
    assert _me(client, tok).status_code == 401


def test_22_uit_gedraagt_zich_als_vandaag_en_leest_niets(client, user_org_user, token_org_user):
    # Geen hartslag, geen stand, wel een intrekking: met "off" maakt het niets uit.
    with TestingSessionLocal() as s:
        s.add(RevokedSession(id=uuid.uuid4(), jti=decode_access_token(token_org_user)["jti"],
                             sub=str(user_org_user.id), not_before=NU(),
                             expires_at=NU() + timedelta(hours=1)))
        s.commit()
    assert _me(client, token_org_user).status_code == 200

    class _Kapot:
        def query(self, *a, **k):
            raise AssertionError("met SESSION_REVOCATION=off wordt niets gelezen")
    assert receiver.beoordeel(decode_access_token(token_org_user), _Kapot())


def test_onleesbare_stand_is_fail_closed(aan):
    class _Kapot:
        def query(self, *a, **k):
            raise RuntimeError("db weg")
    u = receiver.beoordeel({"sub": "x", "iat": int(time.time()), "jti": "j"}, _Kapot())
    assert not u and u.grondslag == "C"


def test_hartslag_start_niet_zonder_doelen():
    assert issuer.start() is False
