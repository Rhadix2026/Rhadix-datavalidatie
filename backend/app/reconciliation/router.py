"""
Rhadix Reconciliation Engine — FastAPI router
Voeg toe aan main.py:
    from app.reconciliation.router import router as recon_router
    app.include_router(recon_router, prefix="/api/reconciliation", tags=["Reconciliation"])
"""

from __future__ import annotations

import io
import json
import math
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

# Profiles dir voor SPARQL-opzoeken
_PROFILES_DIR = Path(__file__).parent.parent.parent / "data" / "profiles"

from .calculation_engine import CalculationEngine
from .reconciliation_engine import (
    BatchReconciliationResult,
    ReconciliationEngine,
    ReconciliationResult,
    ReconciliationStatus,
    SPARQLEngine,
)
from .rule_engine import RuleEngine
from .calculation_engine import DataLoader
from . import rdf_store
from app.services import ontology_index
from app.services.sparql_validator import _FIELD_PREDICATE as _KIKV_PREDICATES, _SCHEMA_CLASS as _KIKV_CLASSES


def _sanitize(obj):
    """Vervang NaN/Inf/Timestamp door JSON-serialiseerbare waarden.
    Behandelt ook pandas Timestamps die ontstaan bij XML-import met datumvelden.
    """
    import datetime
    import pandas as pd
    if obj is None:
        return None
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if isinstance(obj, (pd.Timestamp, datetime.datetime, datetime.date)):
        return obj.isoformat() if not pd.isnull(obj) else None
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    return obj

router = APIRouter()

RULES_DIR = Path(__file__).parent / "rules"

_rule_engine = RuleEngine()
if RULES_DIR.exists():
    _rule_engine.load_directory(RULES_DIR)

_sparql_engine = SPARQLEngine()
_calc_engine = CalculationEngine()
_recon_engine = ReconciliationEngine(sparql_engine=_sparql_engine)


@router.get("/indicators/{indicator_id}/sparql-query")
def get_sparql_query(indicator_id: str):
    """Geeft de SPARQL-query terug die bij deze indicator hoort."""
    try:
        rule = _rule_engine.get(indicator_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Indicator niet gevonden: {indicator_id}")
    if not rule.sparql_query:
        raise HTTPException(status_code=404, detail="Deze indicator heeft geen SPARQL-query geconfigureerd.")
    return {
        "indicator_id": rule.indicator_id,
        "name": rule.name,
        "sparql_query": rule.sparql_query,
        "sparql_endpoint": rule.sparql_endpoint,
    }


@router.get("/indicators")
def list_indicators():
    return _rule_engine.to_dict()


@router.get("/indicators/{indicator_id}")
def get_indicator(indicator_id: str):
    try:
        return _rule_engine.get(indicator_id).dict()
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Indicator niet gevonden: {indicator_id}")


@router.post("/calculate/{indicator_id}")
async def calculate_indicator(indicator_id: str, file: UploadFile = File(...)):
    try:
        rule = _rule_engine.get(indicator_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Indicator niet gevonden: {indicator_id}")
    contents = await file.read()
    try:
        result = _calc_engine.calculate(rule, source=io.BytesIO(contents))
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return JSONResponse(content=_sanitize({
        "indicator_id": result.indicator_id,
        "expected_value": result.expected_value,
        "record_count": result.record_count,
        "excluded_count": len(result.excluded_records),
        "metadata": result.metadata,
        "included_sample": result.included_records[:100],
        "excluded_sample": result.excluded_records[:100],
    }))


@router.post("/reconcile/{indicator_id}")
async def reconcile_indicator(
    indicator_id: str,
    file: UploadFile = File(...),
    actual_value: float | None = Form(default=None),
    sparql_endpoint: str | None = Form(default=None),
    sparql_query: str | None = Form(default=None),
):
    try:
        rule = _rule_engine.get(indicator_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Indicator niet gevonden: {indicator_id}")
    contents = await file.read()
    try:
        calc = _calc_engine.calculate(rule, source=io.BytesIO(contents))
        recon = _recon_engine.reconcile(
            rule, calc,
            actual_value=actual_value,
            sparql_query_override=sparql_query or None,
            sparql_endpoint_override=sparql_endpoint or None,
        )
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return JSONResponse(content=recon.to_dict())


# ── SPARQL-op-data (Reconciliation Engine — handmatig) ─────────────────────────

# Veelgebruikte record-classes bovenaan de dropdown
_COMMON_CLASSES = [
    "http://purl.org/ozo/onz-pers#Medewerker",
    "http://purl.org/ozo/onz-pers#WerkOvereenkomst",
    "http://purl.org/ozo/onz-pers#WerkOvereenkomstAfspraak",
    "http://purl.org/ozo/onz-pers#ArbeidsOvereenkomst",
    "http://purl.org/ozo/onz-pers#ZorgverlenerFunctie",
    "http://purl.org/ozo/onz-zorg#Client",
    "http://purl.org/ozo/onz-org#Vestiging",
    "http://purl.org/ozo/onz-fin#Grootboekpost",
    "http://purl.org/ozo/onz-fin#Grootboekrubriek",
    "http://purl.org/ozo/onz-fin#Kostenplaats",
]


def _concept_entry(uri: str) -> dict:
    c = ontology_index.CONCEPTS.get(uri, {})
    return {
        "uri": uri,
        "name": c.get("name") or uri.split("#")[-1],
        "label": c.get("label_nl") or c.get("name") or uri.split("#")[-1],
        "module": c.get("module", ""),
        "common": uri in _COMMON_CLASSES,
    }


def _property_entry(uri: str) -> dict:
    p = ontology_index.PROPERTIES.get(uri, {})
    return {
        "uri": uri,
        "name": p.get("name") or uri.split("#")[-1],
        "label": p.get("label_nl") or p.get("name") or uri.split("#")[-1],
        "module": p.get("module", ""),
    }


@router.get("/concepts")
def list_concepts():
    """Concepten (classes) en eigenschappen (properties) voor de kolom->concept mapping-UI."""
    classes = [_concept_entry(u) for u in ontology_index.CONCEPTS.keys()]
    # gangbare classes eerst, dan alfabetisch op label
    classes.sort(key=lambda c: (not c["common"], c["label"].lower()))
    prop_uris = set(ontology_index.PROPERTIES.keys())
    properties = [_property_entry(u) for u in prop_uris]
    # voeg de curated KIK-V-predicaten toe die de uitwisselprofiel-queries gebruiken
    for fld, uri in _KIKV_PREDICATES.items():
        if uri not in prop_uris:
            properties.append({"uri": uri, "name": uri.split("#")[-1],
                               "label": uri.split("#")[-1], "module": "kik-v", "kikv": True})
            prop_uris.add(uri)
    properties.sort(key=lambda p: (not p.get("kikv", False), p["label"].lower()))
    return {
        "classes": classes,
        "properties": properties,
        "common_classes": _COMMON_CLASSES,
    }


# kolom-keyword → (concept_uri, datatype) voor auto-suggestie
_SUGGEST_KEYWORDS = {
    "personeelsnummer": ("http://purl.org/ozo/onz-g#personeelsnummer", "string"),
    "medewerkernummer": ("http://purl.org/ozo/onz-g#personeelsnummer", "string"),
    "medewerkerid": ("http://purl.org/ozo/onz-g#personeelsnummer", "string"),
    "geboortedatum": ("http://purl.org/ozo/onz-g#geboortedatum", "date"),
    "startdatum": ("http://purl.org/ozo/onz-g#startDatum", "date"),
    "begindatum": ("http://purl.org/ozo/onz-g#startDatum", "date"),
    "einddatum": ("http://purl.org/ozo/onz-g#eindDatum", "date"),
    "startmoment": ("http://purl.org/ozo/onz-g#startDatum", "date"),
    "eindmoment": ("http://purl.org/ozo/onz-g#eindDatum", "date"),
    "urenperweek": ("http://purl.org/ozo/onz-pers#contractOmvang", "decimal"),
    "contractomvang": ("http://purl.org/ozo/onz-pers#contractOmvang", "decimal"),
    "functie": ("http://purl.org/ozo/onz-pers#functieBenaming", "string"),
    "kwalificatieniveau": ("http://purl.org/ozo/onz-pers#kwalificatieNiveau", "string"),
    "soortverzuim": ("http://purl.org/ozo/onz-pers#soortVerzuim", "string"),
    "verzuimpercentage": ("http://purl.org/ozo/onz-pers#aoPercentage", "decimal"),
    "overeenkomsttype": ("http://purl.org/ozo/onz-pers#overeenkomstType", "string"),
    "contracttype": ("http://purl.org/ozo/onz-pers#overeenkomstType", "string"),
    "dienstverbandnummer": ("http://purl.org/ozo/onz-g#dienstverbandIdentifier", "string"),
}


def _suggest_concept(column: str) -> dict | None:
    """Suggestie: eerst curated KIK-V-keywords, dan property-naam/-label."""
    key = column.strip().lower().replace("_", "").replace(" ", "")
    if not key:
        return None
    if key in _SUGGEST_KEYWORDS:
        uri, dt = _SUGGEST_KEYWORDS[key]
        return {"concept_uri": uri, "kind": "literal", "datatype": dt}
    best = None
    for uri, p in ontology_index.PROPERTIES.items():
        name = (p.get("name") or "").lower().replace("_", "")
        lbl = (p.get("label_nl") or "").lower().replace(" ", "")
        if key == name or (lbl and key == lbl):
            return {"concept_uri": uri, "kind": "literal", "datatype": "string"}
        if best is None and (key in name or (name and name in key)):
            best = {"concept_uri": uri, "kind": "literal", "datatype": "string"}
    return best


@router.post("/preview-columns")
async def preview_columns(file: UploadFile = File(...)):
    """Lees de kolommen + een paar voorbeeldrijen uit een geupload bestand (CSV/Excel/XML)."""
    contents = await file.read()
    try:
        df = DataLoader.load(io.BytesIO(contents))
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Kon bestand niet lezen: {exc}")
    columns = [str(c) for c in df.columns]
    sample = _sanitize(df.head(5).to_dict(orient="records"))
    suggestions = {col: _suggest_concept(col) for col in columns}
    return JSONResponse(content=_sanitize({
        "filename": file.filename,
        "columns": columns,
        "row_count": int(len(df)),
        "sample_rows": sample,
        "suggested_mapping": {k: v for k, v in suggestions.items() if v},
    }))


@router.post("/sparql-reconcile")
async def sparql_reconcile(
    file: UploadFile = File(...),
    sparql_query: str = Form(...),
    mapping: str = Form(...),                       # JSON: {kolom: {concept_uri, kind, datatype}}
    class_uri: str | None = Form(default=None),
    id_field: str | None = Form(default=None),
    indicator_id: str | None = Form(default=None),  # berekeningsregel voor CSV-uitkomst (optioneel)
    prefer_fuseki: bool = Form(default=True),
):
    """
    Laat de geselecteerde SPARQL-query los op de geuploade brondata:
    brondata -> RDF-triples (volgens mapping) -> triple store (Fuseki/rdflib) -> SPARQL -> resultaat.

    Als een indicator_id (berekeningsregel) is meegegeven, wordt ook de CSV-uitkomst
    berekend en vergeleken met de SPARQL-uitkomst.
    """
    try:
        mapping_dict = json.loads(mapping) if mapping else {}
    except Exception:
        raise HTTPException(status_code=400, detail="mapping moet geldige JSON zijn.")
    if not isinstance(mapping_dict, dict):
        raise HTTPException(status_code=400, detail="mapping moet een JSON-object zijn.")

    contents = await file.read()

    # ── Brondata -> records ──────────────────────────────────────────────────
    try:
        df = DataLoader.load(io.BytesIO(contents))
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Kon bestand niet lezen: {exc}")
    records = _sanitize(df.to_dict(orient="records"))

    # ── SPARQL op de triples ─────────────────────────────────────────────────
    try:
        run = rdf_store.run_sparql_on_records(
            records=records,
            mapping=mapping_dict,
            sparql=sparql_query,
            class_uri=class_uri or None,
            id_field=id_field or None,
            prefer_fuseki=prefer_fuseki,
        )
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Triple-generatie/SPARQL faalde: {exc}")

    response: dict = {
        "sparql_result": run.to_dict(),
        "row_count": int(len(df)),
        "columns": [str(c) for c in df.columns],
    }

    # ── Optioneel: vergelijk met CSV-berekeningsregel ────────────────────────
    if indicator_id:
        try:
            rule = _rule_engine.get(indicator_id)
            calc = _calc_engine.calculate(rule, source=io.BytesIO(contents))
            recon = _recon_engine.reconcile(
                rule, calc,
                actual_value=run.scalar,   # SPARQL-uitkomst als 'werkelijke' waarde
            )
            response["calculation"] = {
                "indicator_id": calc.indicator_id,
                "expected_value": calc.expected_value,
                "record_count": calc.record_count,
            }
            response["reconciliation"] = recon.to_dict()
        except KeyError:
            response["calculation_error"] = f"Berekeningsregel niet gevonden: {indicator_id}"
        except Exception as exc:
            response["calculation_error"] = str(exc)

    return JSONResponse(content=_sanitize(response))


@router.post("/batch")
async def batch_reconcile(
    indicator_ids: str = Form(...),   # JSON-array als string: '["id1","id2"]'
    files: list[UploadFile] = File(...),
    actual_values: str = Form(default="{}"),
):
    try:
        ids = json.loads(indicator_ids)
        actuals = json.loads(actual_values)
    except Exception:
        raise HTTPException(status_code=400, detail="indicator_ids en actual_values moeten geldige JSON zijn.")

    if len(ids) != len(files):
        raise HTTPException(status_code=400, detail="Aantal indicator_ids en files moet gelijk zijn.")

    results = []
    for ind_id, upload in zip(ids, files):
        try:
            rule = _rule_engine.get(ind_id)
            contents = await upload.read()
            calc = _calc_engine.calculate(rule, source=io.BytesIO(contents))
            recon = _recon_engine.reconcile(rule, calc, actual_value=actuals.get(ind_id))
            results.append(recon)
        except Exception as exc:
            results.append(ReconciliationResult(
                indicator_id=ind_id, indicator_name=ind_id,
                expected_value=None, actual_value=None,
                absolute_difference=None, percentage_difference=None,
                status=ReconciliationStatus.UNKNOWN,
                confidence_score=0.0, reconciliation_score_label="Unknown",
                metadata={"error": str(exc)},
            ))

    batch = BatchReconciliationResult(results=results)
    return JSONResponse(content=batch.to_dict())


# ── Happy Flow Batch ──────────────────────────────────────────────────────────

def _load_profile_sparqls(profile_filename: str) -> dict[str, dict]:
    """Laad alle indicator-SPARQLs uit een opgeslagen profiel.
    Geeft dict terug: {indicator_id: {id, title, sparql_query}}
    """
    if not profile_filename:
        return {}
    path = _PROFILES_DIR / profile_filename
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        indicators = data.get("indicators", {})
        out = {}
        if isinstance(indicators, list):
            for ind in indicators:
                ind_id = ind.get("id") or ind.get("indicator_id", "")
                sparql_raw = ind.get("sparql_query") or ind.get("files", {}).get("sparql", {}).get("raw", "")
                if sparql_raw:
                    out[ind_id] = {
                        "id": ind_id,
                        "title": ind.get("title") or ind.get("metadata", {}).get("title", ind_id),
                        "sparql_query": sparql_raw,
                    }
        else:
            for k, v in indicators.items():
                if k == "-INDEX":
                    continue
                sparql_raw = v.get("files", {}).get("sparql", {}).get("raw", "")
                if sparql_raw:
                    out[k] = {
                        "id": k,
                        "title": v.get("metadata", {}).get("title", k),
                        "sparql_query": sparql_raw,
                    }
        return out
    except Exception:
        return {}


@router.post("/happy-flow/batch")
async def happy_flow_batch(
    files: list[UploadFile] = File(...),
    profile_filename: str = Form(default=""),
):
    """
    Upload meerdere happy flow CSV-bestanden tegelijk.

    Het systeem herkent automatisch welke berekeningsregels van toepassing zijn
    op basis van de bestandsnaam (source_dataset in de YAML-regels).

    Optioneel: geef een profile_filename mee om per indicator ook de bijbehorende
    SPARQL-query uit het geïmporteerde KIK-V-profiel terug te krijgen.

    Retourneert alle berekende indicatorwaarden gegroepeerd per dataset.
    """
    # ── Lees alle bestanden in één keer ──────────────────────────────────────
    file_contents: dict[str, bytes] = {}
    for upload in files:
        filename = (upload.filename or "").strip()
        if filename:
            file_contents[filename] = await upload.read()

    if not file_contents:
        raise HTTPException(status_code=400, detail="Geen geldige bestanden ontvangen.")

    # ── Laad optioneel profiel-SPARQLs ────────────────────────────────────────
    profile_sparqls = _load_profile_sparqls(profile_filename) if profile_filename else {}

    # ── Bereken alle indicatoren die matchen op bestandsnaam ─────────────────
    happy_flow_rules = [r for r in _rule_engine.list_rules() if "happy_flow" in r.tags]

    results = []
    skipped_files = []  # bestanden waarvoor geen regels gevonden zijn
    matched_files = set()

    for rule in happy_flow_rules:
        if rule.source_dataset not in file_contents:
            continue
        matched_files.add(rule.source_dataset)
        try:
            contents = file_contents[rule.source_dataset]
            calc = _calc_engine.calculate(rule, source=io.BytesIO(contents))
            # Maak een ReconciliationResult zonder SPARQL (status UNKNOWN)
            recon = _recon_engine.reconcile(rule, calc, actual_value=None)
            # Voeg de SPARQL-query toe als vrije tekst (niet uitvoerbaar)
            result_dict = recon.to_dict()
            result_dict["source_dataset"] = rule.source_dataset
            result_dict["tags"] = rule.tags
            result_dict["record_count"] = calc.record_count
            result_dict["total_rows"] = calc.metadata.get("total_rows", 0)
            results.append(result_dict)
        except Exception as exc:
            results.append({
                "indicator_id": rule.indicator_id,
                "indicator_name": rule.name,
                "source_dataset": rule.source_dataset,
                "tags": rule.tags,
                "expected_value": None,
                "actual_value": None,
                "absolute_difference": None,
                "percentage_difference": None,
                "status": "Unknown",
                "confidence_score": 0.0,
                "reconciliation_score_label": "Fout",
                "record_count": 0,
                "total_rows": 0,
                "metadata": {"error": str(exc)},
                "drill_down": [],
            })

    # ── Bepaal niet-gematchte bestanden ───────────────────────────────────────
    for filename in file_contents:
        if filename not in matched_files:
            skipped_files.append(filename)

    # ── Groepeer resultaten per dataset ───────────────────────────────────────
    datasets: dict[str, list] = {}
    for r in results:
        ds = r.get("source_dataset", "onbekend")
        if ds not in datasets:
            datasets[ds] = []
        datasets[ds].append(r)

    return JSONResponse(content=_sanitize({
        "total_indicators": len(results),
        "total_datasets": len(datasets),
        "skipped_files": skipped_files,
        "profile_sparqls_available": len(profile_sparqls),
        "profile_sparqls": profile_sparqls,
        "datasets": datasets,
        "all_results": results,
    }))


@router.get("/happy-flow/rules")
def list_happy_flow_rules():
    """Geeft alle happy flow berekeningsregels terug (indicatoren gegroepeerd per dataset)."""
    hf_rules = [r.dict() for r in _rule_engine.list_rules() if "happy_flow" in r.tags]
    by_dataset: dict[str, list] = {}
    for r in hf_rules:
        ds = r["source_dataset"]
        if ds not in by_dataset:
            by_dataset[ds] = []
        by_dataset[ds].append(r)
    return {"rules": hf_rules, "by_dataset": by_dataset}
