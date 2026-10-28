"""
brute_force.py — In-memory brute-force beveiliging voor de login endpoint.

Per IP-adres worden mislukte pogingen bijgehouden. Na MAX_ATTEMPTS
mislukte pogingen wordt het IP LOCKOUT_SECONDS geblokkeerd.

Daarnaast geldt een uurlimiet op het aantal loginverzoeken per IP, geslaagd of
niet (LOGIN_RATE_LIMIT_PER_HOUR, standaard 96; 0 = uit). De sleutel is wat
app.auth.client_ip.limiet_sleutel oplevert (B-26).

Opmerking: in-memory betekent dat de teller reset bij een herstart.
Voor productie met meerdere instances: vervang door Redis-backed opslag.
"""
from __future__ import annotations

import logging
import os
import time
from collections import defaultdict, deque
from threading import Lock

log = logging.getLogger("rhadix.brute_force")

# ---------------------------------------------------------------------------
# Configuratie
# ---------------------------------------------------------------------------
MAX_ATTEMPTS    = 5       # max mislukte pogingen voor lockout
LOCKOUT_SECONDS = 900     # 15 minuten blokkering
WINDOW_SECONDS  = 300     # telvenster: pogingen ouder dan 5 min tellen niet mee
UURLIMIET_STANDAARD = 96  # loginverzoeken per IP per uur (LOGIN_RATE_LIMIT_PER_HOUR)
UUR_SECONDS     = 3600
MAX_SLEUTELS    = 10_000  # boven dit aantal sleutels wordt de hele tabel opgeschoond

_lock = Lock()

# Structuur: { ip: [(timestamp, success), ...] }
_attempts: dict[str, list[tuple[float, bool]]] = defaultdict(list)

# Structuur: { sleutel: deque([timestamp, ...]) } — alle loginverzoeken van het laatste uur
_verzoeken: dict[str, deque] = {}


# ---------------------------------------------------------------------------
# Publieke API
# ---------------------------------------------------------------------------

def record_failure(ip: str) -> None:
    """Registreer een mislukte loginpoging."""
    with _lock:
        _attempts[ip].append((time.time(), False))
        _cleanup(ip)


def record_success(ip: str) -> None:
    """Verwijder de telhistorie na een succesvolle login."""
    with _lock:
        _attempts.pop(ip, None)


def is_blocked(ip: str) -> bool:
    """Geeft True terug als het IP geblokkeerd is."""
    with _lock:
        _cleanup(ip)
        failures = [t for t, ok in _attempts.get(ip, []) if not ok]
        if len(failures) < MAX_ATTEMPTS:
            return False
        # Blokkering duurt LOCKOUT_SECONDS vanaf de EERSTE fout in het venster
        oldest_failure = failures[0]
        return (time.time() - oldest_failure) < LOCKOUT_SECONDS


def seconds_until_unblocked(ip: str) -> int:
    """Geeft de resterende blokkeertijd in seconden."""
    with _lock:
        failures = [t for t, ok in _attempts.get(ip, []) if not ok]
        if not failures:
            return 0
        elapsed = time.time() - failures[0]
        remaining = int(LOCKOUT_SECONDS - elapsed)
        return max(remaining, 0)


def uurlimiet() -> int:
    """LOGIN_RATE_LIMIT_PER_HOUR; ongeldig → de standaard, 0 of minder → uit."""
    ruw = (os.getenv("LOGIN_RATE_LIMIT_PER_HOUR") or "").strip()
    if not ruw:
        return UURLIMIET_STANDAARD
    try:
        return int(ruw)
    except ValueError:
        log.error("LOGIN_RATE_LIMIT_PER_HOUR=%r is geen geheel getal — standaard %d",
                  ruw, UURLIMIET_STANDAARD)
        return UURLIMIET_STANDAARD


def verzoek_toegestaan(sleutel: str) -> tuple[bool, int]:
    """Telt dit loginverzoek mee voor de uurlimiet.

    Geeft (True, 0) als het verzoek binnen de limiet valt (en telt het), of
    (False, seconden) als de limiet bereikt is; een geweigerd verzoek telt niet.
    """
    limiet = uurlimiet()
    if limiet <= 0:
        return True, 0
    nu = time.time()
    with _lock:
        if len(_verzoeken) > MAX_SLEUTELS:
            _ruim_verzoeken_op(nu)
        rij = _verzoeken.setdefault(sleutel, deque())
        while rij and rij[0] <= nu - UUR_SECONDS:
            rij.popleft()
        if len(rij) >= limiet:
            return False, max(int(rij[0] + UUR_SECONDS - nu) + 1, 1)
        rij.append(nu)
        return True, 0


def reset() -> None:
    """Alle tellers leeg (tests)."""
    with _lock:
        _attempts.clear()
        _verzoeken.clear()


# ---------------------------------------------------------------------------
# Intern
# ---------------------------------------------------------------------------

def _ruim_verzoeken_op(nu: float) -> None:
    for sleutel in [s for s, rij in _verzoeken.items() if not rij or rij[-1] <= nu - UUR_SECONDS]:
        del _verzoeken[sleutel]


def _cleanup(ip: str) -> None:
    """Verwijder pogingen die buiten het telvenster vallen."""
    cutoff = time.time() - max(WINDOW_SECONDS, LOCKOUT_SECONDS)
    if ip in _attempts:
        _attempts[ip] = [(t, ok) for t, ok in _attempts[ip] if t > cutoff]
        if not _attempts[ip]:
            del _attempts[ip]
