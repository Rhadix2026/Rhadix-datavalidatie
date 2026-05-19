"""
dashboard.py — Rhadix Index Dashboard API

Three access levels:
  GET /api/dashboard/me     — own runs (any authenticated user)
  GET /api/dashboard/org    — all runs within tenant (ORG_ADMIN + RHADIX_ADMIN)
  GET /api/dashboard/admin  — cross-tenant platform view (RHADIX_ADMIN only)

All queries enforce tenant isolation: an ORG_USER/ORG_ADMIN never sees data
from another tenant. RHADIX_ADMIN sees everything.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Integer, String, case, cast, extract, func, text
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.auth_models import License, Tenant, User, UserRole
from app.models.models import ValidationRun

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

# ── Helpers ───────────────────────────────────────────────────────────────────

def _period_expr(col):
    """
    Cross-dialect YYYY-MM expression for monthly grouping.
    Works on both PostgreSQL (production) and SQLite (tests).
    """
    year      = cast(extract("year",  col), Integer)
    month     = cast(extract("month", col), Integer)
    month_str = case((month < 10, "0" + cast(month, String)), else_=cast(month, String))
    return cast(year, String) + "-" + month_str


def _score_label(score: float | None) -> str:
    if score is None:
        return "onbekend"
    if score >= 90:
        return "Uitstekend"
    if score >= 75:
        return "Goed"
    if score >= 60:
        return "Voldoende"
    return "Onvoldoende"


def _run_to_dict(run: ValidationRun) -> dict:
    return {
        "run_id":            run.id,
        "label":             run.label,
        "created_at":        run.created_at.isoformat() if run.created_at else None,
        "standard":          run.standard,
        "score":             run.score,
        "structural_score":  run.structural_score,
        "relational_score":  run.relational_score,
        "use_case_score":    run.use_case_score,
        "source_system":     run.source_system,
        "score_label":       _score_label(run.score),
    }


def _safe_round(val, ndigits: int = 1):
    return round(float(val), ndigits) if val is not None else None


# ── GET /api/dashboard/me ─────────────────────────────────────────────────────

@router.get("/me")
def dashboard_me(
    standard: Optional[str] = Query(None, description="Filter op 'kikv', 'zib' of 'algemeen'"),
    limit:    int            = Query(50,   ge=1, le=200),
    db:       Session        = Depends(get_db),
    current_user: User       = Depends(get_current_user),
):
    """Own run history + trend. Accessible by every authenticated user."""
    q = (
        db.query(ValidationRun)
        .filter(
            ValidationRun.created_by == current_user.id,
            ValidationRun.tenant_id  == current_user.tenant_id,
        )
    )
    if standard:
        q = q.filter(ValidationRun.standard == standard.lower())

    runs = q.order_by(ValidationRun.created_at.desc()).limit(limit).all()

    # ── Total runs (respects standard filter) ─────────────────────────────────
    total_q = db.query(func.count(ValidationRun.id)).filter(
        ValidationRun.created_by == current_user.id,
        ValidationRun.tenant_id  == current_user.tenant_id,
    )
    if standard:
        total_q = total_q.filter(ValidationRun.standard == standard.lower())
    total_runs = total_q.scalar() or 0

    # ── By-standard aggregates (always across all standards, unfiltered) ──────
    agg_q = db.query(
        ValidationRun.standard,
        func.count(ValidationRun.id).label("run_count"),
        func.avg(ValidationRun.score).label("avg_score"),
    ).filter(
        ValidationRun.created_by == current_user.id,
        ValidationRun.tenant_id  == current_user.tenant_id,
    ).group_by(ValidationRun.standard).all()

    by_standard = {
        row.standard: {
            "run_count": row.run_count,
            "avg_score": _safe_round(row.avg_score),
        }
        for row in agg_q
        if row.standard
    }

    latest = runs[0] if runs else None

    # Trend: chronological order (oldest first) for chart
    trend = [
        {
            "run_id":     r.id,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "score":      r.score,
        }
        for r in reversed(runs[:24])
    ]

    return {
        "user_id":     str(current_user.id),
        "full_name":   current_user.full_name,
        "total_runs":  total_runs,
        "latest_run":  _run_to_dict(latest) if latest else None,
        "trend":       trend,
        "by_standard": by_standard,
    }


# ── GET /api/dashboard/org ────────────────────────────────────────────────────

@router.get("/org")
def dashboard_org(
    tenant_id: Optional[uuid.UUID] = Query(None, description="RHADIX_ADMIN only: filter op tenant"),
    standard:  Optional[str]       = Query(None),
    from_date: Optional[datetime]  = Query(None, alias="from"),
    to_date:   Optional[datetime]  = Query(None, alias="to"),
    db:        Session              = Depends(get_db),
    current_user: User              = Depends(get_current_user),
):
    """Organisation-level dashboard. ORG_ADMIN sees own tenant; RHADIX_ADMIN can specify tenant."""
    if current_user.role == UserRole.ORG_USER:
        raise HTTPException(403, "Organisatiedashboard vereist ORG_ADMIN of hogere rol.")

    # Determine which tenant to query
    if current_user.role == UserRole.RHADIX_ADMIN and tenant_id:
        target_tenant_id = tenant_id
    else:
        target_tenant_id = current_user.tenant_id

    tenant = db.query(Tenant).filter(Tenant.id == target_tenant_id).first()
    if not tenant:
        raise HTTPException(404, "Tenant niet gevonden.")

    base_filter = [ValidationRun.tenant_id == target_tenant_id]
    if standard:
        base_filter.append(ValidationRun.standard == standard.lower())
    if from_date:
        base_filter.append(ValidationRun.created_at >= from_date)
    if to_date:
        base_filter.append(ValidationRun.created_at <= to_date)

    # ── Summary ──────────────────────────────────────────────────────────────
    summary_row = db.query(
        func.count(ValidationRun.id).label("total_runs"),
        func.avg(ValidationRun.score).label("avg_score"),
        func.avg(ValidationRun.structural_score).label("avg_structural"),
        func.avg(ValidationRun.relational_score).label("avg_relational"),
        func.avg(ValidationRun.use_case_score).label("avg_use_case"),
        func.count(func.distinct(ValidationRun.created_by)).label("active_users"),
    ).filter(*base_filter).one()

    # ── Monthly trend ─────────────────────────────────────────────────────────
    trend_rows = db.query(
        _period_expr(ValidationRun.created_at).label("period"),
        func.count(ValidationRun.id).label("run_count"),
        func.avg(ValidationRun.score).label("avg_score"),
    ).filter(*base_filter).group_by("period").order_by("period").all()

    # ── By application ────────────────────────────────────────────────────────
    from app.models.auth_models import Application
    app_rows = db.query(
        ValidationRun.application_id,
        Application.name.label("app_name"),
        func.count(ValidationRun.id).label("run_count"),
        func.avg(ValidationRun.score).label("avg_score"),
        func.max(ValidationRun.score).label("latest_score"),
    ).outerjoin(
        Application, Application.id == ValidationRun.application_id
    ).filter(*base_filter).group_by(
        ValidationRun.application_id, Application.name
    ).all()

    # ── By user ───────────────────────────────────────────────────────────────
    user_rows = db.query(
        ValidationRun.created_by,
        User.full_name,
        func.count(ValidationRun.id).label("run_count"),
        func.avg(ValidationRun.score).label("avg_score"),
        func.max(ValidationRun.created_at).label("latest_run_at"),
    ).outerjoin(
        User, User.id == ValidationRun.created_by
    ).filter(*base_filter).group_by(
        ValidationRun.created_by, User.full_name
    ).all()

    # ── Top 5 runs ────────────────────────────────────────────────────────────
    top_runs = (
        db.query(ValidationRun)
        .filter(*base_filter, ValidationRun.score.isnot(None))
        .order_by(ValidationRun.score.desc())
        .limit(5)
        .all()
    )

    # ── Sector benchmark (anonymised, min 5 tenants) ──────────────────────────
    benchmark_standard = standard or "kikv"
    sector_benchmark = _compute_sector_benchmark(
        db, target_tenant_id, benchmark_standard, from_date, to_date
    )

    return {
        "tenant_id":   str(target_tenant_id),
        "tenant_name": tenant.name,
        "period": {
            "from": from_date.isoformat() if from_date else None,
            "to":   to_date.isoformat()   if to_date   else None,
        },
        "summary": {
            "total_runs":            summary_row.total_runs or 0,
            "active_users":          summary_row.active_users or 0,
            "avg_score":             _safe_round(summary_row.avg_score),
            "avg_structural_score":  _safe_round(summary_row.avg_structural),
            "avg_relational_score":  _safe_round(summary_row.avg_relational),
            "avg_use_case_score":    _safe_round(summary_row.avg_use_case),
        },
        "trend_monthly": [
            {
                "period":    row.period,
                "run_count": row.run_count,
                "avg_score": _safe_round(row.avg_score),
            }
            for row in trend_rows
        ],
        "by_application": [
            {
                "application_id":   str(row.application_id) if row.application_id else None,
                "application_name": row.app_name or "Onbekend",
                "run_count":        row.run_count,
                "avg_score":        _safe_round(row.avg_score),
                "latest_score":     _safe_round(row.latest_score),
            }
            for row in app_rows
            if row.run_count > 0
        ],
        "by_user": [
            {
                "user_id":       str(row.created_by) if row.created_by else None,
                "full_name":     row.full_name or "Onbekend",
                "run_count":     row.run_count,
                "avg_score":     _safe_round(row.avg_score),
                "latest_run_at": row.latest_run_at.isoformat() if row.latest_run_at else None,
            }
            for row in user_rows
            if row.run_count > 0
        ],
        "top_runs": [_run_to_dict(r) for r in top_runs],
        "sector_benchmark": sector_benchmark,
    }


def _compute_sector_benchmark(
    db: Session,
    tenant_id,
    standard: str,
    from_date: Optional[datetime],
    to_date: Optional[datetime],
) -> Optional[dict]:
    """
    Compute anonymised sector benchmark.
    Returns None if fewer than 5 tenants have data for this standard/period.
    Never exposes tenant identities to the caller.
    """
    filters = [
        ValidationRun.standard == standard,
        ValidationRun.score.isnot(None),
    ]
    if from_date:
        filters.append(ValidationRun.created_at >= from_date)
    if to_date:
        filters.append(ValidationRun.created_at <= to_date)

    # Per-tenant average subquery
    tenant_avgs = (
        db.query(
            ValidationRun.tenant_id.label("tid"),
            func.avg(ValidationRun.score).label("avg_score"),
        )
        .filter(*filters)
        .group_by(ValidationRun.tenant_id)
        .subquery()
    )

    agg = db.query(
        func.count(tenant_avgs.c.tid).label("participant_count"),
        func.avg(tenant_avgs.c.avg_score).label("sector_avg"),
    ).one()

    if (agg.participant_count or 0) < 5:
        return None

    # Collect per-tenant averages in Python for cross-dialect percentile calc
    scores_q = (
        db.query(func.avg(ValidationRun.score).label("avg_score"))
        .filter(*filters)
        .group_by(ValidationRun.tenant_id)
        .all()
    )
    scores = sorted([float(r.avg_score) for r in scores_q if r.avg_score is not None])

    def _percentile(data, p):
        if not data:
            return None
        idx = (len(data) - 1) * p
        lo, hi = int(idx), min(int(idx) + 1, len(data) - 1)
        return data[lo] + (data[hi] - data[lo]) * (idx - lo)

    p25 = _percentile(scores, 0.25)
    p50 = _percentile(scores, 0.50)
    p75 = _percentile(scores, 0.75)

    class _PctRow:
        pass
    pct_row = _PctRow()
    pct_row.p25, pct_row.p50, pct_row.p75 = p25, p50, p75

    # Own tenant average
    own_avg_row = db.query(
        func.avg(ValidationRun.score).label("own_avg")
    ).filter(
        *filters,
        ValidationRun.tenant_id == tenant_id,
    ).one()
    own_avg = float(own_avg_row.own_avg) if own_avg_row.own_avg else None

    # Approximate percentile rank for own tenant
    your_percentile = None
    if own_avg is not None and pct_row:
        p25 = float(pct_row.p25) if pct_row.p25 else None
        p50 = float(pct_row.p50) if pct_row.p50 else None
        p75 = float(pct_row.p75) if pct_row.p75 else None
        if p25 and p50 and p75:
            if own_avg <= p25:
                your_percentile = round(own_avg / p25 * 25)
            elif own_avg <= p50:
                your_percentile = round(25 + (own_avg - p25) / (p50 - p25) * 25)
            elif own_avg <= p75:
                your_percentile = round(50 + (own_avg - p50) / (p75 - p50) * 25)
            else:
                your_percentile = round(75 + min((own_avg - p75) / (100 - p75) * 25, 25))

    return {
        "note":                     "Geanonimiseerd — geen tenantidentiteit zichtbaar",
        "standard":                 standard,
        "participant_count":        agg.participant_count,
        "sector_avg_score":         _safe_round(agg.sector_avg),
        "percentile_25":            _safe_round(float(pct_row.p25)) if pct_row and pct_row.p25 else None,
        "percentile_50":            _safe_round(float(pct_row.p50)) if pct_row and pct_row.p50 else None,
        "percentile_75":            _safe_round(float(pct_row.p75)) if pct_row and pct_row.p75 else None,
        "your_score":               _safe_round(own_avg),
        "your_percentile":          your_percentile,
    }


# ── GET /api/dashboard/admin ──────────────────────────────────────────────────

@router.get("/admin")
def dashboard_admin(
    standard: Optional[str]      = Query(None),
    period:   Optional[str]      = Query(None, description="YYYY-MM filter, bijv. '2026-05'"),
    db:       Session             = Depends(get_db),
    current_user: User            = Depends(get_current_user),
):
    """Cross-tenant platform dashboard. RHADIX_ADMIN only."""
    if current_user.role != UserRole.RHADIX_ADMIN:
        raise HTTPException(403, "Platform dashboard is uitsluitend toegankelijk voor RHADIX_ADMIN.")

    base_filter = []
    if standard:
        base_filter.append(ValidationRun.standard == standard.lower())
    if period:
        base_filter.append(
            _period_expr(ValidationRun.created_at) == period
        )

    # ── Platform summary ──────────────────────────────────────────────────────
    total_tenants = db.query(func.count(Tenant.id)).filter(Tenant.is_active == True).scalar() or 0

    platform_agg = db.query(
        func.count(ValidationRun.id).label("total_runs"),
        func.avg(ValidationRun.score).label("avg_score"),
        func.count(func.distinct(ValidationRun.tenant_id)).label("active_tenants"),
    ).filter(*base_filter).one()

    # ── Per tenant ────────────────────────────────────────────────────────────
    tenant_rows = db.query(
        ValidationRun.tenant_id,
        Tenant.name.label("tenant_name"),
        func.count(ValidationRun.id).label("run_count"),
        func.avg(ValidationRun.score).label("avg_score"),
        func.max(ValidationRun.created_at).label("latest_run_at"),
    ).join(
        Tenant, Tenant.id == ValidationRun.tenant_id
    ).filter(*base_filter).group_by(
        ValidationRun.tenant_id, Tenant.name
    ).order_by(func.avg(ValidationRun.score).desc()).all()

    # Enrich with license status
    tenant_list = []
    for row in tenant_rows:
        active_lic = db.query(License).filter(
            License.tenant_id == row.tenant_id,
            License.is_active  == True,
        ).order_by(License.valid_until.desc().nullslast()).first()

        license_valid_until = None
        license_status = "geen"
        if active_lic:
            license_valid_until = active_lic.valid_until.isoformat() if active_lic.valid_until else None
            now = datetime.now(timezone.utc)
            if active_lic.valid_until is None:
                license_status = "active"
            elif active_lic.valid_until.replace(tzinfo=timezone.utc) >= now:
                license_status = "active"
            else:
                license_status = "verlopen"

        tenant_list.append({
            "tenant_id":           str(row.tenant_id),
            "tenant_name":         row.tenant_name,
            "run_count":           row.run_count,
            "avg_score":           _safe_round(row.avg_score),
            "score_label":         _score_label(row.avg_score),
            "latest_run_at":       row.latest_run_at.isoformat() if row.latest_run_at else None,
            "license_valid_until": license_valid_until,
            "license_status":      license_status,
        })

    # ── Platform trend (monthly) ──────────────────────────────────────────────
    platform_trend = db.query(
        _period_expr(ValidationRun.created_at).label("period"),
        func.count(ValidationRun.id).label("run_count"),
        func.avg(ValidationRun.score).label("avg_score"),
        func.count(func.distinct(ValidationRun.tenant_id)).label("tenant_count"),
    ).filter(*base_filter).group_by("period").order_by("period").all()

    # ── Benchmark distribution (over all tenant averages) ─────────────────────
    benchmark = _compute_platform_benchmark(db, base_filter)

    return {
        "platform_summary": {
            "total_tenants":              total_tenants,
            "active_tenants_this_period": platform_agg.active_tenants or 0,
            "total_runs":                 platform_agg.total_runs or 0,
            "platform_avg_score":         _safe_round(platform_agg.avg_score),
        },
        "per_tenant": tenant_list,
        "trend_platform_monthly": [
            {
                "period":       row.period,
                "run_count":    row.run_count,
                "avg_score":    _safe_round(row.avg_score),
                "tenant_count": row.tenant_count,
            }
            for row in platform_trend
        ],
        "benchmark": benchmark,
    }


def _compute_platform_benchmark(db: Session, base_filter: list) -> dict:
    """Platform-wide benchmark statistics across all tenant averages."""
    tenant_avgs = (
        db.query(
            ValidationRun.tenant_id,
            func.avg(ValidationRun.score).label("avg_score"),
        )
        .filter(*base_filter, ValidationRun.score.isnot(None))
        .group_by(ValidationRun.tenant_id)
        .subquery()
    )

    agg = db.query(
        func.count(tenant_avgs.c.tenant_id).label("n"),
        func.avg(tenant_avgs.c.avg_score).label("mean"),
        func.min(tenant_avgs.c.avg_score).label("min_score"),
        func.max(tenant_avgs.c.avg_score).label("max_score"),
    ).one()

    scores_q2 = (
        db.query(func.avg(ValidationRun.score).label("avg_score"))
        .filter(*base_filter, ValidationRun.score.isnot(None))
        .group_by(ValidationRun.tenant_id)
        .all()
    )
    scores2 = sorted([float(r.avg_score) for r in scores_q2 if r.avg_score is not None])

    def _pct(data, p):
        if not data:
            return None
        idx = (len(data) - 1) * p
        lo, hi = int(idx), min(int(idx) + 1, len(data) - 1)
        return data[lo] + (data[hi] - data[lo]) * (idx - lo)

    class _P:
        pass
    pct_row = _P()
    pct_row.p25, pct_row.p50, pct_row.p75 = _pct(scores2, 0.25), _pct(scores2, 0.50), _pct(scores2, 0.75)

    # Top performer (name visible to RHADIX_ADMIN)
    top = db.query(
        Tenant.name,
        func.avg(ValidationRun.score).label("avg_score"),
    ).join(Tenant, Tenant.id == ValidationRun.tenant_id).filter(
        *base_filter, ValidationRun.score.isnot(None)
    ).group_by(Tenant.name).order_by(
        func.avg(ValidationRun.score).desc()
    ).first()

    return {
        "participant_count": agg.n or 0,
        "mean":              _safe_round(agg.mean),
        "min_score":         _safe_round(agg.min_score),
        "max_score":         _safe_round(agg.max_score),
        "percentile_25":     _safe_round(float(pct_row.p25)) if pct_row and pct_row.p25 else None,
        "percentile_50":     _safe_round(float(pct_row.p50)) if pct_row and pct_row.p50 else None,
        "percentile_75":     _safe_round(float(pct_row.p75)) if pct_row and pct_row.p75 else None,
        "top_performer":     {"tenant_name": top[0], "avg_score": _safe_round(top[1])} if top else None,
    }
