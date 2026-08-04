"""
branding.py — publiek serveren van tenant-logo's (voor de look-and-feel).

Logo's zijn niet gevoelig en worden in de balk getoond, dus dit endpoint is
zonder authenticatie benaderbaar. Cache-busting gebeurt via ?v=<version> vanuit
de effectieve-branding-payload.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.auth_models import TenantBranding

router = APIRouter(tags=["Branding"])


@router.get("/{tenant_id}/logo")
def get_tenant_logo(tenant_id: str, db: Session = Depends(get_db)):
    try:
        tid = uuid.UUID(tenant_id)
    except (ValueError, AttributeError):
        raise HTTPException(400, "Invalid tenant_id")
    b = db.query(TenantBranding).filter(TenantBranding.tenant_id == tid).first()
    if not b or b.logo_data is None:
        raise HTTPException(404, "Geen logo")
    return Response(content=b.logo_data, media_type=b.logo_mime or "application/octet-stream",
                    headers={"Cache-Control": "public, max-age=3600"})
