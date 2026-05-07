"""
traceability.py — Centrale traceerbaarheid voor alle validatielagen
====================================================================
Post-verwerking: verrijkt bestaande issue-dicts met uniforme traceervelden.
Wijzigt GEEN bestaande scoringsfuncties; voegt alleen velden TOE.

Gebruik in validate.py:
    from app.services.traceability import enrich_issues, collect_all_issues
"""
from __future__ import annotations
import uuid
from typing import Optional

# ─── KIK-V metadata per schema + veld ────────────────────────────────────────
# kikv_domain / kikv_class / kikv_property / exchange_profiles / indicators
# Bron: KIK-V informatiestandaard v1.x (ONZ ontologie)

_KIKV_META: dict = {
    "medewerker": {
        "_domain": "Personeel",
        "personeelsnummer": {
            "kikv_class":    "Medewerker",
            "kikv_property": "personeelsnummer",
            "profiles":      ["KIK-V Basisset", "KIK-V Personeel"],
            "indicators":    ["IN-M-01", "IN-M-02"],
        },
        "geboortedatum": {
            "kikv_class":    "Medewerker",
            "kikv_property": "geboortedatum",
            "profiles":      ["KIK-V Basisset", "KIK-V Personeel"],
            "indicators":    ["IN-M-03"],
        },
    },
    "werkovereenkomst": {
        "_domain": "Arbeid",
        "overeenkomsttype": {
            "kikv_class":    "WerkOvereenkomst",
            "kikv_property": "overeenkomstType",
            "profiles":      ["KIK-V Basisset", "KIK-V Arbeidsrelaties"],
            "indicators":    ["IN-WO-01", "IN-WO-02"],
        },
        "startdatum": {
            "kikv_class":    "WerkOvereenkomst",
            "kikv_property": "startDatum",
            "profiles":      ["KIK-V Basisset", "KIK-V Arbeidsrelaties"],
            "indicators":    ["IN-WO-01"],
        },
        "einddatum": {
            "kikv_class":    "WerkOvereenkomst",
            "kikv_property": "eindDatum",
            "profiles":      ["KIK-V Arbeidsrelaties"],
            "indicators":    ["IN-WO-03"],
        },
        "personeelsnummer": {
            "kikv_class":    "WerkOvereenkomst",
            "kikv_property": "personeelsnummer",
            "profiles":      ["KIK-V Basisset"],
            "indicators":    ["IN-WO-01"],
        },
        "dienstverbandnummer": {
            "kikv_class":    "WerkOvereenkomst",
            "kikv_property": "dienstverbandIdentifier",
            "profiles":      ["KIK-V Basisset"],
            "indicators":    ["IN-WO-01"],
        },
        "urenperweek": {
            "kikv_class":    "WerkOvereenkomst",
            "kikv_property": "contractOmvang",
            "profiles":      ["KIK-V Arbeidsrelaties"],
            "indicators":    ["IN-WO-04"],
        },
        "overeenkomstoe": {
            "kikv_class":    "WerkOvereenkomst",
            "kikv_property": "organisatieEenheid",
            "profiles":      ["KIK-V Organisatie"],
            "indicators":    ["IN-WO-05"],
        },
    },
    "functie": {
        "_domain": "Kwalificatie",
        "functie": {
            "kikv_class":    "ZorgverlenerFunctie",
            "kikv_property": "functieBenaming",
            "profiles":      ["KIK-V Kwalificaties"],
            "indicators":    ["IN-F-01", "IN-F-02"],
        },
        "kwalificatieniveau": {
            "kikv_class":    "ZorgverlenerFunctie",
            "kikv_property": "kwalificatieNiveau",
            "profiles":      ["KIK-V Kwalificaties"],
            "indicators":    ["IN-F-03", "IN-F-04"],
        },
    },
    "verzuim": {
        "_domain": "Verzuim",
        "personeelsnummer": {
            "kikv_class":    "VerzuimPeriode",
            "kikv_property": "personeelsnummer",
            "profiles":      ["KIK-V Verzuim"],
            "indicators":    ["IN-V-01"],
        },
        "soortverzuim": {
            "kikv_class":    "VerzuimPeriode",
            "kikv_property": "soortVerzuim",
            "profiles":      ["KIK-V Verzuim"],
            "indicators":    ["IN-V-01", "IN-V-02"],
        },
        "startmoment": {
            "kikv_class":    "VerzuimPeriode",
            "kikv_property": "startDatum",
            "profiles":      ["KIK-V Verzuim"],
            "indicators":    ["IN-V-01"],
        },
        "eindmoment": {
            "kikv_class":    "VerzuimPeriode",
            "kikv_property": "eindDatum",
            "profiles":      ["KIK-V Verzuim"],
            "indicators":    ["IN-V-03"],
        },
        "verzuimpercentage": {
            "kikv_class":    "VerzuimPeriode",
            "kikv_property": "aoPercentage",
            "profiles":      ["KIK-V Verzuim"],
            "indicators":    ["IN-V-04"],
        },
    },
    # ZIB schemas
    "patient": {
        "_domain": "Patiënt",
        "bsn": {
            "kikv_class":    "Patient",
            "kikv_property": "burgerservicenummer",
            "profiles":      ["ZIB Patient"],
            "indicators":    ["ZIB-P-01"],
        },
        "geboortedatum": {
            "kikv_class":    "Patient",
            "kikv_property": "geboorteDatum",
            "profiles":      ["ZIB Patient"],
            "indicators":    ["ZIB-P-02"],
        },
    },
    "probleem": {
        "_domain": "Klinisch",
        "_default": {
            "kikv_class":    "Probleem",
            "kikv_property": None,
            "profiles":      ["ZIB Probleem"],
            "indicators":    ["ZIB-PR-01"],
        },
    },
    "medicatieafspraak": {
        "_domain": "Medicatie",
        "_default": {
            "kikv_class":    "MedicatieAfspraak",
            "kikv_property": None,
            "profiles":      ["ZIB MedicatieAfspraak"],
            "indicators":    ["ZIB-MA-01"],
        },
    },
    "allergie": {
        "_domain": "Klinisch",
        "_default": {
            "kikv_class":    "AllergieIntolerantie",
            "kikv_property": None,
            "profiles":      ["ZIB Allergie"],
            "indicators":    ["ZIB-AL-01"],
        },
    },
}

# Severiteit → impact op score (omschrijving)
_SEVERITY_IMPACT = {
    "error":   "Vermindert kwaliteitsscore; telt mee als fout in Rhadix Index.",
    "warning": "Vermindert kwaliteitsscore gedeeltelijk; telt mee als waarschuwing.",
    "info":    "Geen directe scorewijziging; informatief.",
}

# Validatielaag → mensleesbare naam
_LAYER_LABELS = {
    "prescan":          "Pre-scan (formaat)",
    "availability":     "Beschikbaarheid (stap 1)",
    "quality":          "Kwaliteit (stap 2)",
    "concept_mapping":  "Ontologie-mapping (stap 2)",
    "actuality":        "Actualiteit (tijdsdimensie)",
    "zib_availability": "ZIB Beschikbaarheid",
    "zib_quality":      "ZIB Kwaliteit",
}


def _lookup_kikv(schema_key: Optional[str], field_key: Optional[str]) -> dict:
    """Zoek KIK-V metadata op voor schema + veld. Geeft nulls bij onbekend."""
    if not schema_key or schema_key not in _KIKV_META:
        return {"kikv_domain": None, "kikv_class": None, "kikv_property": None,
                "impacted_exchange_profiles": None, "impacted_indicators": None}

    schema_meta = _KIKV_META[schema_key]
    domain = schema_meta.get("_domain")

    # Zoek veld op (genormaliseerd)
    norm_field = (field_key or "").lower().replace(" ", "").replace("_", "").replace("-", "")
    field_meta = None
    for k, v in schema_meta.items():
        if k.startswith("_"):
            continue
        if k.replace("_", "") == norm_field or k == field_key:
            field_meta = v
            break

    if field_meta is None:
        field_meta = schema_meta.get("_default", {})

    return {
        "kikv_domain":                domain,
        "kikv_class":                 field_meta.get("kikv_class"),
        "kikv_property":              field_meta.get("kikv_property"),
        "impacted_exchange_profiles": field_meta.get("profiles"),
        "impacted_indicators":        field_meta.get("indicators"),
    }


def _make_issue_id(layer: str, rule_id: Optional[str], source_file: str, source_row: Optional[int]) -> str:
    """Genereer deterministische issue-ID."""
    parts = [layer, rule_id or "unknown", source_file or "", str(source_row or "")]
    base = "_".join(p.replace("/", "-").replace(" ", "_") for p in parts)
    # Trim en voeg korte hash toe voor uniciteit
    short = base[:80]
    suffix = uuid.uuid5(uuid.NAMESPACE_DNS, base).hex[:6]
    return f"{short}_{suffix}"


def normalize_row_issue(
    row_item: dict,
    *,
    layer: str,
    source_file: str,
    schema_key: Optional[str] = None,
    rule_id: Optional[str] = None,
    severity: Optional[str] = None,
    supplier_object: Optional[str] = None,
    supplier_field: Optional[str] = None,
    impact_on_score: Optional[str] = None,
    suggested_fix_default: Optional[str] = None,
) -> dict:
    """
    Verrijkt één rij-item (uit issue["rows"]) met alle traceervelden.
    Bestaande velden worden NIET overschreven — alleen nieuwe worden toegevoegd.
    Geeft een nieuw dict terug (origineel ongewijzigd).
    """
    field_key  = row_item.get("field") or row_item.get("source_column")
    source_row = row_item.get("rowNumber") or row_item.get("source_row")
    current    = row_item.get("currentValue") or row_item.get("current_value", "")
    message    = row_item.get("message") or row_item.get("issue_description", "")
    sev        = row_item.get("severity") or severity or "warning"

    kikv = _lookup_kikv(schema_key, field_key)

    issue_id = _make_issue_id(layer, rule_id, source_file, source_row)

    trace = {
        "issue_id":                   issue_id,
        "validation_layer":           layer,
        "validation_layer_label":     _LAYER_LABELS.get(layer, layer),
        "source_file":                row_item.get("source_file") or source_file,
        "source_column":              field_key,
        "source_row":                 source_row,
        "current_value":              current,
        "supplier_reference_object":  supplier_object,
        "supplier_reference_field":   supplier_field,
        "kikv_domain":                kikv["kikv_domain"],
        "kikv_class":                 kikv["kikv_class"],
        "kikv_property":              kikv["kikv_property"],
        "rule_id":                    rule_id,
        "severity":                   sev,
        "issue_description":          message,
        "suggested_fix":              row_item.get("suggested_fix") or suggested_fix_default,
        "impact_on_score":            impact_on_score or _SEVERITY_IMPACT.get(sev),
        "impacted_exchange_profiles": kikv["impacted_exchange_profiles"],
        "impacted_indicators":        kikv["impacted_indicators"],
    }
    return {**row_item, **trace}


def enrich_issue_group(
    issue: dict,
    *,
    layer: str,
    source_file: str,
    schema_key: Optional[str] = None,
    supplier_object: Optional[str] = None,
    supplier_field: Optional[str] = None,
) -> None:
    """
    Verrijkt een groep-level issue IN-PLACE (het "issue" dict uit issues[]).
    Verrijkt ook elk item in issue["rows"][].
    """
    rule_id   = issue.get("id") or issue.get("rule_id")
    severity  = issue.get("severity", "warning")
    sev_fix   = None

    # Bepaal impact op score
    impact = _SEVERITY_IMPACT.get(severity)

    # Verrijk groep-level velden (alleen als ze ontbreken)
    issue.setdefault("validation_layer", layer)
    issue.setdefault("validation_layer_label", _LAYER_LABELS.get(layer, layer))
    issue.setdefault("source_file", source_file)
    issue.setdefault("rule_id", rule_id)
    issue.setdefault("impact_on_score", impact)

    # Probeer field_key te achterhalen uit label of eerste row
    rows = issue.get("rows", [])
    first_row_field = rows[0].get("field") if rows else None
    label_field = issue.get("fieldLabel")
    field_key_hint = label_field or first_row_field

    kikv = _lookup_kikv(schema_key, field_key_hint)
    issue.setdefault("kikv_domain",                kikv["kikv_domain"])
    issue.setdefault("kikv_class",                 kikv["kikv_class"])
    issue.setdefault("kikv_property",              kikv["kikv_property"])
    issue.setdefault("impacted_exchange_profiles", kikv["impacted_exchange_profiles"])
    issue.setdefault("impacted_indicators",        kikv["impacted_indicators"])

    # Verrijk rij-items
    enriched_rows = []
    for row in rows:
        enriched = normalize_row_issue(
            row,
            layer=layer,
            source_file=source_file,
            schema_key=schema_key,
            rule_id=rule_id,
            severity=severity,
            supplier_object=supplier_object,
            supplier_field=supplier_field,
            impact_on_score=impact,
        )
        enriched_rows.append(enriched)
    issue["rows"] = enriched_rows


def enrich_file_result(
    file_result: dict,
    *,
    layer: str,
    source_file: str,
    schema_key: Optional[str] = None,
    supplier_object: Optional[str] = None,
) -> None:
    """Verrijkt alle issues in één file_result IN-PLACE."""
    for issue in file_result.get("issues", []):
        enrich_issue_group(
            issue,
            layer=layer,
            source_file=source_file,
            schema_key=schema_key,
            supplier_object=supplier_object,
        )


def collect_all_issues(
    kikv_result: Optional[dict] = None,
    zib_result: Optional[dict] = None,
    actuality_results: Optional[list] = None,
) -> list[dict]:
    """
    Verzamelt ALLE verrijkte rij-issues uit alle validatielagen in één platte lijst.
    Bedoeld voor de drilldown-tabel in de frontend.

    Geeft een lijst van genormaliseerde trace-dicts terug.
    """
    all_issues: list[dict] = []

    # ── KIK-V: issues per file ──────────────────────────────────────────────
    if kikv_result:
        for fsum in kikv_result.get("files_summary", []):
            fname = fsum.get("filename", "")
            for issue in fsum.get("issues", []):
                for row in issue.get("rows", []):
                    # Rij-items zijn al verrijkt door enrich_file_result
                    if "issue_id" in row:
                        all_issues.append(row)
                    else:
                        # Fallback normalisatie
                        all_issues.append(normalize_row_issue(
                            row,
                            layer=issue.get("validation_layer", "quality"),
                            source_file=fname,
                            rule_id=issue.get("id"),
                            severity=issue.get("severity"),
                        ))

    # ── ZIB: issues per file_result ─────────────────────────────────────────
    if zib_result:
        for fr in zib_result.get("file_results", []):
            fname = fr.get("filename", "")
            sk    = fr.get("schema_key")
            for issue in fr.get("issues", []):
                for row in issue.get("rows", []):
                    if "issue_id" in row:
                        all_issues.append(row)
                    else:
                        all_issues.append(normalize_row_issue(
                            row,
                            layer=issue.get("validation_layer", "zib_quality"),
                            source_file=fname,
                            schema_key=sk,
                            severity=issue.get("severity"),
                        ))

    # ── Actualiteit: outdated + inconsistent ────────────────────────────────
    if actuality_results:
        for ar in actuality_results:
            fname = ar.get("filename", "")
            for item in ar.get("outdated", []):
                if "issue_id" in item:
                    all_issues.append(item)
                else:
                    all_issues.append(normalize_row_issue(
                        item, layer="actuality", source_file=fname,
                        severity="warning",
                        suggested_fix_default="Actualiseer de mutatiedatum",
                    ))
            for item in ar.get("inconsistent", []):
                if "issue_id" in item:
                    all_issues.append(item)
                else:
                    all_issues.append(normalize_row_issue(
                        item, layer="actuality", source_file=fname,
                        severity="error",
                        suggested_fix_default="Herstel de datum-volgorde (start ≤ eind)",
                    ))

    return all_issues
