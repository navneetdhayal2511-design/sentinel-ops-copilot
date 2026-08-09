from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Alert, AuditEvent, Investigation, User
from app.schemas import AuditOut, StatsOut

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
    return StatsOut(
        open_alerts=open_alerts,
        critical_alerts=critical,
        investigations=inv_count,
        avg_confidence=float(avg_conf),
        avg_latency_ms=float(avg_lat),
    )


@router.get("/audit", response_model=list[AuditOut])
def audit_log(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> list[AuditEvent]:
    return db.query(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(50).all()
