"""
beveiligingsregel.py — B-31: wijzigingen van credentials en bevoegdheden.

De regel:

    Bij elke wijziging of intrekking van een credential of bevoegdheid wordt
    (1) een auditgebeurtenis vastgelegd — wie, wat, voor wie, reden, tijd, IP — en
    (2) elk token en elke sessie van dat subject met een `iat` vóór dat moment
        ongeldig verklaard, via de centrale intrekking van B-16.

Deel (2) loopt via `revocation_issuer.registreer_intrekking`: dezelfde tabel,
dezelfde volledige lijst en dezelfde hartslag als een uitlog. Het wordt altijd
vastgelegd; effectief wordt het per app zodra daar `SESSION_REVOCATION=on` staat.
Met de schakelaar uit (vandaag) verandert er voor gebruikers dus niets.

Faalt het vastleggen van de intrekking, dan gaat de handeling zelf door (die is al
gecommit) en neemt de uitgever de intrekking mee in de eerstvolgende hartslag —
hetzelfde gedrag als bij uitloggen.
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import Request

from app.audit import audit_log


def toepassen(db, gebeurtenis: str, onderwerp, *, request: Optional[Request] = None,
              door: Optional[Any] = None, intrekken: bool = True, **details: Any) -> None:
    """Audit + (optioneel) intrekking voor één gebruiker. Na de commit aanroepen."""
    audit_log(
        gebeurtenis, request,
        user_id=str(onderwerp.id),
        email=getattr(onderwerp, "email", None),
        tenant_id=str(getattr(onderwerp, "tenant_id", "") or "") or None,
        door=str(getattr(door, "id", door)) if door is not None else None,
        sessies_ingetrokken=intrekken,
        **details,
    )
    if intrekken:
        from app.services.revocation_issuer import registreer_intrekking
        registreer_intrekking(db, str(onderwerp.id), None, reden=gebeurtenis)


def toepassen_op_tenant(db, gebeurtenis: str, tenant_id, *, request: Optional[Request] = None,
                        door: Optional[Any] = None, **details: Any) -> int:
    """Zelfde regel voor alle gebruikers van een organisatie. Geeft het aantal terug."""
    from app.models.auth_models import User
    gebruikers = db.query(User).filter(User.tenant_id == tenant_id).all()
    for u in gebruikers:
        toepassen(db, gebeurtenis, u, request=request, door=door, **details)
    return len(gebruikers)
