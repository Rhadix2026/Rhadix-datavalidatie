from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import ValidationRun

router = APIRouter()

@router.get("/")
def list_runs(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    runs = db.query(ValidationRun).order_by(ValidationRun.created_at.desc()).offset(skip).limit(limit).all()
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
        }
        for r in runs
    ]

@router.get("/{run_id}")
def get_run(run_id: int, db: Session = Depends(get_db)):
    run = db.query(ValidationRun).filter(ValidationRun.id == run_id).first()
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
    }

@router.delete("/{run_id}")
def delete_run(run_id: int, db: Session = Depends(get_db)):
    run = db.query(ValidationRun).filter(ValidationRun.id == run_id).first()
    if not run:
        raise HTTPException(404, "Run not found")
    db.delete(run)
    db.commit()
    return {"deleted": run_id}

@router.get("/stats/summary")
def stats_summary(db: Session = Depends(get_db)):
    runs = db.query(ValidationRun).order_by(ValidationRun.created_at.desc()).limit(30).all()
    return {
        "total_runs":    len(runs),
        "avg_score":     round(sum(r.score for r in runs) / len(runs), 1) if runs else 0,
        "total_errors":  sum(r.error_count for r in runs),
        "total_rows":    sum(r.total_rows for r in runs),
        "recent":        [{"id":r.id,"label":r.label,"score":r.score,"created_at":r.created_at.isoformat(),"error_count":r.error_count} for r in runs[:5]],
    }
