"""
B-26 — client-IP uitsluitend via de vertrouwde proxyketen, en de uurlimiet op login.

Unit: client_ip() op losse verzoeken met een gekozen bronadres en koppen.
Integratie: /api/auth/login achter een ASGI-omhulsel dat het bronadres zet,
zodat de keten Cloudflare → nginx → backend na te bootsen is.
"""
import json
import logging

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.auth import brute_force, client_ip as cip
from app.database import get_db
from conftest import override_get_db

GATEWAY = "172.20.0.1"          # host-nginx zoals de backend hem ziet
FRONTEND = "172.20.0.5"         # andere container op hetzelfde netwerk
CF_RAND = "172.70.1.1"          # Cloudflare (172.64.0.0/13)
CF_RAND6 = "2606:4700:10::1"    # Cloudflare IPv6
WW = "Correct-Password-123!"


@pytest.fixture(autouse=True)
def _keten(monkeypatch):
    monkeypatch.setenv("TRUSTED_PROXY_NETWORKS", f"127.0.0.0/8,::1/128,{GATEWAY}/32")
    monkeypatch.delenv("CLOUDFLARE_NETWORKS", raising=False)
    monkeypatch.delenv("LOGIN_RATE_LIMIT_PER_HOUR", raising=False)
    cip._vertrouwde_proxys.cache_clear()
    cip._cloudflare.cache_clear()
    yield
    cip._vertrouwde_proxys.cache_clear()
    cip._cloudflare.cache_clear()


def _req(bron, **koppen):
    headers = [(k.replace("_", "-").lower().encode(), v.encode()) for k, v in koppen.items()]
    return Request({"type": "http", "method": "POST", "path": "/", "headers": headers,
                    "client": (bron, 50000) if bron else None})


# ── unit: de keten ─────────────────────────────────────────────────────────

def test_via_cloudflare_telt_cf_connecting_ip_en_nooit_xff():
    r = _req(GATEWAY, x_real_ip=CF_RAND, cf_connecting_ip="203.0.113.5",
             x_forwarded_for="198.51.100.7, 203.0.113.5")
    assert cip.client_ip(r) == "203.0.113.5"


def test_xff_alleen_telt_niet():
    assert cip.client_ip(_req(GATEWAY, x_forwarded_for="198.51.100.7")) == GATEWAY


def test_om_cloudflare_heen_telt_x_real_ip_niet_de_vervalste_cf_kop():
    r = _req(GATEWAY, x_real_ip="203.0.113.9", cf_connecting_ip="198.51.100.1",
             x_forwarded_for="198.51.100.2")
    assert cip.client_ip(r) == "203.0.113.9"


@pytest.mark.parametrize("bron", [FRONTEND, "203.0.113.50", "2001:db8::50"])
def test_onvertrouwde_bron_negeert_alle_koppen(bron):
    r = _req(bron, x_real_ip=CF_RAND, cf_connecting_ip="198.51.100.1", x_forwarded_for="198.51.100.2")
    assert cip.client_ip(r) == bron


def test_ipv6_via_cloudflare():
    r = _req(GATEWAY, x_real_ip=CF_RAND6, cf_connecting_ip="2001:db8:1:2::abcd")
    assert cip.client_ip(r) == "2001:db8:1:2::abcd"


def test_ipv6_rechtstreeks_telt_x_real_ip():
    r = _req(GATEWAY, x_real_ip="2001:db8:9::1", cf_connecting_ip="198.51.100.1")
    assert cip.client_ip(r) == "2001:db8:9::1"


def test_ipv6_bron_vertrouwd_via_loopback():
    r = _req("::1", x_real_ip="203.0.113.9")
    assert cip.client_ip(r) == "203.0.113.9"


def test_ipv4_in_ipv6_vorm_wordt_ipv4():
    assert cip.client_ip(_req(GATEWAY, x_real_ip="::ffff:203.0.113.9")) == "203.0.113.9"
    assert cip.client_ip(_req("::ffff:172.20.0.1", x_real_ip="203.0.113.9")) == "203.0.113.9"


@pytest.mark.parametrize("koppen,verwacht", [
    ({"x_real_ip": "rommel"}, GATEWAY),
    ({"x_real_ip": "203.0.113.9, 198.51.100.1"}, GATEWAY),
    ({"x_real_ip": ""}, GATEWAY),
    ({"x_real_ip": CF_RAND, "cf_connecting_ip": "rommel"}, CF_RAND),
    ({"x_real_ip": CF_RAND, "cf_connecting_ip": "1.2.3.4, 5.6.7.8"}, CF_RAND),
    ({"x_real_ip": CF_RAND}, CF_RAND),
])
def test_ongeldige_koppen_vallen_terug_zonder_fout(koppen, verwacht):
    assert cip.client_ip(_req(GATEWAY, **koppen)) == verwacht


def test_zonder_bronadres_of_met_naam():
    assert cip.client_ip(_req(None)) == "unknown"
    assert cip.client_ip(_req("testclient", x_real_ip="203.0.113.9")) == "testclient"


def test_standaard_vertrouwt_loopback_en_de_eigen_gateway(monkeypatch):
    monkeypatch.setenv("TRUSTED_PROXY_NETWORKS", "")
    monkeypatch.setattr(cip, "standaard_gateway", lambda: GATEWAY)
    cip._vertrouwde_proxys.cache_clear()
    assert cip.client_ip(_req(GATEWAY, x_real_ip="203.0.113.9")) == "203.0.113.9"
    assert cip.client_ip(_req("127.0.0.1", x_real_ip="203.0.113.9")) == "203.0.113.9"
    # een andere container op hetzelfde netwerk is géén proxy
    assert cip.client_ip(_req(FRONTEND, x_real_ip="203.0.113.9")) == FRONTEND


def test_standaard_zonder_gateway_alleen_loopback(monkeypatch):
    monkeypatch.setenv("TRUSTED_PROXY_NETWORKS", "")
    monkeypatch.setattr(cip, "standaard_gateway", lambda: None)
    cip._vertrouwde_proxys.cache_clear()
    assert cip.client_ip(_req(GATEWAY, x_real_ip="203.0.113.9")) == GATEWAY


def test_gateway_uit_de_routetabel():
    tabel = ("Iface\tDestination\tGateway \tFlags\tRefCnt\tUse\tMetric\tMask\n"
             "eth0\t00000000\t010014AC\t0003\t0\t0\t0\t00000000\n"
             "eth0\t000014AC\t00000000\t0001\t0\t0\t0\t0000FFFF\n")
    assert cip.standaard_gateway(tabel) == "172.20.0.1"
    assert cip.standaard_gateway("Iface\tDestination\tGateway\n") is None


def test_cloudflare_lijst_is_te_overschrijven(monkeypatch):
    monkeypatch.setenv("CLOUDFLARE_NETWORKS", "198.18.0.0/15")
    cip._cloudflare.cache_clear()
    assert cip.client_ip(_req(GATEWAY, x_real_ip="198.18.0.1", cf_connecting_ip="203.0.113.5")) == "203.0.113.5"
    # het echte Cloudflare-adres telt dan niet meer als Cloudflare
    assert cip.client_ip(_req(GATEWAY, x_real_ip=CF_RAND, cf_connecting_ip="203.0.113.5")) == CF_RAND


def test_ongeldige_netwerken_in_de_configuratie_worden_overgeslagen(monkeypatch, caplog):
    monkeypatch.setenv("TRUSTED_PROXY_NETWORKS", f"geen-net,{GATEWAY}/32")
    cip._vertrouwde_proxys.cache_clear()
    with caplog.at_level(logging.ERROR, logger="rhadix.client_ip"):
        assert cip.client_ip(_req(GATEWAY, x_real_ip="203.0.113.9")) == "203.0.113.9"
    assert "geen-net" in caplog.text


def test_limietsleutel_ipv4_en_ipv6_per_64():
    assert cip.limiet_sleutel("203.0.113.5") == "203.0.113.5"
    assert cip.limiet_sleutel("2001:db8:1:2::abcd") == "2001:db8:1:2::/64"
    assert cip.limiet_sleutel("2001:db8:1:2:ffff::1") == "2001:db8:1:2::/64"
    assert cip.limiet_sleutel("testclient") == "testclient"


# ── unit: de uurlimiet ─────────────────────────────────────────────────────

@pytest.mark.parametrize("waarde,verwacht", [(None, 96), ("", 96), ("10", 10), ("0", 0), ("-1", -1), ("veel", 96)])
def test_uurlimiet_configuratie(monkeypatch, waarde, verwacht):
    if waarde is None:
        monkeypatch.delenv("LOGIN_RATE_LIMIT_PER_HOUR", raising=False)
    else:
        monkeypatch.setenv("LOGIN_RATE_LIMIT_PER_HOUR", waarde)
    assert brute_force.uurlimiet() == verwacht


def test_uurlimiet_telt_per_sleutel_en_vervalt_na_een_uur(monkeypatch):
    monkeypatch.setenv("LOGIN_RATE_LIMIT_PER_HOUR", "3")
    nu = [1_000_000.0]
    monkeypatch.setattr(brute_force.time, "time", lambda: nu[0])
    assert [brute_force.verzoek_toegestaan("a")[0] for _ in range(3)] == [True] * 3
    ok, wacht = brute_force.verzoek_toegestaan("a")
    assert not ok and wacht == 3601
    assert brute_force.verzoek_toegestaan("b") == (True, 0)
    nu[0] += 1800
    assert brute_force.verzoek_toegestaan("a") == (False, 1801)   # geweigerd telt niet mee
    nu[0] += 1800
    assert brute_force.verzoek_toegestaan("a") == (True, 0)


def test_uurlimiet_nul_is_uit(monkeypatch):
    monkeypatch.setenv("LOGIN_RATE_LIMIT_PER_HOUR", "0")
    assert all(brute_force.verzoek_toegestaan("a") == (True, 0) for _ in range(200))


def test_uurtabel_wordt_opgeschoond(monkeypatch):
    monkeypatch.setattr(brute_force, "MAX_SLEUTELS", 5)
    nu = [1_000_000.0]
    monkeypatch.setattr(brute_force.time, "time", lambda: nu[0])
    for i in range(6):
        brute_force.verzoek_toegestaan(f"oud-{i}")
    nu[0] += 3601
    brute_force.verzoek_toegestaan("nieuw")
    assert set(brute_force._verzoeken) == {"nieuw"}


# ── integratie: /api/auth/login achter de nagebootste keten ────────────────

def _met_bron(app, bron):
    async def omhulsel(scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            scope = dict(scope, client=(bron, 50000))
        await app(scope, receive, send)
    return omhulsel


@pytest.fixture()
def via():
    """via(bron) → TestClient waarvan elk verzoek van `bron` lijkt te komen."""
    import app.main as main_module
    main_module.app.dependency_overrides[get_db] = override_get_db
    clients = []

    def maak(bron=GATEWAY):
        c = TestClient(_met_bron(main_module.app, bron), raise_server_exceptions=True)
        clients.append(c)
        return c
    yield maak
    main_module.app.dependency_overrides.clear()


def _login(c, email, ww, **koppen):
    hdr = {k.replace("_", "-"): v for k, v in koppen.items()}
    return c.post("/api/auth/login", json={"email": email, "password": ww}, headers=hdr)


def test_m1_wisselende_xff_via_cloudflare_omzeilt_de_blokkade_niet(via, user_org_user):
    c = via()
    for i in range(5):
        r = _login(c, user_org_user.email, "fout", x_real_ip=CF_RAND, cf_connecting_ip="203.0.113.5",
                   x_forwarded_for=f"198.51.100.{i}")
        assert r.status_code == 401
    r = _login(c, user_org_user.email, WW, x_real_ip=CF_RAND, cf_connecting_ip="203.0.113.5",
               x_forwarded_for="198.51.100.99")
    assert r.status_code == 429


def test_m3_om_cloudflare_heen_met_wisselende_cf_kop(via, user_org_user):
    c = via()
    for i in range(5):
        assert _login(c, user_org_user.email, "fout", x_real_ip="203.0.113.9",
                      cf_connecting_ip=f"198.51.100.{i}", x_forwarded_for=f"192.0.2.{i}").status_code == 401
    assert _login(c, user_org_user.email, WW, x_real_ip="203.0.113.9",
                  cf_connecting_ip="198.51.100.200").status_code == 429


def test_m5_rechtstreeks_op_de_backend_met_vervalste_koppen(via, user_org_user):
    c = via("203.0.113.77")
    for i in range(5):
        assert _login(c, user_org_user.email, "fout", x_real_ip=f"198.51.100.{i}",
                      cf_connecting_ip=f"192.0.2.{i}", x_forwarded_for=f"192.0.2.{i}").status_code == 401
    assert _login(c, user_org_user.email, WW, x_real_ip="198.51.100.250").status_code == 429


def test_m6_normale_gebruiker_elders_blijft_ongemoeid(via, user_org_user, user_tenant_b):
    c = via()
    for _ in range(5):
        _login(c, user_org_user.email, "fout", x_real_ip=CF_RAND, cf_connecting_ip="203.0.113.5")
    assert _login(c, user_org_user.email, WW, x_real_ip=CF_RAND, cf_connecting_ip="203.0.113.5").status_code == 429
    # een andere bezoeker achter dezelfde Cloudflare-rand
    r = _login(c, user_tenant_b.email, "Tenant-B-Pass-123!", x_real_ip=CF_RAND, cf_connecting_ip="203.0.113.6")
    assert r.status_code == 200 and r.json()["access_token"]
    # en dezelfde gebruiker vanaf een ander adres
    assert _login(c, user_org_user.email, WW, x_real_ip=CF_RAND, cf_connecting_ip="203.0.113.7").status_code == 200


def test_ipv6_blokkade_per_64(via, user_org_user):
    c = via()
    for i in range(1, 6):
        assert _login(c, user_org_user.email, "fout", x_real_ip=CF_RAND6,
                      cf_connecting_ip=f"2001:db8:1:2::{i:x}").status_code == 401
    # ander adres in hetzelfde /64: geblokkeerd
    assert _login(c, user_org_user.email, WW, x_real_ip=CF_RAND6,
                  cf_connecting_ip="2001:db8:1:2:ffff::9").status_code == 429
    # ander /64: niet geblokkeerd
    assert _login(c, user_org_user.email, WW, x_real_ip=CF_RAND6,
                  cf_connecting_ip="2001:db8:1:3::1").status_code == 200


@pytest.fixture()
def snel_wachtwoord(monkeypatch):
    """bcrypt kost ± 0,25 s per poging; voor tellertests volstaat een vergelijking."""
    import app.auth.router as router
    monkeypatch.setattr(router, "verify_password", lambda ww, _h: ww == WW)


def test_uurlimiet_telt_ook_geslaagde_logins(via, user_org_user, monkeypatch, snel_wachtwoord):
    monkeypatch.setenv("LOGIN_RATE_LIMIT_PER_HOUR", "3")
    c = via()
    hdr = {"x_real_ip": CF_RAND, "cf_connecting_ip": "203.0.113.5"}
    assert [_login(c, user_org_user.email, WW, **hdr).status_code for _ in range(3)] == [200] * 3
    r = _login(c, user_org_user.email, WW, **hdr)
    assert r.status_code == 429 and int(r.headers["Retry-After"]) > 3500
    assert "Too many login attempts" in r.json()["detail"]
    assert _login(c, user_org_user.email, WW, x_real_ip=CF_RAND, cf_connecting_ip="203.0.113.6").status_code == 200


def test_standaardlimiet_is_96_per_uur(via, user_org_user, snel_wachtwoord):
    c = via()
    hdr = {"x_real_ip": CF_RAND, "cf_connecting_ip": "203.0.113.5"}
    codes = [_login(c, user_org_user.email, WW, **hdr).status_code for _ in range(97)]
    assert codes[:96] == [200] * 96 and codes[96] == 429


def test_auditlog_legt_het_werkelijke_adres_vast(via, user_org_user, caplog):
    c = via()
    with caplog.at_level(logging.INFO, logger="rhadix.audit"):
        _login(c, user_org_user.email, "fout", x_real_ip=CF_RAND, cf_connecting_ip="203.0.113.5",
               x_forwarded_for="198.51.100.7")
        _login(c, user_org_user.email, WW, x_real_ip="203.0.113.9", cf_connecting_ip="198.51.100.8")
    ips = [json.loads(r.getMessage())["ip"] for r in caplog.records if r.name == "rhadix.audit"]
    assert ips == ["203.0.113.5", "203.0.113.9"]


def test_bestaande_login_ongewijzigd(client, user_org_user):
    r = client.post("/api/auth/login", json={"email": user_org_user.email, "password": WW})
    assert r.status_code == 200 and r.json()["access_token"]
    r = client.post("/api/auth/login", json={"email": user_org_user.email, "password": "fout"})
    assert r.status_code == 401 and r.json()["detail"] == "Incorrect email or password"
    for _ in range(4):
        client.post("/api/auth/login", json={"email": user_org_user.email, "password": "fout"})
    r = client.post("/api/auth/login", json={"email": user_org_user.email, "password": WW})
    assert r.status_code == 429 and r.json()["detail"].startswith("Too many failed login attempts")


def test_noodprocedure_blijft_op_het_directe_bronadres(monkeypatch):
    from app.routers import internal_revocation as ir
    r = _req(GATEWAY, x_real_ip="203.0.113.9", cf_connecting_ip="198.51.100.1")
    assert ir._ip(r) == GATEWAY
