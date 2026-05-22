"""
brute_force.py — In-memory brute-force beveiliging voor de login endpoint.

Per IP-adres worden mislukte pogingen bijgehouden. Na MAX_ATTEMPTS
mislukte pogingen wordt het IP LOCKOUT_SECONDS geblokkeerd.

Opmerking: in-memory betekent dat de teller reset bij een herstart.
Voor productie met meerdere instances: vervang door Redis-backed opslag.
"""
from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock

# ---------------------------------------------------------------------------
# Configuratie
# ---------------------------------------------------------------------------
MAX_ATTEMPTS    = 5       # max mislukte pogingen voor lockout
LOCKOUT_SECONDS = 900     # 15 minuten blokkering
WINDOW_SECONDS  = 300     # telvenster: pogingen ouder dan 5 min tellen niet mee

_lock = Lock()

# Structuur: { ip: [(timestamp, success), ...] }
_attempts: dict[str, list[tuple[float, bool]]] = defaultdict(list)


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


# ---------------------------------------------------------------------------
# Intern
# ---------------------------------------------------------------------------

def _cleanup(ip: str) -> None:
    """Verwijder pogingen die buiten het telvenster vallen."""
    cutoff = time.time() - max(WINDOW_SECONDS, LOCKOUT_SECONDS)
    if ip in _attempts:
        _attempts[ip] = [(t, ok) for t, ok in _attempts[ip] if t > cutoff]
        if not _attempts[ip]:
            del _attempts[ip]
