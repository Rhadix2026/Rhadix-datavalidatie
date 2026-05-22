"""
token_blocklist.py — In-memory blocklist voor ingetrokken JWT tokens.

Bij logout wordt de token-JTI (of het volledige token) geblokkeerd tot de
originele vervaldatum. Verlopen tokens worden automatisch opgeruimd.

Opmerking: in-memory → reset bij herstart. Voor multi-instance productie:
vervang _blocklist door een Redis SET met TTL.
"""
from __future__ import annotations

import time
from threading import Lock

_lock = Lock()
# { jti_or_token: expires_at_unix }
_blocklist: dict[str, float] = {}


def block_token(token_id: str, expires_at: float) -> None:
    """Voeg een token toe aan de blocklist tot expires_at (unix timestamp)."""
    with _lock:
        _blocklist[token_id] = expires_at
        _cleanup()


def is_blocked(token_id: str) -> bool:
    """Geeft True als het token geblokkeerd is en nog niet verlopen."""
    with _lock:
        exp = _blocklist.get(token_id)
        if exp is None:
            return False
        if time.time() > exp:
            del _blocklist[token_id]
            return False
        return True


def _cleanup() -> None:
    """Verwijder verlopen tokens (aanroepen terwijl lock gehouden wordt)."""
    now = time.time()
    expired = [k for k, v in _blocklist.items() if v < now]
    for k in expired:
        del _blocklist[k]
