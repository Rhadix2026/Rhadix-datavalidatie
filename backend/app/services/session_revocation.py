"""
session_revocation.py — centrale intrekking van gebruikerssessies (B-16).

Ontwerp in één alinea: de uitgever duwt intrekkingen naar de resource-apps en
stuurt elke 15 seconden een hartslag met de **volledige actuele lijst**. Een
resource-app doet zelf geen enkele uitgaande aanroep — nodig omdat fail-closed
plus een live aanroep de uitgever tot single point of failure voor vier
applicaties zou maken, en omdat CRM geen HTTP-client heeft.

Drie strikt gescheiden controles, en dat onderscheid is de hele veiligheid:

    A  jti staat in de lokale lijst          -> bekende intrekking, altijd 401
    B  logout_at van sub ligt na token.iat   -> bekende intrekking, altijd 401
    C  laatste hartslag te oud               -> ACTUALITEIT, niet een intrekking

De noodprocedure versoepelt **uitsluitend C**. Een token dat door A of B wordt
geweigerd blijft geweigerd, in elke stand. Er bestaat dus geen situatie waarin
een bekend ingetrokken token opnieuw geldig wordt.

Machine-to-machine valt hier volledig buiten: lokale HS256-tokens met
`typ=client` komen via een andere tak van `get_current_user` binnen en worden
nooit tegen deze lijst getoetst — ook niet wanneer het beeld muf is.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

log = logging.getLogger("rhadix.revocation")

# ── instellingen ───────────────────────────────────────────────────────────

def _aan() -> bool:
    return os.getenv("SESSION_REVOCATION", "off").lower().strip() == "on"


def max_levensduur_seconden() -> int:
    """Langste toegestane tokenlevensduur: gelijk aan die van de uitgever
    (JWT_ACCESS_TOKEN_EXPIRE_MINUTES, standaard 60), plus één minuut klokmarge."""
    try:
        minuten = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    except ValueError:
        minuten = 60
    return minuten * 60 + 60


def versheidsbudget() -> int:
    return int(os.getenv("REVOCATION_FRESHNESS_BUDGET", "60"))


def hartslaginterval() -> int:
    return int(os.getenv("REVOCATION_HEARTBEAT_INTERVAL", "15"))


def doelen() -> list[str]:
    ruw = os.getenv("REVOCATION_TARGETS", "")
    return [d.strip().rstrip("/") for d in ruw.split(",") if d.strip()]


def lokaal_toepassen() -> bool:
    """Alleen voor de uitgever die ook resource is (Datavalidatie, stap 3): pas
    elke hartslag in hetzelfde proces toe op de eigen ontvangertabellen, in
    plaats van via HTTP naar zichzelf."""
    return os.getenv("REVOCATION_APPLY_LOCALLY", "off").lower().strip() == "on"


def _iat_vereist_vanaf() -> Optional[datetime]:
    """Harde overgangsdatum. Vóór dit tijdstip wordt een token zonder `iat`
    toegelaten; daarna geweigerd. Niet gezet = nooit vereisen."""
    ruw = (os.getenv("REVOCATION_REQUIRE_IAT_FROM") or "").strip()
    if not ruw:
        return None
    try:
        return datetime.fromisoformat(ruw.replace("Z", "+00:00"))
    except ValueError:
        log.error("REVOCATION_REQUIRE_IAT_FROM is onleesbaar: %r — als niet gezet behandeld", ruw)
        return None


MAX_NOODDUUR_MINUTEN = 30


# ── uitkomst van de controle ───────────────────────────────────────────────

class Uitkomst:
    """Waarom een token wordt geweigerd, of dat het mag."""

    def __init__(self, toegestaan: bool, reden: str = "", grondslag: str = ""):
        self.toegestaan = toegestaan
        self.reden = reden
        self.grondslag = grondslag          # "A" | "B" | "C" | ""

    def __bool__(self) -> bool:
        return self.toegestaan


TOEGESTAAN = Uitkomst(True)


# ── de kern: controleer een centrale claimset ──────────────────────────────

def controleer(
    claims: dict[str, Any],
    *,
    ingetrokken_jtis: set[str],
    logout_at_voor_sub,
    laatst_gehoord: Optional[datetime],
    noodmarge_tot: Optional[datetime] = None,
    nu: Optional[datetime] = None,
) -> Uitkomst:
    """Past A, B en C toe. Pure functie: de aanroeper levert de stand aan, zodat
    dit zonder database te testen is.

    `logout_at_voor_sub` is een callable die voor een `sub` het uitlogmoment
    teruggeeft, of None.
    """
    if not _aan():
        return TOEGESTAAN
    nu = nu or datetime.now(timezone.utc)

    # ── A: dit specifieke token is ingetrokken ──
    jti = claims.get("jti")
    if jti and jti in ingetrokken_jtis:
        return Uitkomst(False, "Sessie is ingetrokken", "A")

    # ── B: alle sessies van deze gebruiker van vóór het uitlogmoment ──
    iat_ruw = claims.get("iat")
    sub = str(claims.get("sub") or "")
    if iat_ruw is None:
        grens = _iat_vereist_vanaf()
        if grens is not None and nu >= grens:
            return Uitkomst(False, "Token mist een uitgiftetijd", "B")
        # Binnen het overgangsvenster: toegestaan, maar B kan niet worden
        # beoordeeld. Bewust en aflopend; na `grens` kan dit niet meer.
        log.info("token zonder iat toegelaten binnen het overgangsvenster (sub=%s)", sub[:8])
    else:
        iat = datetime.fromtimestamp(int(iat_ruw), tz=timezone.utc)
        # Een intrekking blijft tokenlevensduur + marge bewaard. Een token dat langer
        # leeft dan die levensduur zou na het verlopen van de intrekking weer
        # geldig worden; zo'n token wordt daarom nooit geaccepteerd.
        exp_ruw = claims.get("exp")
        if exp_ruw is not None and int(exp_ruw) - int(iat_ruw) > max_levensduur_seconden():
            return Uitkomst(False, "Token leeft langer dan toegestaan", "B")
        uitgelogd_op = logout_at_voor_sub(sub) if sub else None
        if uitgelogd_op is not None:
            if uitgelogd_op.tzinfo is None:
                uitgelogd_op = uitgelogd_op.replace(tzinfo=timezone.utc)
            # Gelijk aan het uitlogmoment telt als ingetrokken: een token dat in
            # dezelfde seconde is uitgegeven hoort niet door te mogen.
            if iat <= uitgelogd_op:
                return Uitkomst(False, "Sessie is ingetrokken", "B")

    # ── C: is ons beeld actueel genoeg? ──
    if laatst_gehoord is None:
        vers = False
    else:
        if laatst_gehoord.tzinfo is None:
            laatst_gehoord = laatst_gehoord.replace(tzinfo=timezone.utc)
        vers = (nu - laatst_gehoord) <= timedelta(seconds=versheidsbudget())
    if vers:
        return TOEGESTAAN

    if noodmarge_tot is not None:
        if noodmarge_tot.tzinfo is None:
            noodmarge_tot = noodmarge_tot.replace(tzinfo=timezone.utc)
        if nu < noodmarge_tot:
            # Uitsluitend C wordt versoepeld; A en B zijn hierboven al afgedwongen.
            log.warning(
                "noodprocedure actief: muf beeld toegelaten (sub=%s, laatst gehoord %s)",
                (str(claims.get("sub") or ""))[:8], laatst_gehoord)
            return TOEGESTAAN

    return Uitkomst(False, "Intrekkingsstatus is niet actueel", "C")


# ── de lijst die de uitgever rondstuurt ────────────────────────────────────

def bouw_lijst(rijen) -> dict[str, Any]:
    """Zet intrekkingsrijen om in de hartslag-inhoud. De volledige actuele
    lijst, niet een delta: daardoor is elke hartslag idempotent en
    zelfherstellend, en convergeert elke ontvanger binnen één interval."""
    nu = datetime.now(timezone.utc)
    uit = []
    for r in rijen:
        verloopt = getattr(r, "expires_at", None)
        if verloopt is not None:
            if verloopt.tzinfo is None:
                verloopt = verloopt.replace(tzinfo=timezone.utc)
            if verloopt <= nu:
                continue        # verlopen intrekkingen hoeven niet rond
        # Een ontbrekende not_before blijft leeg: dan is het een intrekking van
        # één token (A), geen intrekking van alle sessies van `sub` (B).
        nb = getattr(r, "not_before", None)
        if nb is not None and nb.tzinfo is None:
            nb = nb.replace(tzinfo=timezone.utc)
        uit.append({
            "jti":        getattr(r, "jti", None),
            "sub":        str(getattr(r, "sub", "") or ""),
            "not_before": nb.isoformat() if nb else None,
            "expires_at": verloopt.isoformat() if verloopt else None,
        })
    return {"generated_at": nu.isoformat(), "revocations": uit}


# ── de lijst als ondertekend bericht ───────────────────────────────────────
#
# Push-authenticatie zonder nieuw gedeeld geheim: de uitgever tekent de lijst
# met dezelfde sleutel als de toegangstokens, en elke ontvanger controleert met
# de publieke sleutel die hij al heeft. `aud` en `typ` houden de twee soorten
# berichten strikt uit elkaar: een toegangstoken is nooit een lijst, en een
# lijst heeft geen `sub` en is dus nooit een toegangstoken.

LIJST_AUD = "rhadix-revocation"
LIJST_TYP = "revocation-list"
MAX_KLOKVERSCHIL = timedelta(seconds=5)


def teken_lijst(lijst: dict[str, Any]) -> str:
    from jose import jwt
    from app.auth import security

    nu = datetime.now(timezone.utc)
    claims = {
        "iss": security.ISSUER,
        "aud": LIJST_AUD,
        "typ": LIJST_TYP,
        "iat": int(nu.timestamp()),
        # Kort geldig: een onderschept bericht is na twee intervallen waardeloos.
        "exp": int((nu + timedelta(seconds=max(2 * hartslaginterval(), 30))).timestamp()),
        **lijst,
    }
    if security.USE_RS256:
        return jwt.encode(claims, security.PRIVATE_KEY, algorithm="RS256",
                          headers={"kid": security.KID})
    return jwt.encode(claims, security.SECRET_KEY, algorithm=security.ALGORITHM)


def lees_lijst(token: str) -> dict[str, Any]:
    """Verifieer een lijstbericht. Gooit ValueError bij elke afwijking."""
    from jose import JWTError, jwt
    from app.auth import security

    # Het algoritme volgt uit de configuratie, nooit uit de header van het bericht.
    if security.USE_RS256:
        sleutel, alg = security.PUBLIC_KEY, "RS256"
    else:
        sleutel, alg = security.SECRET_KEY, security.ALGORITHM
    try:
        claims = jwt.decode(token, sleutel, algorithms=[alg], audience=LIJST_AUD,
                            issuer=security.ISSUER)
    except JWTError as exc:
        raise ValueError(f"ongeldig lijstbericht: {exc}") from exc
    # python-jose controleert `aud` alleen als hij aanwezig is; daarom expliciet.
    if claims.get("aud") != LIJST_AUD or claims.get("typ") != LIJST_TYP:
        raise ValueError("geen intrekkingslijst")
    if "sub" in claims:
        raise ValueError("lijstbericht mag geen sub dragen")
    if not isinstance(claims.get("revocations"), list) or not claims.get("generated_at"):
        raise ValueError("lijstbericht is onvolledig")
    return claims


def lees_tijd(ruw) -> Optional[datetime]:
    if not ruw:
        return None
    t = datetime.fromisoformat(str(ruw).replace("Z", "+00:00"))
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


# ── noodprocedure: invoer en geheim ────────────────────────────────────────

MIN_REDEN_TEKENS = 20
MIN_GEHEIM_TEKENS = 32


def noodgeheim() -> Optional[str]:
    """De SHA-256-hash (hex) van het voorgedeelde geheim, of None als de
    noodprocedure niet is ingericht.

    De server kent alleen de hash, nooit het geheim zelf: wie de omgeving of
    het env-bestand leest, kan er de noodprocedure niet mee activeren. Het
    geheim is willekeurig en lang, dus een kale SHA-256 volstaat."""
    h = (os.getenv("REVOCATION_BREAKGLASS_SECRET_SHA256") or "").strip().lower()
    if not h:
        return None
    if len(h) != 64 or any(c not in "0123456789abcdef" for c in h):
        log.error("REVOCATION_BREAKGLASS_SECRET_SHA256 is geen SHA-256-hexwaarde — noodprocedure uit")
        return None
    return h


def geheim_klopt(aangeboden: Optional[str]) -> bool:
    import hashlib
    import hmac
    h = noodgeheim()
    if not h or not aangeboden:
        return False
    aangeboden = aangeboden.strip()
    # Een te kort geheim wordt niet eens vergeleken: liever geen nooduitgang dan
    # een die te raden is.
    if len(aangeboden) < MIN_GEHEIM_TEKENS:
        return False
    return hmac.compare_digest(hashlib.sha256(aangeboden.encode("utf-8")).hexdigest(), h)


def toets_noodverzoek(body: Any) -> tuple[int, str, str]:
    """Controleer de verplichte velden. Geeft (duur_minuten, reden, uitgevoerd_door)
    of gooit ValueError met een leesbare melding."""
    if not isinstance(body, dict):
        raise ValueError("verwacht een JSON-object")
    duur = body.get("duur_minuten")
    if isinstance(duur, bool) or not isinstance(duur, int):
        raise ValueError("duur_minuten is verplicht en moet een geheel getal zijn")
    if not 1 <= duur <= MAX_NOODDUUR_MINUTEN:
        raise ValueError(f"duur_minuten moet tussen 1 en {MAX_NOODDUUR_MINUTEN} liggen")
    reden = body.get("reden")
    if not isinstance(reden, str) or len(reden.strip()) < MIN_REDEN_TEKENS:
        raise ValueError(f"reden is verplicht, minimaal {MIN_REDEN_TEKENS} tekens")
    door = body.get("uitgevoerd_door")
    if not isinstance(door, str) or not door.strip():
        raise ValueError("uitgevoerd_door is verplicht")
    if len(door.strip()) > 255 or len(reden.strip()) > 2000:
        raise ValueError("uitgevoerd_door of reden is te lang")
    return duur, reden.strip(), door.strip()
