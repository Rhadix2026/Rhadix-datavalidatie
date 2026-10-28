"""
client_ip.py — het IP-adres van de client, uitsluitend via een vertrouwde proxyketen (B-26).

De keten op staging en productie:

    client → Cloudflare → host-nginx → docker-proxy → backend

1. De backend ziet als direct bronadres de Docker-gateway; dat is de host, en
   daarmee nginx. Alleen zo'n vertrouwde proxy mag koppen meegeven
   (TRUSTED_PROXY_NETWORKS; leeg = loopback plus de eigen standaardgateway).
2. nginx zet `X-Real-IP $remote_addr` zelf, op basis van de TCP-verbinding; een
   door de client meegestuurde X-Real-IP wordt daarbij overschreven.
3. Is dat adres een Cloudflare-adres (CLOUDFLARE_NETWORKS), dan heeft Cloudflare
   `CF-Connecting-IP` gezet en een meegestuurde overschreven. Is het geen
   Cloudflare-adres, dan kwam de verbinding om Cloudflare heen en is
   `CF-Connecting-IP` vrij te kiezen: dan telt X-Real-IP.
4. `X-Forwarded-For` wordt nooit gebruikt: het eerste element kiest de client zelf.

Een kop die niet als één IP-adres te lezen is, telt niet; dan valt de bepaling
terug op de vorige schakel. Er wordt nooit een uitzondering opgegooid.
"""
from __future__ import annotations

import ipaddress
import logging
import os
from functools import lru_cache
from typing import Optional

from fastapi import Request

log = logging.getLogger("rhadix.client_ip")

Adres = ipaddress.IPv4Address | ipaddress.IPv6Address
Net = ipaddress.IPv4Network | ipaddress.IPv6Network

# Gepubliceerd op https://www.cloudflare.com/ips-v4 en /ips-v6 (opgehaald 28-10-2026).
CLOUDFLARE_STANDAARD = (
    "173.245.48.0/20,103.21.244.0/22,103.22.200.0/22,103.31.4.0/22,141.101.64.0/18,"
    "108.162.192.0/18,190.93.240.0/20,188.114.96.0/20,197.234.240.0/22,198.41.128.0/17,"
    "162.158.0.0/15,104.16.0.0/13,104.24.0.0/14,172.64.0.0/13,131.0.72.0/22,"
    "2400:cb00::/32,2606:4700::/32,2803:f800::/32,2405:b500::/32,2405:8100::/32,"
    "2a06:98c0::/29,2c0f:f248::/32"
)
LOOPBACK = "127.0.0.0/8,::1/128"
ROUTETABEL = "/proc/net/route"


def _adres(waarde: Optional[str]) -> Optional[Adres]:
    """Eén IP-adres, of None. Een IPv4-adres in IPv6-vorm wordt IPv4."""
    if not waarde:
        return None
    try:
        a = ipaddress.ip_address(waarde.strip())
    except ValueError:
        return None
    if isinstance(a, ipaddress.IPv6Address) and a.ipv4_mapped:
        return a.ipv4_mapped
    return a


def _netten(tekst: str, bron: str) -> tuple[Net, ...]:
    netten = []
    for deel in (tekst or "").split(","):
        deel = deel.strip()
        if not deel:
            continue
        try:
            netten.append(ipaddress.ip_network(deel, strict=False))
        except ValueError:
            log.error("%s: '%s' is geen netwerk — overgeslagen", bron, deel)
    return tuple(netten)


def standaard_gateway(routetabel: Optional[str] = None) -> Optional[str]:
    """De IPv4-standaardgateway uit /proc/net/route; in een container is dat de host."""
    try:
        if routetabel is None:
            with open(ROUTETABEL) as f:
                routetabel = f.read()
    except OSError:
        return None
    for regel in routetabel.splitlines()[1:]:
        velden = regel.split()
        if len(velden) >= 3 and velden[1] == "00000000":
            try:
                return str(ipaddress.IPv4Address(bytes.fromhex(velden[2])[::-1]))
            except ValueError:
                return None
    return None


@lru_cache(maxsize=8)
def _vertrouwde_proxys(spec: str) -> tuple[Net, ...]:
    if spec.strip():
        netten = _netten(spec, "TRUSTED_PROXY_NETWORKS")
    else:
        gw = standaard_gateway()
        netten = _netten(LOOPBACK + (f",{gw}/32" if gw else ""), "standaard")
    log.info("client-IP: vertrouwde proxy's = %s", ", ".join(str(n) for n in netten))
    return netten


@lru_cache(maxsize=8)
def _cloudflare(spec: str) -> tuple[Net, ...]:
    return _netten(spec.strip() or CLOUDFLARE_STANDAARD, "CLOUDFLARE_NETWORKS")


def _in(adres: Adres, netten: tuple[Net, ...]) -> bool:
    return any(adres.version == n.version and adres in n for n in netten)


def client_ip(request: Request) -> str:
    """Het werkelijke client-IP volgens de vertrouwde keten (zie moduledocstring)."""
    ruw = request.client.host if request.client else None
    bron = _adres(ruw)
    if bron is None:
        return ruw or "unknown"
    if not _in(bron, _vertrouwde_proxys(os.getenv("TRUSTED_PROXY_NETWORKS", ""))):
        return str(bron)
    echt = _adres(request.headers.get("x-real-ip"))
    if echt is None:
        return str(bron)
    if _in(echt, _cloudflare(os.getenv("CLOUDFLARE_NETWORKS", ""))):
        cf = _adres(request.headers.get("cf-connecting-ip"))
        if cf is not None:
            return str(cf)
    return str(echt)


def limiet_sleutel(ip: str) -> str:
    """Sleutel voor begrenzing: het IPv4-adres, of het /64-net van een IPv6-adres.

    Eén IPv6-aansluiting krijgt doorgaans een heel /64; per adres tellen zou een
    aanvaller binnen dat net onbeperkt nieuwe adressen geven.
    """
    a = _adres(ip)
    if a is None:
        return ip
    if a.version == 6:
        return str(ipaddress.ip_network(f"{a}/64", strict=False))
    return str(a)
