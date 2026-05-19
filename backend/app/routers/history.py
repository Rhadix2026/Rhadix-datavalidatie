from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.auth_models import User, UserRole
from app.models.models import ValidationRun

router = APIRouter()


def _tenant_filter(query, user: User):
    """Apply tenant isolation unless the caller is a RHADIX_ADMIN."""
    if user.role == UserRole.RHADIX_ADMIN:
        return query
    return query.filter(ValidationRun.tenant_id == user.tenant_id)


@router.get("/")
def list_runs(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q    = _tenant_filter(db.query(ValidationRun), current_user)
    runs = q.order_by(ValidationRun.created_at.desc()).offset(skip).limit(limit).all()
    return [
        {
            "id":          r.id,
            "label":       r.label,
            "created_at":  r.created_at.isoformat(),
            "files":       r.files,
            "total_rows":  r.total_rows,
            "error_count": r.error_count,
            "warn_count":  r.warn_count,
            "score":       r.score,
            "status":      r.status,
            "standard":    r.standard,
        }
        for r in runs
    ]


@router.get("/stats/summary")
def stats_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q    = _tenant_filter(db.query(ValidationRun), current_user)
    runs = q.order_by(ValidationRun.created_at.desc()).limit(30).all()
    return {
        "total_runs":   len(runs),
        "avg_score":    round(sum(r.score for r in runs) / len(runs), 1) if runs else 0,
        "total_errors": sum(r.error_count for r in runs),
        "total_rows":   sum(r.total_rows  for r in runs),
        "recent":       [
            {
                "id":          r.id,
                "label":       r.label,
                "score":       r.score,
                "created_at":  r.created_at.isoformat(),
                "error_count": r.error_count,
            }
            for r in runs[:5]
        ],
    }


@router.get("/{run_id}")
def get_run(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q   = _tenant_filter(db.query(ValidationRun), current_user)
    run = q.filter(ValidationRun.id == run_id).first()
    if not run:
        raise HTTPException(404, "Run not found")
    return {
        "id":          run.id,
        "label":       run.label,
        "created_at":  run.created_at.isoformat(),
        "files":       run.files,
        "results":     run.results,
        "total_rows":  run.total_rows,
        "error_count": run.error_count,
        "warn_count":  run.warn_count,
        "score":       run.score,
        "status":      run.status,
        "standard":    run.standard,
    }


@router.delete("/{run_id}")
def delete_run(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q   = _tenant_filter(db.query(ValidationRun), current_user)
    run = q.filter(ValidationRun.id == run_id).first()
    if not run:
        raise HTTPException(404, "Run not found")
    db.delete(run)
    db.commit()
    return {"deleted": run_id}
