"""
branding.py — effectieve look-and-feel per tenant, met overerving.

Resolutievolgorde (eerste die een branding-profiel heeft, wint):
    1. de tenant zelf
    2. de ouder-RSO (parent_tenant_id)
    3. het Rhadix-platform (tenant met slug 'rhadix-platform')
    4. de vaste Rhadix-default (hieronder)

Een "profiel heeft branding" = er is een TenantBranding-rij met minstens één
betekenisvol veld (preset/kleur/wordmerk/logo).
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.models.auth_models import Tenant, TenantBranding

PLATFORM_SLUG = "rhadix-platform"

# Vaste Rhadix-default (komt overeen met index.css :root)
RHADIX_DEFAULT = {
    "preset":        "rhadix",
    "primary_color": "#1A2847",
    "accent_color":  "#1A2847",
    "wordmark":      None,
    "source":        "default",
    "logo_tenant_id": None,
    "logo_version":   None,
}


def _has_branding(b: Optional[TenantBranding]) -> bool:
    if not b:
        return False
    return any([b.preset, b.primary_color, b.accent_color, b.wordmark, b.logo_data])


def _to_payload(b: TenantBranding, source: str) -> dict:
    has_logo = b.logo_data is not None
    return {
        "preset":         b.preset or "custom",
        "primary_color":  b.primary_color or RHADIX_DEFAULT["primary_color"],
        "accent_color":   b.accent_color or (b.primary_color or RHADIX_DEFAULT["accent_color"]),
        "wordmark":       b.wordmark,
        "source":         source,
        "logo_tenant_id": str(b.tenant_id) if has_logo else None,
        "logo_version":   int(b.updated_at.timestamp()) if (has_logo and b.updated_at) else None,
    }


def _branding_for(db: Session, tenant_id) -> Optional[TenantBranding]:
    return db.query(TenantBranding).filter(TenantBranding.tenant_id == tenant_id).first()


def resolve_effective_branding(db: Session, tenant: Tenant) -> dict:
    """Bepaal de effectieve branding voor (gebruikers van) deze tenant."""
    if tenant is None:
        return dict(RHADIX_DEFAULT)

    # 1. tenant zelf
    own = _branding_for(db, tenant.id)
    if _has_branding(own):
        return _to_payload(own, "self")

    # 2. ouder-RSO
    parent_id = getattr(tenant, "parent_tenant_id", None)
    if parent_id:
        par = _branding_for(db, parent_id)
        if _has_branding(par):
            return _to_payload(par, "rso")

    # 3. platform-default (bewerkbaar door Rhadix-beheerder)
    platform = db.query(Tenant).filter(Tenant.slug == PLATFORM_SLUG).first()
    if platform:
        pb = _branding_for(db, platform.id)
        if _has_branding(pb):
            return _to_payload(pb, "platform")

    # 4. vaste Rhadix-default
    return dict(RHADIX_DEFAULT)
