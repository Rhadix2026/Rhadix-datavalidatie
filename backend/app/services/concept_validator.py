"""
concept_validator.py — Stap 2: KIK-V concept-mapping validatie

Controleert per veld of de aanwezige waarde gemapped kan worden naar het
bijbehorende KIK-V ontologieconcept.

Stap 1 (beschikbaarheid)  → validator.py  : zijn de velden aanwezig?
Stap 2 (concept-mapping)  → dit bestand   : kunnen waarden naar het concept?

Resultaat per veld:
  mapped         : bool  — kon de waarde worden gemapped?
  concept_uri    : str   — het doelconcept in de ontologie
  concept_label  : str   — NL-label van het concept
  issues         : list  — gevonden mapping-problemen
"""

import json
import os
from typing import Any
from app.services.rules import (
    FIELD_RULES,
    CONTRACTTYPE_ALLOWED,
    VERZUIMTYPE_ALLOWED,
    get_concept_uri,
    ONZ_PERS, ONZ_G,
)
from app.services.ontology_index import get_concept, label as concept_label_fn

# ── KIK-V Hergebruik concepten (kik-v-publicatieplatform.nl/kik-v-concepten) ─
_HERGEBRUIK_PATH = os.path.join(os.path.dirname(__file__), "../../data/concept_hergebruik.json")

def _load_hergebruik() -> dict:
    try:
        with open(_HERGEBRUIK_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("concepts", {})
    except Exception:
        return {}

_HERGEBRUIK: dict = _load_hergebruik()
_TOTAL_PROFILES: int = 8  # uitwisselprofielen in de hergebruik-tabel


def get_hergebruik(concept_uri: str) -> dict | None:
    """
    Zoekt de hergebruik-info op voor een concept-URI.
    Accepteert zowel volledige URIs (http://purl.org/ozo/onz-pers#X)
    als korte vormen (onz-pers#X) en fragmenten (X).
    """
    if not concept_uri:
        return None
    # Normaliseer naar kort formaat: onz-pers#ArbeidsOvereenkomst
    short = concept_uri.replace("http://purl.org/ozo/", "")
    if short in _HERGEBRUIK:
        return _HERGEBRUIK[short]
    # Fallback: zoek op fragment (na #)
    frag = short.split("#")[-1] if "#" in short else short
    for v in _HERGEBRUIK.values():
        if v["uri"].split("#")[-1] == frag:
            return v
    return None

# ── Waarde-naar-concept mapping tabellen ──────────────────────────────────────

# KIK-V waarde → concept URI voor contracttypes
CONTRACTTYPE_CONCEPT_MAP: dict[str, str] = {
    av["value"]: av["concept_uri"]
    for av in CONTRACTTYPE_ALLOWED
    if "concept_uri" in av
}

# KIK-V waarde → concept URI voor verzuimtypes
VERZUIMTYPE_CONCEPT_MAP: dict[str, str] = {
    av["value"]: av["concept_uri"]
    for av in VERZUIMTYPE_ALLOWED
    if "concept_uri" in av
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_date_like(val: Any) -> bool:
    import re
    return bool(re.match(r'\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}', str(val or '')))

def _is_number_like(val: Any) -> bool:
    try:
        float(str(val).replace(',', '.'))
        return True
    except (ValueError, TypeError):
        return False

def _normalize(val: str) -> str:
    return str(val or '').strip().lower()


# ── Concept-mapping per veldtype ──────────────────────────────────────────────

def _map_field(schema: str, field: str, value: Any, rules: dict) -> dict:
    """
    Controleert of `value` gemapped kan worden naar het concept voor dit veld.
    Geeft terug: {mapped, concept_uri, concept_label, issues}
    """
    concept_uri   = rules.get("concept_uri", "")
    concept_label = rules.get("concept_label", concept_uri.split("#")[-1] if concept_uri else field)
    issues        = []
    mapped        = True

    if not concept_uri:
        return {"mapped": None, "concept_uri": None, "concept_label": None,
                "issues": ["Geen concept_uri geconfigureerd voor dit veld"]}

    # Lege waarde
    if value is None or str(value).strip() == "":
        if rules.get("required"):
            issues.append(f"Waarde ontbreekt — kan niet mappen naar «{concept_label}»")
            mapped = False
        else:
            # Optioneel veld, leeg is OK
            return {"mapped": True, "concept_uri": concept_uri,
                    "concept_label": concept_label, "issues": [], "skipped": True}

    val_str = str(value).strip()

    # ── Datum-concepten ──────────────────────────────────────────────────────
    if concept_uri in (f"{ONZ_G}startDatum", f"{ONZ_G}eindDatum", f"{ONZ_G}hasDateOfBirth"):
        if not _is_date_like(val_str):
            issues.append(f"Waarde «{val_str}» is geen geldige datum — verwacht dd/mm/yyyy")
            mapped = False

    # ── Identifier-concepten ─────────────────────────────────────────────────
    elif concept_uri == f"{ONZ_G}EmployeeIdentifier":
        if len(val_str) < 1:
            issues.append(f"Personeelsnummer mag niet leeg zijn")
            mapped = False

    elif concept_uri == f"{ONZ_G}FormalIdentifier":
        if len(val_str) < 1:
            issues.append(f"Identifier mag niet leeg zijn")
            mapped = False

    # ── Contracttype → ArbeidsOvereenkomst subklasse ─────────────────────────
    elif concept_uri in (f"{ONZ_PERS}WerkOvereenkomst", f"{ONZ_PERS}ArbeidsOvereenkomst"):
        norm = _normalize(val_str)
        matched_concept = CONTRACTTYPE_CONCEPT_MAP.get(norm)
        if matched_concept:
            concept_uri   = matched_concept
            concept_label = concept_label_fn(matched_concept) or matched_concept.split("#")[-1]
        else:
            issues.append(
                f"Waarde «{val_str}» herkend niet als geldig KIK-V contracttype. "
                f"Geldige waarden: {', '.join(CONTRACTTYPE_CONCEPT_MAP.keys())}"
            )
            mapped = False

    # ── Verzuimperiode → VerzuimPeriode subklasse ────────────────────────────
    elif concept_uri == f"{ONZ_PERS}VerzuimPeriode":
        norm = _normalize(val_str)
        matched_concept = VERZUIMTYPE_CONCEPT_MAP.get(norm)
        if matched_concept:
            concept_uri   = matched_concept
            concept_label = concept_label_fn(matched_concept) or matched_concept.split("#")[-1]
        else:
            issues.append(
                f"Waarde «{val_str}» herkend niet als geldig KIK-V verzuimtype. "
                f"Geldige waarden: {', '.join(VERZUIMTYPE_CONCEPT_MAP.keys())}"
            )
            mapped = False

    # ── Numerieke concepten ──────────────────────────────────────────────────
    elif concept_uri in (f"{ONZ_PERS}AOPercentage", f"{ONZ_PERS}ContractOmvangWaarde",
                         f"{ONZ_PERS}ContractOmvang"):
        if not _is_number_like(val_str):
            issues.append(f"Waarde «{val_str}» is geen getal")
            mapped = False
        else:
            num = float(str(val_str).replace(',', '.'))
            if concept_uri == f"{ONZ_PERS}AOPercentage" and not (0 <= num <= 100):
                issues.append(f"Percentage «{val_str}» ligt buiten 0-100")
                mapped = False

    # ── Tekst-concepten (functienaam, organisatorische eenheid, etc.) ────────
    else:
        if len(val_str.strip()) < 1:
            issues.append(f"Waarde ontbreekt voor concept «{concept_label}»")
            mapped = False

    return {
        "mapped":        mapped,
        "concept_uri":   concept_uri,
        "concept_label": concept_label,
        "issues":        issues,
    }


# ── Hoofd-functie: stap 2 validatie per schema ────────────────────────────────

def validate_concept_mapping(schema_key: str, rows: list[dict], field_map: dict) -> dict:
    """
    Valideert of de waarden in `rows` gemapped kunnen worden naar de KIK-V ontologieconcepten.

    Parameters
    ----------
    schema_key  : bijv. "werkovereenkomst"
    rows        : lijst van rij-dicts (genormaliseerde kolomnamen als keys)
    field_map   : {intern_veld: originele_kolomnaam} — output van auto_map()

    Returns
    -------
    {
        "schema":  str,
        "fields":  {veld: {concept_uri, concept_label, mapped_rows, unmapped_rows, issues_sample}},
        "summary": {total_fields, mapped_fields, mapping_score},
    }
    """
    schema_rules = FIELD_RULES.get(schema_key, {})
    field_results = {}

    for field, col_name in field_map.items():
        rules = schema_rules.get(field, {})
        if not rules.get("concept_uri"):
            continue  # geen ontologiekoppeling geconfigureerd

        concept_uri   = rules["concept_uri"]
        concept_label = rules.get("concept_label", concept_uri.split("#")[-1])
        mapped_count  = 0
        unmapped_count = 0
        issues_sample  = []

        for i, row in enumerate(rows):
            value = row.get(col_name, row.get(field, ""))
            result = _map_field(schema_key, field, value, rules)

            if result.get("skipped"):
                mapped_count += 1
                continue

            if result["mapped"]:
                mapped_count += 1
                # Verifieer dat het gemappe concept correct is (kan zijn verfijnd)
                concept_uri   = result["concept_uri"]
                concept_label = result["concept_label"]
            else:
                unmapped_count += 1
                if len(issues_sample) < 3:
                    issues_sample.append({
                        "row": i + 1,
                        "value": str(value)[:60],
                        "issues": result["issues"],
                    })

        total = mapped_count + unmapped_count

        # Hergebruik-info: in hoeveel uitwisselprofielen wordt dit concept gebruikt?
        hergebruik = get_hergebruik(concept_uri)

        field_results[field] = {
            "concept_uri":       concept_uri,
            "concept_label":     concept_label,
            "col_name":          col_name,
            "mapped_rows":       mapped_count,
            "unmapped_rows":     unmapped_count,
            "mapping_pct":       round(mapped_count / total * 100, 1) if total > 0 else 100,
            "issues_sample":     issues_sample,
            # KIK-V hergebruik (hoeveel uitwisselprofielen gebruiken dit concept)
            "hergebruik_count":  hergebruik["profile_count"] if hergebruik else None,
            "hergebruik_total":  _TOTAL_PROFILES,
            "hergebruik_profielen": hergebruik["profiles"] if hergebruik else [],
        }

    # Samenvatting
    fields_with_concept = [f for f, v in field_results.items() if v["unmapped_rows"] + v["mapped_rows"] > 0]
    fully_mapped = [f for f in fields_with_concept if field_results[f]["unmapped_rows"] == 0]

    # Score = gemiddelde mapping-percentage over alle velden met ontologiekoppeling
    if fields_with_concept:
        avg_pct = sum(field_results[f]["mapping_pct"] for f in fields_with_concept) / len(fields_with_concept)
        mapping_score = round(avg_pct, 1)
    else:
        mapping_score = 100.0

    return {
        "schema":  schema_key,
        "fields":  field_results,
        "summary": {
            "total_fields":  len(fields_with_concept),
            "mapped_fields": len(fully_mapped),
            "mapping_score": mapping_score,
        },
    }
