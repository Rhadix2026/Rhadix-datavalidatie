"""
test_b31_beveiligingsregel.py — B-31: elke wijziging van een credential of
bevoegdheid wordt geaudit en trekt de bestaande sessies van dat subject in.

Plus de borging dat een ingetrokken token nooit opnieuw geldig wordt (B-16):
  * `logout_at` gaat alleen vooruit;
  * de ontvanger laat een nog geldige intrekking nooit vallen;
  * een token dat langer leeft dan de intrekking bewaard blijft, wordt geweigerd.

Met SESSION_REVOCATION=off (de huidige stand) verandert er voor gebruikers niets:
de intrekking wordt alleen vastgelegd.
"""
import json
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.auth.security import create_access_token, decode_access_token
from app.models.auth_models import User, UserRole
from app.models.revocation_models import RevocationState, RevokedSession, SessionRevocation
from app.services import revocation_issuer as issuer
from app.services import revocation_receiver as ontvanger
from app.services import session_revocation as sr

from conftest import TestingSessionLocal, make_token  # noqa: E402

NU = lambda: datetime.now(timezone.utc)  # noqa: E731


@pytest.fixture(autouse=True)
def _schoon(monkeypatch):
    monkeypatch.setenv("SESSION_REVOCATION", "off")
    monkeypatch.setenv("REVOCATION_FRESHNESS_BUDGET", "60")
    monkeypatch.delenv("REVOCATION_TARGETS", raising=False)
    monkeypatch.delenv("REVOCATION_APPLY_LOCALLY", raising=False)
    issuer._laatst_bekend = None
    issuer._nog_op_te_slaan.clear()
    from app.auth import brute_force, token_blocklist
    brute_force._attempts.clear()
    token_blocklist._blocklist.clear()
    yield
    issuer._laatst_bekend = None


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


def _intrekkingen(sub):
    with TestingSessionLocal() as s:
        return s.query(SessionRevocation).filter(SessionRevocation.sub == str(sub)).all()


def _audit(caplog, event):
    uit = []
    for r in caplog.records:
        if r.name != "rhadix.audit":
            continue
        try:
            d = json.loads(r.getMessage())
        except ValueError:
            continue
        if d.get("event") == event:
            uit.append(d)
    return uit


def _vers_beeld():
    """Laat de lokale ontvanger de actuele lijst van de uitgever toepassen."""
    import os
    os.environ["REVOCATION_APPLY_LOCALLY"] = "on"
    try:
        issuer.stuur_hartslag(TestingSessionLocal)
    finally:
        del os.environ["REVOCATION_APPLY_LOCALLY"]


# ── 1. Elke gebeurtenis: precies één auditregel én een intrekking ────────────
GEVALLEN = [
    ("admin reset", "post", "/api/admin/users/{id}/reset-password", {"new_password": "Nieuw-Wachtwoord-123!"},
     "token_rhadix_admin", "password_reset_by_admin", True),
    ("org reset", "post", "/api/org/users/{id}/reset-password", {"new_password": "Nieuw-Wachtwoord-123!"},
     "token_org_admin", "password_reset_by_admin", True),
    ("admin deactiveren", "patch", "/api/admin/users/{id}/deactivate", None,
     "token_rhadix_admin", "user_deactivated", True),
    ("org deactiveren", "patch", "/api/org/users/{id}/deactivate", None,
     "token_org_admin", "user_deactivated", True),
    ("admin rol", "patch", "/api/admin/users/{id}", {"role": "ORG_ADMIN"},
     "token_rhadix_admin", "role_changed", True),
    ("org verwijderen", "delete", "/api/org/users/{id}", None,
     "token_org_admin", "user_deleted", True),
]


@pytest.mark.parametrize("naam,methode,pad,body,beheerder,event,intrekking", GEVALLEN, ids=[g[0] for g in GEVALLEN])
def test_gebeurtenis_audit_en_intrekking(request, client, caplog, user_org_user,
                                        naam, methode, pad, body, beheerder, event, intrekking):
    tok_beheerder = request.getfixturevalue(beheerder)
    with caplog.at_level(logging.INFO, logger="rhadix.audit"):
        kw = {"headers": _h(tok_beheerder)}
        if body is not None:
            kw["json"] = body
        r = getattr(client, methode)(pad.format(id=user_org_user.id), **kw)
    assert r.status_code < 300, (naam, r.status_code, r.text)
    regels = _audit(caplog, event)
    assert len(regels) == 1, (naam, [x.get("event") for x in regels])
    assert regels[0]["user_id"] == str(user_org_user.id)
    assert regels[0]["door"] is not None and regels[0]["sessies_ingetrokken"] is intrekking
    assert len(_intrekkingen(user_org_user.id)) == (1 if intrekking else 0)


def test_heractiveren_audit_zonder_intrekking(client, caplog, user_org_user, token_rhadix_admin):
    client.patch(f"/api/admin/users/{user_org_user.id}/deactivate", headers=_h(token_rhadix_admin))
    with caplog.at_level(logging.INFO, logger="rhadix.audit"):
        r = client.patch(f"/api/admin/users/{user_org_user.id}/deactivate", headers=_h(token_rhadix_admin))
    assert r.json()["is_active"] is True
    assert len(_audit(caplog, "user_reactivated")) == 1
    assert len(_intrekkingen(user_org_user.id)) == 1, "alleen de deactivering trok in"


def test_rol_ongewijzigd_geen_intrekking(client, user_org_user, token_rhadix_admin):
    client.patch(f"/api/admin/users/{user_org_user.id}", headers=_h(token_rhadix_admin),
                 json={"role": "ORG_USER", "full_name": "Andere Naam"})
    assert _intrekkingen(user_org_user.id) == []


def test_tenant_deactiveren_trekt_alle_gebruikers_in(client, user_org_user, user_org_admin,
                                                    token_tenant_b, user_tenant_b, db):
    # beheerder in een andere tenant, zodat hij zijn eigen organisatie niet raakt
    user_tenant_b.role = UserRole.RHADIX_ADMIN
    db.commit()
    tok = make_token(user_tenant_b)
    r = client.patch(f"/api/admin/tenants/{user_org_user.tenant_id}/deactivate", headers=_h(tok),
                     json={"is_active": False})
    assert r.status_code == 200, r.text
    assert len(_intrekkingen(user_org_user.id)) == 1 and len(_intrekkingen(user_org_admin.id)) == 1


# ── 2. Zelf wijzigen: nieuw token, niet buitengesloten ───────────────────────
def test_eigen_wachtwoord_wijzigen_geeft_nieuw_token(client, caplog, user_org_user, token_org_user):
    with caplog.at_level(logging.INFO, logger="rhadix.audit"):
        r = client.patch("/api/auth/me/password", headers=_h(token_org_user),
                         json={"current_password": "Correct-Password-123!", "new_password": "Nieuw-Wachtwoord-123!"})
    assert r.status_code == 200, r.text
    nieuw = r.json()["access_token"]
    assert len(_audit(caplog, "password_changed")) == 1
    [rij] = _intrekkingen(user_org_user.id)
    oud_iat = decode_access_token(token_org_user)["iat"]
    nieuw_iat = decode_access_token(nieuw)["iat"]
    grens = int(rij.not_before.replace(tzinfo=timezone.utc).timestamp())
    assert oud_iat <= grens < nieuw_iat, "oud token valt onder de intrekking, het nieuwe niet"


def test_met_controle_aan_oud_token_weg_nieuw_token_werkt(monkeypatch, client, user_org_user, token_org_user):
    monkeypatch.setenv("SESSION_REVOCATION", "on")
    _vers_beeld()
    r = client.patch("/api/auth/me/password", headers=_h(token_org_user),
                     json={"current_password": "Correct-Password-123!", "new_password": "Nieuw-Wachtwoord-123!"})
    nieuw = r.json()["access_token"]
    from app.auth import token_blocklist
    token_blocklist._blocklist.clear()
    _vers_beeld()
    assert client.get("/api/auth/me", headers=_h(token_org_user)).status_code == 401
    assert client.get("/api/auth/me", headers=_h(nieuw)).status_code == 200


def test_met_controle_uit_niemand_buitengesloten(client, user_org_user, token_org_user, token_rhadix_admin):
    """De huidige stand: na een reset werkt het oude token nog (alleen vastgelegd)."""
    client.post(f"/api/admin/users/{user_org_user.id}/reset-password", headers=_h(token_rhadix_admin),
                json={"new_password": "Nieuw-Wachtwoord-123!"})
    assert len(_intrekkingen(user_org_user.id)) == 1
    assert client.get("/api/auth/me", headers=_h(token_org_user)).status_code == 200


def test_reset_door_beheerder_met_controle_aan(monkeypatch, client, user_org_user, token_org_user,
                                              token_rhadix_admin):
    monkeypatch.setenv("SESSION_REVOCATION", "on")
    _vers_beeld()
    client.post(f"/api/admin/users/{user_org_user.id}/reset-password", headers=_h(token_rhadix_admin),
                json={"new_password": "Nieuw-Wachtwoord-123!"})
    _vers_beeld()
    assert client.get("/api/auth/me", headers=_h(token_org_user)).status_code == 401
    assert client.get("/api/auth/me", headers=_h(token_rhadix_admin)).status_code == 200, \
        "de beheerder zelf blijft ingelogd"


# ── 3. Nooit opnieuw geldig ───────────────────────────────────────────────────
def test_logout_at_gaat_alleen_vooruit(db, user_org_user):
    later = NU()
    issuer._zet_logout_at(db, str(user_org_user.id), later); db.commit()
    issuer._zet_logout_at(db, str(user_org_user.id), later - timedelta(minutes=10)); db.commit()
    db.expire_all()
    opgeslagen = db.get(User, user_org_user.id).logout_at
    assert opgeslagen.replace(tzinfo=timezone.utc) == later.replace(microsecond=opgeslagen.microsecond) or \
        abs((opgeslagen.replace(tzinfo=timezone.utc) - later).total_seconds()) < 1


def test_ontvanger_laat_geldige_intrekking_niet_vallen(db):
    sub = str(uuid.uuid4())
    nu = NU()
    lijst1 = {"generated_at": nu.isoformat(), "revocations": [
        {"sub": sub, "jti": None, "not_before": nu.isoformat(), "expires_at": (nu + timedelta(hours=1)).isoformat()}]}
    ontvanger.ontvang(db, lijst1)
    # de uitgever stuurt (bijv. na een herstelde back-up) een lijst zonder deze intrekking
    lijst2 = {"generated_at": (nu + timedelta(seconds=5)).isoformat(), "revocations": []}
    ontvanger.ontvang(db, lijst2, nu=nu + timedelta(seconds=6))
    rijen = db.query(RevokedSession).filter(RevokedSession.sub == sub).all()
    assert len(rijen) == 1, "een ingetrokken token mag niet opnieuw geldig worden"


def test_verlopen_intrekking_mag_wel_vervallen(db):
    sub = str(uuid.uuid4())
    nu = NU()
    ontvanger.ontvang(db, {"generated_at": nu.isoformat(), "revocations": [
        {"sub": sub, "jti": None, "not_before": nu.isoformat(), "expires_at": (nu + timedelta(minutes=1)).isoformat()}]})
    later = nu + timedelta(minutes=2)
    ontvanger.ontvang(db, {"generated_at": later.isoformat(), "revocations": []}, nu=later)
    assert db.query(RevokedSession).filter(RevokedSession.sub == sub).count() == 0


def test_te_lang_levend_token_geweigerd(monkeypatch):
    monkeypatch.setenv("SESSION_REVOCATION", "on")
    nu = int(time.time())
    claims = {"sub": "x", "jti": "j", "iat": nu, "exp": nu + 3 * 3600}
    u = sr.controleer(claims, ingetrokken_jtis=set(), logout_at_voor_sub=lambda s: None,
                      laatst_gehoord=NU())
    assert not u.toegestaan and u.grondslag == "B"
    claims["exp"] = nu + 3600
    assert sr.controleer(claims, ingetrokken_jtis=set(), logout_at_voor_sub=lambda s: None,
                         laatst_gehoord=NU()).toegestaan


def test_machinetoken_typ_machine_valt_wel_onder_de_controle():
    assert ontvanger._is_machine({"typ": "client"}) is True
    assert ontvanger._is_machine({"typ": "machine", "aud": "datastation-staging"}) is False


def test_storing_bij_vastleggen_gaat_mee_in_hartslag(db, user_org_user, monkeypatch):
    """Faalt de database, dan gaat de handeling door en volgt de intrekking later."""
    issuer._laatst_bekend = []

    class Kapot:
        def add(self, *a): raise RuntimeError("db weg")
        def rollback(self): pass
    issuer.registreer_intrekking(Kapot(), str(user_org_user.id), None, reden="password_reset_by_admin")
    assert any(r.sub == str(user_org_user.id) for r in issuer._laatst_bekend)
    assert any(r.sub == str(user_org_user.id) for r in issuer._nog_op_te_slaan)
