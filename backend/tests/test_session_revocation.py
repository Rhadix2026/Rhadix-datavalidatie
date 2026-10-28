"""
test_session_revocation.py — B-16 stap 1 en 2.

De belangrijkste test staat onder "noodprocedure": tijdens de noodprocedure
blijft een bekend ingetrokken token geweigerd. Dat is acceptatiecriterium 14 en
de reden dat de drie controles strikt gescheiden zijn.
"""
import os
from datetime import datetime, timedelta, timezone

import pytest

from app.auth.security import create_access_token, decode_access_token
from app.services import session_revocation as sr

NU = datetime(2026, 10, 28, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def _aan(monkeypatch):
    monkeypatch.setenv("SESSION_REVOCATION", "on")
    monkeypatch.setenv("REVOCATION_FRESHNESS_BUDGET", "60")
    monkeypatch.delenv("REVOCATION_REQUIRE_IAT_FROM", raising=False)


def _claims(**extra):
    basis = {"sub": "11111111-1111-1111-1111-111111111111",
             "iat": int((NU - timedelta(minutes=5)).timestamp()),
             "jti": "aaaa"}
    basis.update(extra)
    return basis


def _controleer(claims, *, jtis=(), logout_at=None, gehoord_sec=5, nood=None):
    return sr.controleer(
        claims,
        ingetrokken_jtis=set(jtis),
        logout_at_voor_sub=lambda s: logout_at,
        laatst_gehoord=None if gehoord_sec is None else NU - timedelta(seconds=gehoord_sec),
        noodmarge_tot=nood,
        nu=NU,
    )


# ── stap 1: iat en jti in het token ───────────────────────────────────────

def test_token_draagt_iat_en_jti():
    claims = decode_access_token(create_access_token({"sub": "x"}))
    assert isinstance(claims["iat"], int)
    assert claims["jti"] and len(claims["jti"]) == 32
    assert claims["iat"] < claims["exp"]


def test_jti_is_per_token_uniek():
    a = decode_access_token(create_access_token({"sub": "x"}))["jti"]
    b = decode_access_token(create_access_token({"sub": "x"}))["jti"]
    assert a != b


def test_meegegeven_claims_worden_niet_overschreven():
    """Machine-tokens of tests die zelf iat/jti zetten houden die."""
    claims = decode_access_token(create_access_token({"sub": "x", "jti": "eigen", "iat": 1}))
    assert claims["jti"] == "eigen" and claims["iat"] == 1


# ── controle A: dit token is ingetrokken ──────────────────────────────────

def test_A_ingetrokken_jti_wordt_geweigerd():
    u = _controleer(_claims(), jtis=["aaaa"])
    assert not u and u.grondslag == "A"


def test_A_ander_jti_mag_door():
    assert _controleer(_claims(), jtis=["bbbb"])


# ── controle B: alle sessies van vóór het uitlogmoment ───────────────────

def test_B_token_van_voor_het_uitloggen_wordt_geweigerd():
    u = _controleer(_claims(), logout_at=NU - timedelta(minutes=1))
    assert not u and u.grondslag == "B"


def test_B_token_van_na_het_uitloggen_mag_door():
    """Criterium 3: opnieuw inloggen werkt onmiddellijk."""
    assert _controleer(_claims(iat=int((NU - timedelta(seconds=10)).timestamp())),
                       logout_at=NU - timedelta(minutes=1))


def test_B_gelijktijdig_uitgegeven_token_telt_als_ingetrokken():
    moment = NU - timedelta(minutes=2)
    u = _controleer(_claims(iat=int(moment.timestamp())), logout_at=moment)
    assert not u and u.grondslag == "B"


def test_B_nooit_uitgelogd_mag_door():
    assert _controleer(_claims(), logout_at=None)


# ── de overgang: tokens zonder iat ───────────────────────────────────────

def test_token_zonder_iat_mag_door_voor_de_grens(monkeypatch):
    monkeypatch.setenv("REVOCATION_REQUIRE_IAT_FROM", (NU + timedelta(hours=1)).isoformat())
    claims = _claims(); del claims["iat"]
    assert _controleer(claims)


def test_token_zonder_iat_wordt_geweigerd_na_de_grens(monkeypatch):
    monkeypatch.setenv("REVOCATION_REQUIRE_IAT_FROM", (NU - timedelta(minutes=1)).isoformat())
    claims = _claims(); del claims["iat"]
    u = _controleer(claims)
    assert not u and u.grondslag == "B"


def test_onleesbare_grens_wordt_als_niet_gezet_behandeld(monkeypatch):
    monkeypatch.setenv("REVOCATION_REQUIRE_IAT_FROM", "geen-datum")
    claims = _claims(); del claims["iat"]
    assert _controleer(claims)


# ── controle C: actualiteit ───────────────────────────────────────────────

def test_C_vers_beeld_mag_door():
    assert _controleer(_claims(), gehoord_sec=45)      # criterium 5


def test_C_muf_beeld_wordt_geweigerd():
    u = _controleer(_claims(), gehoord_sec=61)         # criterium 6
    assert not u and u.grondslag == "C"


def test_C_koude_start_weigert():
    """Criterium 11: nog nooit een hartslag gehoord -> niet voor vers houden."""
    u = _controleer(_claims(), gehoord_sec=None)
    assert not u and u.grondslag == "C"


# ── noodprocedure ────────────────────────────────────────────────────────

def test_noodprocedure_versoepelt_alleen_de_actualiteit():
    nood = NU + timedelta(minutes=10)
    assert _controleer(_claims(), gehoord_sec=600, nood=nood)


def test_noodprocedure_laat_een_ingetrokken_jti_NIET_door():
    """Acceptatiecriterium 14 — de kern van voorwaarde 2."""
    nood = NU + timedelta(minutes=10)
    u = _controleer(_claims(), jtis=["aaaa"], gehoord_sec=600, nood=nood)
    assert not u and u.grondslag == "A"


def test_noodprocedure_laat_een_uitgelogde_sessie_NIET_door():
    nood = NU + timedelta(minutes=10)
    u = _controleer(_claims(), logout_at=NU - timedelta(minutes=1), gehoord_sec=600, nood=nood)
    assert not u and u.grondslag == "B"


def test_verlopen_noodprocedure_weigert_weer():
    """Criterium 15: automatische beëindiging."""
    u = _controleer(_claims(), gehoord_sec=600, nood=NU - timedelta(seconds=1))
    assert not u and u.grondslag == "C"


def test_noodduur_is_hard_begrensd():
    assert sr.MAX_NOODDUUR_MINUTEN == 30


# ── uitgeschakeld = gedrag als vandaag ───────────────────────────────────

def test_uit_laat_alles_door(monkeypatch):
    """Criterium 22: met SESSION_REVOCATION=off exact gedrag als vandaag."""
    monkeypatch.setenv("SESSION_REVOCATION", "off")
    assert _controleer(_claims(), jtis=["aaaa"], logout_at=NU, gehoord_sec=None)


# ── de hartslaglijst ─────────────────────────────────────────────────────

class _Rij:
    def __init__(self, jti, sub, not_before, expires_at):
        self.jti, self.sub, self.not_before, self.expires_at = jti, sub, not_before, expires_at


def test_lijst_bevat_de_volledige_actuele_stand():
    nu = datetime.now(timezone.utc)
    rijen = [_Rij("a", "s1", nu, nu + timedelta(minutes=30)),
             _Rij("b", "s2", nu, nu + timedelta(minutes=10))]
    d = sr.bouw_lijst(rijen)
    assert {r["jti"] for r in d["revocations"]} == {"a", "b"}
    assert d["generated_at"]


def test_lijst_laat_verlopen_intrekkingen_weg():
    nu = datetime.now(timezone.utc)
    rijen = [_Rij("oud", "s1", nu - timedelta(hours=2), nu - timedelta(hours=1)),
             _Rij("nieuw", "s2", nu, nu + timedelta(minutes=30))]
    d = sr.bouw_lijst(rijen)
    assert [r["jti"] for r in d["revocations"]] == ["nieuw"]


def test_lijst_is_leeg_zonder_intrekkingen():
    assert sr.bouw_lijst([])["revocations"] == []
