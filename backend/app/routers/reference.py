from fastapi import APIRouter, HTTPException
from app.services.validator import KIKV_REFERENCE, KIKV_FIELDS_REFERENCE
from app.services.rules import FIELD_RULES
from app.services.source_systems import get_all_systems, get_system, SOURCE_SYSTEMS
from app.services.ontology_index import CONCEPTS, PROPERTIES, get_subclasses, label as concept_label

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
    """
    Groepeert KIKV_FIELDS_REFERENCE op concept en voegt concept_uri toe.
    Stap 2: toont de ontologie-koppeling per veld.
    """
    concepts: dict = {}
    for f in KIKV_FIELDS_REFERENCE:
        c = f["concept"]
        uri = f.get("concept_uri", "")
        if c not in concepts:
            concepts[c] = {
                "concept":       c,
                "concept_uri":   uri,
                "concept_label": concept_label(uri) if uri else c,
                "fields":        [],
            }
        concepts[c]["fields"].append(f)
    return list(concepts.values())

@router.get("/rules")
def get_rules():
    """
    Geeft de volledige validatieregels terug per schema en veld.
    Bevat allowedValues (met label + tijdelijk-flag + concept_uri), required,
    format, concept_uri en bronverwijzingen voor elk veld.
    """
    return FIELD_RULES


# ── Ontologie-browser ─────────────────────────────────────────────────────────

@router.get("/ontology")
def get_ontology_summary():
    """
    Geeft een samenvatting van de KIK-V ONZ-ontologie terug:
    totaal klassen per module, met NL-labels.
    """
    modules: dict = {}
    for uri, info in CONCEPTS.items():
        mod = info["module"]
        if mod not in modules:
            modules[mod] = {"module": mod, "count": 0, "classes": []}
        modules[mod]["count"] += 1
        if info.get("label_nl"):
            modules[mod]["classes"].append({
                "uri":      uri,
                "name":     info["name"],
                "label_nl": info["label_nl"],
                "parents":  info["parents"],
            })
    return list(modules.values())


@router.get("/ontology/{module}")
def get_ontology_module(module: str):
    """
    Geeft alle klassen van één ONZ-module terug (bijv. onz-pers, onz-org).
    Inclusief subklassen-boom en NL-labels.
    """
    valid = {"onz-g", "onz-pers", "onz-org", "onz-zorg", "onz-fin", "onz-plan"}
    if module not in valid:
        raise HTTPException(status_code=404, detail=f"Module '{module}' niet gevonden. Geldig: {', '.join(valid)}")

    classes = [
        {
            "uri":        uri,
            "name":       info["name"],
            "label_nl":   info["label_nl"],
            "label_en":   info.get("label_en", ""),
            "parents":    info["parents"],
            "subclasses": info["subclasses"],
        }
        for uri, info in CONCEPTS.items()
        if info["module"] == module
    ]
    return {"module": module, "count": len(classes), "classes": classes}


@router.get("/ontology-concept/{concept_name}")
def get_ontology_concept(concept_name: str):
    """
    Zoek een concept op naam (bijv. 'ArbeidsOvereenkomst').
    Geeft het concept terug inclusief alle subklassen (recursief).
    """
    # Zoek op naam
    match = None
    for uri, info in CONCEPTS.items():
        if info["name"].lower() == concept_name.lower():
            match = (uri, info)
            break

    if not match:
        raise HTTPException(status_code=404, detail=f"Concept '{concept_name}' niet gevonden.")

    uri, info = match
    subs = get_subclasses(uri, recursive=True)

    return {
        "uri":        uri,
        "name":       info["name"],
        "label_nl":   info["label_nl"],
        "module":     info["module"],
        "parents":    [{"uri": p, "label_nl": concept_label(p)} for p in info["parents"]],
        "subclasses": [
            {"uri": s, "name": CONCEPTS[s]["name"], "label_nl": CONCEPTS[s]["label_nl"]}
            for s in subs if s in CONCEPTS
        ],
    }


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
    inclusief per schema de verwachte exportkolomnamen, toelichtingen
    en concept_uri verwijzingen naar de KIK-V ontologie.
    """
    system = get_system(system_id)
    if not system:
        raise HTTPException(status_code=404, detail=f"Bronsysteem '{system_id}' niet gevonden.")
    return system


@router.get("/source-systems/{system_id}/schemas")
def get_source_system_schemas(system_id: str):
    """
    Geeft de schema-mappings van een bronsysteem terug:
    welke kolom in het bronsysteem hoort bij welk KIK-V veld en concept.
    """
    system = get_system(system_id)
    if not system:
        raise HTTPException(status_code=404, detail=f"Bronsysteem '{system_id}' niet gevonden.")
    return system.get("schemas", {})
