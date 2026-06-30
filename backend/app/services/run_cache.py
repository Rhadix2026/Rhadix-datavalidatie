"""
run_cache.py — Tijdelijke, in-memory cache van de huidige fase-1 validatie per
gebruiker, zodat een fase-2 benchmark (KIK-V/ZIB) geen her-upload vraagt.

Dataminimaal:
  * één 'huidige validatie' per gebruiker — een nieuwe scan OVERSCHRIJFT de vorige
    (cache wissen bij nieuwe scan);
  * TTL: een entry vervalt automatisch (geen zorgdata blijft hangen);
  * clear(user_id) voor expliciet wissen (bv. bij logout/sessie-einde).

NB: in-memory en per-proces; bij meerdere workers/replica's later vervangen door
een gedeelde store (Redis) met dezelfde semantiek.
"""
from __future__ import annotations

import time
import threading
from typing import Any, Optional

_TTL_SECONDS = 2 * 60 * 60  # 2 uur
_lock = threading.Lock()
_store: dict[str, dict[str, Any]] = {}


def _now() -> float:
    return time.time()


def _prune() -> None:
    cutoff = _now() - _TTL_SECONDS
    for k in [k for k, v in _store.items() if v.get("ts", 0) < cutoff]:
        _store.pop(k, None)


def set_current(user_key: str, source: Optional[str], files: list[dict]) -> None:
    """Bewaar de huidige fase-1 data (overschrijft de vorige = wissen bij nieuwe scan)."""
    if not user_key:
        return
    with _lock:
        _prune()
        _store[user_key] = {"source": source, "files": files, "ts": _now()}


def get_current(user_key: str) -> Optional[dict[str, Any]]:
    if not user_key:
        return None
    with _lock:
        _prune()
        return _store.get(user_key)


def clear(user_key: str) -> None:
    with _lock:
        _store.pop(user_key, None)
