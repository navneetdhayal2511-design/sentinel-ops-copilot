from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import (
    Alert,
    AuditEvent,
    BackgroundJob,
    EvalRun,
    Investigation,
    InvestigationFeedback,
    User,
)
from app.schemas import AuditOut, ObservabilityOut, StatsOut

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/stats", response_model=StatsOut)
def stats(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> StatsOut:
    open_alerts = db.query(Alert).filter(Alert.status == "open").count()
    critical = db.query(Alert).filter(Alert.severity == "critical", Alert.status != "resolved").count()
    inv_count = db.query(Investigation).count()
    avg_conf = db.query(func.avg(Investigation.confidence)).scalar() or 0.0
    avg_lat = db.query(func.avg(Investigation.latency_ms)).scalar() or 0.0
    approved = db.query(InvestigationFeedback).filter(InvestigationFeedback.decision == "approved").count()
    rejected = db.query(InvestigationFeedback).filter(InvestigationFeedback.decision == "rejected").count()
    latest_eval = db.query(EvalRun).order_by(EvalRun.created_at.desc()).first()
    jobs_queued = db.query(BackgroundJob).filter(BackgroundJob.status == "queued").count()
    return StatsOut(
        open_alerts=open_alerts,
        critical_alerts=critical,
        investigations=inv_count,
        avg_confidence=float(avg_conf),
        avg_latency_ms=float(avg_lat),
        feedback_approved=approved,
        feedback_rejected=rejected,
        latest_eval_accuracy=latest_eval.accuracy if latest_eval else None,
        jobs_queued=jobs_queued,
    )


@router.get("/observability", response_model=ObservabilityOut)
def observability(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> ObservabilityOut:
    total = db.query(Investigation).count()
    avg_lat = float(db.query(func.avg(Investigation.latency_ms)).scalar() or 0.0)
    avg_conf = float(db.query(func.avg(Investigation.confidence)).scalar() or 0.0)
    avg_cost = float(db.query(func.avg(Investigation.cost_usd)).scalar() or 0.0)

    fb_total = max(db.query(InvestigationFeedback).count(), 1)
    rates = {}
    for decision in ("approved", "rejected", "edited"):
        c = db.query(InvestigationFeedback).filter(InvestigationFeedback.decision == decision).count()
        rates[decision] = round(c / fb_total, 3)

    taxonomy: dict[str, int] = {}
    for inv in db.query(Investigation).all():
        text = (inv.root_cause or "").lower()
        if "database" in text or "postgres" in text:
            key = "database"
        elif "jwt" in text or "auth" in text:
            key = "auth"
        elif "cdn" in text or "asset" in text:
            key = "frontend"
        elif "kafka" in text or "ingest" in text:
            key = "ingest"
        else:
            key = "other"
        taxonomy[key] = taxonomy.get(key, 0) + 1

    evals = (
        db.query(EvalRun).order_by(EvalRun.created_at.desc()).limit(10).all()
    )
    jobs_by_status: dict[str, int] = {}
    for status in ("queued", "running", "completed", "failed"):
        jobs_by_status[status] = (
            db.query(BackgroundJob).filter(BackgroundJob.status == status).count()
        )

    return ObservabilityOut(
        total_investigations=total,
        avg_latency_ms=avg_lat,
        avg_confidence=avg_conf,
        avg_cost_usd=avg_cost,
        feedback_rates=rates,
        failure_taxonomy=taxonomy,
        recent_eval_accuracy=[e.accuracy for e in reversed(evals)],
        jobs_by_status=jobs_by_status,
    )


@router.get("/audit", response_model=list[AuditOut])
def audit_log(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> list[AuditEvent]:
    return db.query(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(50).all()
