from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.agent.investigator import run_investigation
from app.auth import get_current_user, require_admin
from app.database import get_db
from app.jobs import enqueue_investigation, process_investigation_job
from app.models import Alert, AuditEvent, Investigation, InvestigationFeedback, User
from app.schemas import FeedbackIn, FeedbackOut, InvestigateRequest, InvestigationOut, JobOut
from app.serializers import investigation_to_out
from app.models import BackgroundJob

router = APIRouter(prefix="/api/investigations", tags=["investigations"])


@router.get("", response_model=list[InvestigationOut])
def list_investigations(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> list[InvestigationOut]:
    rows = (
        db.query(Investigation)
        .options(joinedload(Investigation.traces))
        .order_by(Investigation.created_at.desc())
        .all()
    )
    return [investigation_to_out(r) for r in rows]


@router.get("/{investigation_id}", response_model=InvestigationOut)
def get_investigation(
    investigation_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> InvestigationOut:
    inv = (
        db.query(Investigation)
        .options(joinedload(Investigation.traces))
        .filter(Investigation.id == investigation_id)
        .first()
    )
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return investigation_to_out(inv)


@router.post("/alerts/{alert_id}/run", response_model=InvestigationOut | JobOut)
def investigate_alert(
    alert_id: int,
    payload: InvestigateRequest,
    background: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_admin)],
) -> InvestigationOut | JobOut:
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    if payload.async_mode:
        job = enqueue_investigation(db, alert.id, actor=user.email, use_llm=payload.use_llm)
        background.add_task(process_investigation_job, job.id)
        return job

    inv = run_investigation(db, alert, actor=user.email, use_llm=payload.use_llm)
    inv = (
        db.query(Investigation)
        .options(joinedload(Investigation.traces))
        .filter(Investigation.id == inv.id)
        .one()
    )
    return investigation_to_out(inv)


@router.post("/{investigation_id}/feedback", response_model=FeedbackOut)
def submit_feedback(
    investigation_id: int,
    payload: FeedbackIn,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_admin)],
) -> InvestigationFeedback:
    inv = db.query(Investigation).filter(Investigation.id == investigation_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    fb = InvestigationFeedback(
        investigation_id=inv.id,
        actor=user.email,
        decision=payload.decision,
        notes=payload.notes,
        edited_root_cause=payload.edited_root_cause,
    )
    inv.feedback_status = payload.decision
    if payload.decision == "edited" and payload.edited_root_cause:
        inv.root_cause = payload.edited_root_cause
        inv.status = "edited"
    elif payload.decision == "approved":
        inv.status = "approved"
        alert = db.query(Alert).filter(Alert.id == inv.alert_id).first()
        if alert:
            alert.status = "resolved"
    elif payload.decision == "rejected":
        inv.status = "rejected"

    db.add(fb)
    db.add(
        AuditEvent(
            investigation_id=inv.id,
            actor=user.email,
            action=f"feedback.{payload.decision}",
            detail=payload.notes or payload.edited_root_cause or "",
        )
    )
    db.commit()
    db.refresh(fb)
    return fb
