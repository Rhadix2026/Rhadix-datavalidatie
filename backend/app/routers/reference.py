from fastapi import APIRouter, HTTPException
from app.services.validator import KIKV_REFERENCE, KIKV_FIELDS_REFERENCE
from app.services.rules import FIELD_RULES
from app.services.source_systems import get_all_systems, get_system, SOURCE_SYSTEMS

router = APIRouter()

@router.get("/schemas")
def get_schemas():
    return {k: {
        "label": v["label"], "color": v["color"], "icon": v["icon"],
        "description": v["description"], "source": v.get("source",""),
        "required_cols": v["required_cols"],
        "col_aliases": v["col_aliases"],
        "allowed_types": v.get("allowed_types", []),
    } for k, v in KIKV_REFERENCE.items()}

@router.get("/fields")
def get_fields():
    return KIKV_FIELDS_REFERENCE

@router.get("/concepts")
def get_concepts():
    concepts = {}
    for f in KIKV_FIELDS_REFERENCE:
        c = f["concept"]
        if c not in concepts:
            concepts[c] = {"concept": c, "fields": []}
        concepts[c]["fields"].append(f)
    return list(concepts.values())

@router.get("/rules")
def get_rules():
    """
    Geeft de volledige validatieregels terug per schema en veld.
    Bevat allowedValues (met label + tijdelijk-flag), required,
    format en bronverwijzingen voor elk veld.
    """
    return FIELD_RULES


# ── Bronsystemen bibliotheek ───────────────────────────────────────────────────

@router.get("/source-systems")
def get_source_systems():
    """
    Geeft alle beschikbare bronsystemen terug met metadata:
    id, label, vendor, versie, kleur, beschrijving, aandachtspunten.
    """
    return get_all_systems()


@router.get("/source-systems/{system_id}")
def get_source_system_detail(system_id: str):
    """
    Geeft het volledige referentieontwerp van één bronsysteem terug,
    inclusief per schema de verwachte exportkolomnamen en toelichtingen.
    """
    system = get_system(system_id)
    if not system:
        raise HTTPException(status_code=404, detail=f"Bronsysteem '{system_id}' niet gevonden.")
    return system


@router.get("/source-systems/{system_id}/schemas")
def get_source_system_schemas(system_id: str):
    """
    Geeft de schema-mappings van een bronsysteem terug:
    welke kolom in het bronsysteem hoort bij welk KIK-V veld.
    """
    system = get_system(system_id)
    if not system:
        raise HTTPException(status_code=404, detail=f"Bronsysteem '{system_id}' niet gevonden.")
    return system.get("schemas", {})
