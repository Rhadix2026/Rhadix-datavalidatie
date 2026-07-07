"""
tasks.py — Generieke taken-/workflow-API voor het Rhadix-platform.

Eindpunten (mount: /api/tasks):
  GET    /api/tasks                 — lijst (scope=mine|created|all, filters status/assignee)
  GET    /api/tasks/summary         — telling open taken (badge op dashboard)
  GET    /api/tasks/assignable-users— gebruikers binnen eigen tenant (toewijs-dropdown)
  POST   /api/tasks                 — taak aanmaken
  POST   /api/tasks/bulk            — meerdere taken aanmaken (bv. uit AFAS-bevindingen)
  PATCH  /api/tasks/{task_id}       — taak bijwerken (status/toewijzing/velden)
  DELETE /api/tasks/{task_id}       — taak verwijderen

Tenant-gescoped: een gebruiker ziet/raakt alleen taken binnen de eigen tenant.
Toewijzen kan uitsluitend aan gebruikers binnen dezelfde tenant.
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.auth_models import User, UserRole
from app.models.task_models import Task, TaskStatus, TaskPriority
from app.services import mailer

router = APIRouter(tags=["Tasks"])

_STATUSES   = {s.value for s in TaskStatus}
_PRIORITIES = {p.value for p in TaskPriority}
APP_SLUG    = "kikv-validator"   # per app anders; CRM zet 'rhadix-crm'


# ─── helpers ──────────────────────────────────────────────────────────────────

def _uuid(val, label="ID"):
    if val in (None, ""):
        return None
    try:
        return uuid.UUID(str(val))
    except (ValueError, AttributeError):
        raise HTTPException(400, f"Ongeldige {label}: {val!r}")

def _is_admin(user: User) -> bool:
    return user.role in (UserRole.ORG_ADMIN, UserRole.RHADIX_ADMIN)

def _tenant_users(db: Session, tenant_id):
    return db.query(User).filter(User.tenant_id == tenant_id, User.is_active == True).all()

def _validate_assignee(db: Session, assignee_id, tenant_id):
    """Assignee moet een actieve gebruiker binnen dezelfde tenant zijn."""
    if assignee_id is None:
        return None
    u = db.query(User).filter(User.id == assignee_id, User.is_active == True).first()
    if not u or u.tenant_id != tenant_id:
        raise HTTPException(400, "Toegewezen gebruiker hoort niet bij deze organisatie")
    return u.id

def _name(u: Optional[User]):
    if not u:
        return None
    return u.full_name or u.email

def _serialize(t: Task) -> dict:
    return {
        "id":            str(t.id),
        "title":         t.title,
        "description":   t.description,
        "status":        t.status.value if t.status else None,
        "priority":      t.priority.value if t.priority else None,
        "due_date":      t.due_date.isoformat() if t.due_date else None,
        "assignee_id":   str(t.assignee_id) if t.assignee_id else None,
        "assignee_name": _name(t.assignee),
        "created_by_id": str(t.created_by_id) if t.created_by_id else None,
        "created_by_name": _name(t.created_by),
        "app_slug":      t.app_slug,
        "source_type":   t.source_type,
        "source_ref":    t.source_ref,
        "source_label":  t.source_label,
        "created_at":    t.created_at.isoformat() if t.created_at else None,
        "updated_at":    t.updated_at.isoformat() if t.updated_at else None,
        "completed_at":  t.completed_at.isoformat() if t.completed_at else None,
    }




def _notify_assignment(db, task, actor):
    """Mail de assignee bij toewijzing aan iemand anders dan de actor (guarded)."""
    try:
        if not task.assignee_id or task.assignee_id == actor.id:
            return
        a = db.query(User).filter(User.id == task.assignee_id).first()
        if a and a.email:
            mailer.notify_task_assigned(a.email, _name(a), _name(actor), task.title)
    except Exception:
        import logging; logging.getLogger('rhadix.mail').exception('notify_assignment faalde')


def _notify_bulk(db, tasks, actor):
    """Eén samenvattingsmail per assignee (≠ actor) voor bulk-aanmaak."""
    try:
        from collections import Counter
        counts = Counter(t.assignee_id for t in tasks if t.assignee_id and t.assignee_id != actor.id)
        for aid, n in counts.items():
            a = db.query(User).filter(User.id == aid).first()
            if a and a.email:
                if n == 1:
                    one = next(t for t in tasks if t.assignee_id == aid)
                    mailer.notify_task_assigned(a.email, _name(a), _name(actor), one.title)
                else:
                    mailer.notify_tasks_assigned(a.email, _name(a), _name(actor), n)
    except Exception:
        import logging; logging.getLogger('rhadix.mail').exception('notify_bulk faalde')

# ─── schemas ──────────────────────────────────────────────────────────────────

class TaskCreate(BaseModel):
    title:        str = Field(..., min_length=1, max_length=255)
    description:  Optional[str] = None
    priority:     Optional[str] = "NORMAAL"
    due_date:     Optional[str] = None
    assignee_id:  Optional[str] = None
    source_type:  Optional[str] = None
    source_ref:   Optional[str] = None
    source_label: Optional[str] = None

class TaskBulkCreate(BaseModel):
    items:        List[TaskCreate]
    assignee_id:  Optional[str] = None   # standaard-toewijzing voor alle items zonder eigen assignee
    source_type:  Optional[str] = None
    source_ref:   Optional[str] = None

class TaskPatch(BaseModel):
    title:        Optional[str] = None
    description:  Optional[str] = None
    status:       Optional[str] = None
    priority:     Optional[str] = None
    due_date:     Optional[str] = None
    assignee_id:  Optional[str] = None


def _parse_dt(val):
    if not val:
        return None
    try:
        return datetime.fromisoformat(str(val).replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(400, f"Ongeldige datum: {val!r}")


# ─── lijst + telling ──────────────────────────────────────────────────────────

@router.get("")
def list_tasks(
    scope:       str = Query("mine", pattern="^(mine|created|all)$"),
    status:      Optional[str] = None,
    assignee_id: Optional[str] = None,
    db:          Session = Depends(get_db),
    user:        User    = Depends(get_current_user),
):
    q = db.query(Task).filter(Task.tenant_id == user.tenant_id)

    if scope == "mine":
        q = q.filter(Task.assignee_id == user.id)
    elif scope == "created":
        q = q.filter(Task.created_by_id == user.id)
    else:  # all
        if not _is_admin(user):
            # gewone gebruiker: 'alles' = eigen toegewezen + zelf aangemaakt
            q = q.filter(or_(Task.assignee_id == user.id, Task.created_by_id == user.id))

    if status:
        if status not in _STATUSES:
            raise HTTPException(400, f"Onbekende status: {status}")
        q = q.filter(Task.status == status)
    if assignee_id:
        q = q.filter(Task.assignee_id == _uuid(assignee_id, "assignee_id"))

    # open taken eerst, dan deadline, dan nieuwste
    rows = q.order_by(Task.completed_at.is_(None).desc(), Task.due_date.asc().nullslast(),
                      Task.created_at.desc()).all()
    return [_serialize(t) for t in rows]


@router.get("/summary")
def task_summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    base = db.query(Task).filter(Task.tenant_id == user.tenant_id)
    mine_open = base.filter(Task.assignee_id == user.id,
                            Task.status.in_([TaskStatus.OPEN, TaskStatus.IN_BEHANDELING])).count()
    now = datetime.now(timezone.utc)
    mine_overdue = base.filter(Task.assignee_id == user.id,
                               Task.status.in_([TaskStatus.OPEN, TaskStatus.IN_BEHANDELING]),
                               Task.due_date.isnot(None), Task.due_date < now).count()
    out = {"mine_open": mine_open, "mine_overdue": mine_overdue}
    if _is_admin(user):
        out["tenant_open"] = base.filter(Task.status.in_(
            [TaskStatus.OPEN, TaskStatus.IN_BEHANDELING])).count()
    return out


@router.get("/assignable-users")
def assignable_users(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return [
        {"id": str(u.id), "name": _name(u), "email": u.email, "role": u.role.value}
        for u in _tenant_users(db, user.tenant_id)
    ]


# ─── aanmaken ─────────────────────────────────────────────────────────────────

def _create_one(db, user, data: TaskCreate, default_assignee=None,
                src_type=None, src_ref=None):
    prio = (data.priority or "NORMAAL").upper()
    if prio not in _PRIORITIES:
        raise HTTPException(400, f"Onbekende prioriteit: {prio}")
    assignee = _validate_assignee(db, _uuid(data.assignee_id, "assignee_id") or default_assignee,
                                  user.tenant_id)
    t = Task(
        tenant_id     = user.tenant_id,
        title         = data.title.strip(),
        description   = data.description,
        priority      = TaskPriority(prio),
        status        = TaskStatus.OPEN,
        due_date      = _parse_dt(data.due_date),
        assignee_id   = assignee,
        created_by_id = user.id,
        app_slug      = APP_SLUG,
        source_type   = data.source_type or src_type,
        source_ref    = data.source_ref or src_ref,
        source_label  = data.source_label,
    )
    db.add(t)
    return t


@router.post("", status_code=201)
def create_task(body: TaskCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    t = _create_one(db, user, body)
    db.commit(); db.refresh(t)
    _notify_assignment(db, t, user)
    return _serialize(t)


@router.post("/bulk", status_code=201)
def create_tasks_bulk(body: TaskBulkCreate, db: Session = Depends(get_db),
                      user: User = Depends(get_current_user)):
    if not body.items:
        raise HTTPException(400, "Geen taken opgegeven")
    if len(body.items) > 500:
        raise HTTPException(400, "Maximaal 500 taken per keer")
    default_assignee = _uuid(body.assignee_id, "assignee_id")
    created = [_create_one(db, user, it, default_assignee, body.source_type, body.source_ref)
               for it in body.items]
    db.commit()
    for t in created:
        db.refresh(t)
    _notify_bulk(db, created, user)
    return {"created": len(created), "tasks": [_serialize(t) for t in created]}


# ─── bijwerken / verwijderen ──────────────────────────────────────────────────

def _get_owned(db, user, task_id):
    t = db.query(Task).filter(Task.id == _uuid(task_id, "task_id"),
                              Task.tenant_id == user.tenant_id).first()
    if not t:
        raise HTTPException(404, "Taak niet gevonden")
    return t


@router.patch("/{task_id}")
def update_task(task_id: str, body: TaskPatch, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    t = _get_owned(db, user, task_id)

    if body.title is not None:
        t.title = body.title.strip()
    if body.description is not None:
        t.description = body.description
    if body.priority is not None:
        p = body.priority.upper()
        if p not in _PRIORITIES:
            raise HTTPException(400, f"Onbekende prioriteit: {p}")
        t.priority = TaskPriority(p)
    if body.due_date is not None:
        t.due_date = _parse_dt(body.due_date)
    _old_assignee = t.assignee_id
    if body.assignee_id is not None:
        t.assignee_id = _validate_assignee(db, _uuid(body.assignee_id, "assignee_id"), user.tenant_id)
    if body.status is not None:
        st = body.status.upper()
        if st not in _STATUSES:
            raise HTTPException(400, f"Onbekende status: {st}")
        t.status = TaskStatus(st)
        t.completed_at = datetime.now(timezone.utc) if st == "KLAAR" else None

    db.commit(); db.refresh(t)
    if t.assignee_id and t.assignee_id != _old_assignee:
        _notify_assignment(db, t, user)
    return _serialize(t)


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    t = _get_owned(db, user, task_id)
    # gewone gebruiker mag alleen eigen-aangemaakte of aan zichzelf toegewezen taken verwijderen
    if not _is_admin(user) and user.id not in (t.created_by_id, t.assignee_id):
        raise HTTPException(403, "Geen rechten om deze taak te verwijderen")
    db.delete(t); db.commit()
    return None
