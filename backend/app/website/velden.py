"""
velden.py — Gedeelde invoercontrole voor de website-endpoints.
"""
from __future__ import annotations

import uuid


def geldige_aanvraag_id(waarde: str) -> str:
    """Leeg (de server maakt er een) of een UUID zoals `crypto.randomUUID()`
    die levert. Iets anders wordt geweigerd: de id wordt een primaire sleutel."""
    waarde = (waarde or "").strip().lower()
    if not waarde:
        return ""
    try:
        return str(uuid.UUID(waarde))
    except ValueError:
        raise ValueError("aanvraag_id is geen geldige UUID") from None
