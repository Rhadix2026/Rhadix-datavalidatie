"""
Rhadix Reconciliation Engine — FastAPI router
Voeg toe aan main.py:
    from app.reconciliation.router import router as recon_router
    app.include_router(recon_router, prefix="/api/reconciliation", tags=["Reconciliation"])
"""

from __future__ import annotations

import io
import json
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from .calculation_engine import CalculationEngine
from .reconciliation_engine import (
    BatchReconciliationResult,
    ReconciliationEngine,
    ReconciliationResult,
    ReconciliationStatus,
    SPARQLEngine,
)
from .rule_engine import RuleEngine

router = APIRouter()

RULES_DIR = Path(__file__).parent / "rules"

_rule_engine = RuleEngine()
if RULES_DIR.exists():
    _rule_engine.load_directory(RULES_DIR)

_sparql_engine = SPARQLEngine()
_calc_engine = CalculationEngine()
_recon_engine = ReconciliationEngine(sparql_engine=_sparql_engine)


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
    return {
        "indicator_id": result.indicator_id,
        "expected_value": result.expected_value,
        "record_count": result.record_count,
        "excluded_count": len(result.excluded_records),
        "metadata": result.metadata,
        "included_sample": result.included_records[:100],
        "excluded_sample": result.excluded_records[:100],
    }


@router.post("/reconcile/{indicator_id}")
async def reconcile_indicator(
    indicator_id: str,
    file: UploadFile = File(...),
    actual_value: float | None = Form(default=None),
    sparql_endpoint: str | None = Form(default=None),
):
    try:
        rule = _rule_engine.get(indicator_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Indicator niet gevonden: {indicator_id}")
    if sparql_endpoint:
        rule = rule.copy(update={"sparql_endpoint": sparql_endpoint})
    contents = await file.read()
    try:
        calc = _calc_engine.calculate(rule, source=io.BytesIO(contents))
        recon = _recon_engine.reconcile(rule, calc, actual_value=actual_value)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return JSONResponse(content=recon.to_dict())


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
