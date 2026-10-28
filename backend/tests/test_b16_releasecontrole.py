"""
test_b16_releasecontrole.py — afsluitende controle van de drie B-16-correcties
(B-28/B-31) onder herstart, uitval van de hartslag, vertraagde intrekking en
storingen. Alles met de echte uitgever- en ontvangercode; SESSION_REVOCATION
wordt alleen binnen de test aangezet.

Eisen:
  * een ingetrokken token wordt nooit opnieuw geldig (ook niet na herstart of een
    onvolledige/oudere lijst);
  * bij twijfel over de actualiteit: weigeren (fail-closed), en de noodprocedure
    versoepelt nooit een bekende intrekking;
  * een token van ná de intrekking blijft gewoon geldig (geen overblokkade).
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.auth.security import create_access_token, decode_access_token
from app.models.auth_models import User
from app.models.revocation_models import RevocationState, RevokedSession, SessionRevocation
from app.services import revocation_issuer as issuer
from app.services import revocation_receiver as ontvanger
from app.services import session_revocation as sr

from conftest import TestingSessionLocal  # noqa: E402

NU = lambda: datetime.now(timezone.utc)  # noqa: E731


@pytest.fixture(autouse=True)
def _aan(monkeypatch):
    monkeypatch.setenv("SESSION_REVOCATION", "on")
    monkeypatch.setenv("REVOCATION_FRESHNESS_BUDGET", "60")
    monkeypatch.delenv("REVOCATION_TARGETS", raising=False)
    monkeypatch.delenv("REVOCATION_APPLY_LOCALLY", raising=False)
    monkeypatch.delenv("REVOCATION_REQUIRE_IAT_FROM", raising=False)
    issuer._laatst_bekend = None
    issuer._nog_op_te_slaan.clear()
    yield
    issuer._laatst_bekend = None
    issuer._nog_op_te_slaan.clear()


def _token(sub, iat=None):
    """Claims zoals de uitgever ze maakt: exp = iat + levensduur (60 min)."""
    iat = int((iat or NU()).timestamp())
    return {"sub": str(sub), "jti": uuid.uuid4().hex, "iat": iat, "exp": iat + 3600}


def _lijst(rijen, gemaakt=None):
    gemaakt = gemaakt or NU()
    return {"generated_at": gemaakt.isoformat(), "revocations": [
        {"sub": str(s), "jti": j, "not_before": nb.isoformat(), "expires_at": (nb + timedelta(minutes=65)).isoformat()}
        for s, j, nb in rijen]}


def _beoordeel(payload, nu=None):
    with TestingSessionLocal() as db:
        return ontvanger.beoordeel(payload, db, nu=nu)


def _herstart_uitgever():
    """Een nieuw proces: niets in het geheugen, alleen wat in de database staat."""
    issuer._laatst_bekend = None
    issuer._nog_op_te_slaan.clear()


# ── herstart ─────────────────────────────────────────────────────────────────
def test_herstart_ontvanger_behoudt_intrekking():
    sub = uuid.uuid4()
    oud = _token(sub, iat=NU() - timedelta(minutes=5))
    with TestingSessionLocal() as db:
        ontvanger.ontvang(db, _lijst([(sub, None, NU() - timedelta(seconds=30))]))
    # "herstart": nieuwe sessie, niets in het geheugen; de lijst staat in de database
    u = _beoordeel(oud)
    assert not u.toegestaan and u.grondslag == "B"


def test_herstart_uitgever_verliest_geen_intrekking(user_org_user):
    with TestingSessionLocal() as db:
        issuer.registreer_intrekking(db, str(user_org_user.id), None, reden="password_reset_by_admin")
    _herstart_uitgever()
    lijst = issuer.actuele_lijst(TestingSessionLocal)
    assert lijst is not None and any(r["sub"] == str(user_org_user.id) for r in lijst["revocations"])


def test_herstart_uitgever_met_onleesbare_database_stuurt_geen_lege_lijst():
    """Na een herstart zonder leesbare database gaat er niets rond: een lege lijst met
    een verse hartslag zou anders bij de ontvangers alle intrekkingen wissen."""
    _herstart_uitgever()
    def kapot():
        raise RuntimeError("database weg")
    assert issuer.actuele_lijst(kapot) is None


def test_na_herstart_zonder_hartslag_fail_closed():
    """Ontvanger herstart, maar de uitgever is (nog) stil: niets wordt toegelaten."""
    with TestingSessionLocal() as db:
        ontvanger.ontvang(db, _lijst([], gemaakt=NU() - timedelta(minutes=10)), nu=NU())
    u = _beoordeel(_token(uuid.uuid4()))
    assert not u.toegestaan and u.grondslag == "C"


# ── uitval van de hartslag ───────────────────────────────────────────────────
def test_hartslag_valt_uit_fail_closed_na_budget():
    with TestingSessionLocal() as db:
        ontvanger.ontvang(db, _lijst([]))
    tok = _token(uuid.uuid4())
    assert _beoordeel(tok).toegestaan
    later = NU() + timedelta(seconds=90)
    u = _beoordeel(tok, nu=later)
    assert not u.toegestaan and u.grondslag == "C"


def test_noodprocedure_versoepelt_nooit_een_bekende_intrekking():
    sub = uuid.uuid4()
    with TestingSessionLocal() as db:
        ontvanger.ontvang(db, _lijst([(sub, None, NU() - timedelta(seconds=5))], gemaakt=NU() - timedelta(minutes=10)))
        ontvanger.activeer_noodmarge(db, 30, "releasecontrole: hartslag weg", "test")
    ingetrokken = _token(sub, iat=NU() - timedelta(minutes=1))
    ander = _token(uuid.uuid4())
    assert not _beoordeel(ingetrokken).toegestaan, "A/B gaan vóór de noodmarge"
    assert _beoordeel(ander).toegestaan, "alleen C wordt versoepeld"


def test_ontvanger_database_onleesbaar_fail_closed(monkeypatch):
    class Kapot:
        def query(self, *a, **k):
            raise RuntimeError("weg")
        def get(self, *a, **k):
            raise RuntimeError("weg")
    u = ontvanger.beoordeel(_token(uuid.uuid4()), Kapot())
    assert not u.toegestaan and u.grondslag == "C"


# ── vertraagde intrekking ────────────────────────────────────────────────────
def test_tokenvorm_in_deze_suite_is_realistisch():
    t = decode_access_token(create_access_token({"sub": "x"}))
    assert t["exp"] - t["iat"] == 3600 and _token("x")["exp"] - _token("x")["iat"] == 3600


def test_vertraagde_intrekking_bij_databasestoring(user_org_user):
    """De database van de uitgever valt weg tijdens de intrekking: de intrekking gaat
    toch mee in de hartslag, en wordt later opgeslagen zonder logout_at terug te zetten."""
    sub = str(user_org_user.id)
    with TestingSessionLocal() as db:
        issuer.actuele_lijst(TestingSessionLocal)          # uitgever kent de lijst

    class Kapot:
        def add(self, *a):
            raise RuntimeError("db weg")
        def rollback(self):
            pass
    tok = _token(sub, iat=NU() - timedelta(minutes=1))
    issuer.registreer_intrekking(Kapot(), sub, None, reden="user_deactivated")
    assert any(r.sub == sub for r in issuer._nog_op_te_slaan)

    # hartslag (lokaal) ondanks de storing: de ontvanger weigert het token al
    lijst = sr.bouw_lijst(list(issuer._laatst_bekend))
    with TestingSessionLocal() as db:
        ontvanger.ontvang(db, lijst)
    assert not _beoordeel(tok).toegestaan

    # intussen een nieuwere intrekking die wél is opgeslagen
    with TestingSessionLocal() as db:
        issuer.registreer_intrekking(db, sub, None, reden="password_changed")
        nieuwer = db.get(User, user_org_user.id).logout_at
    # database terug: de achterstand wordt opgeslagen, logout_at gaat niet terug
    issuer.actuele_lijst(TestingSessionLocal)
    assert not issuer._nog_op_te_slaan
    with TestingSessionLocal() as db:
        assert db.get(User, user_org_user.id).logout_at == nieuwer
        assert db.query(SessionRevocation).filter(SessionRevocation.sub == sub).count() == 2


def test_oudere_lijst_wordt_geweigerd_en_verandert_niets():
    sub = uuid.uuid4()
    nu = NU()
    with TestingSessionLocal() as db:
        ontvanger.ontvang(db, _lijst([(sub, None, nu - timedelta(seconds=5))], gemaakt=nu))
        with pytest.raises(ontvanger.Verouderd):
            ontvanger.ontvang(db, _lijst([], gemaakt=nu - timedelta(minutes=1)))
        assert db.query(RevokedSession).filter(RevokedSession.sub == str(sub)).count() == 1


def test_onvolledige_nieuwere_lijst_wist_geen_geldige_intrekking():
    sub = uuid.uuid4()
    nu = NU()
    tok = _token(sub, iat=nu - timedelta(minutes=2))
    with TestingSessionLocal() as db:
        ontvanger.ontvang(db, _lijst([(sub, None, nu - timedelta(seconds=5))], gemaakt=nu))
        ontvanger.ontvang(db, _lijst([], gemaakt=nu + timedelta(seconds=2)), nu=nu + timedelta(seconds=3))
    assert not _beoordeel(tok, nu=nu + timedelta(seconds=4)).toegestaan


# ── geen overblokkade, en de bewaartermijn ───────────────────────────────────
def test_token_van_na_de_intrekking_is_geldig():
    sub = uuid.uuid4()
    with TestingSessionLocal() as db:
        ontvanger.ontvang(db, _lijst([(sub, None, NU() - timedelta(minutes=1))]))
    assert _beoordeel(_token(sub)).toegestaan


def test_na_de_bewaartermijn_is_het_oude_token_al_verlopen():
    """Een intrekking verdwijnt pas na tokenlevensduur + marge; elk token van vóór de
    intrekking is dan al verlopen, en een langer levend token wordt sowieso geweigerd."""
    retentie = issuer._levensduur()
    assert retentie >= timedelta(seconds=sr.max_levensduur_seconden())
    iat = int(NU().timestamp())
    te_lang = {"sub": "x", "jti": "j", "iat": iat, "exp": iat + int(retentie.total_seconds()) + 120}
    u = sr.controleer(te_lang, ingetrokken_jtis=set(), logout_at_voor_sub=lambda s: None, laatst_gehoord=NU())
    assert not u.toegestaan
