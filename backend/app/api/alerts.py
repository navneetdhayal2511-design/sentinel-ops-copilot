from typing import Annotated
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_admin
from app.database import get_db
from app.models import Alert, AuditEvent, User
from app.schemas import AlertCreate, AlertOut

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertOut])
def list_alerts(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    status: str | None = Query(default=None),
    severity: str | None = Query(default=None),
) -> list[Alert]:
    q = db.query(Alert).order_by(Alert.created_at.desc())
    if status:
        q = q.filter(Alert.status == status)
    if severity:
        q = q.filter(Alert.severity == severity)
    return q.all()


@router.get("/{alert_id}", response_model=AlertOut)
def get_alert(
    alert_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> Alert:
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.post("", response_model=AlertOut)
def create_alert(
    payload: AlertCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_admin)],
) -> Alert:
    alert = Alert(
        external_id=payload.external_id or f"evt-{uuid.uuid4().hex[:12]}",
        title=payload.title,
        service=payload.service,
        severity=payload.severity,
        source=payload.source,
        message=payload.message,
        raw_payload=json.dumps(payload.raw_payload or {}),
        status="open",
    )
    db.add(alert)
    db.add(
        AuditEvent(
            actor=user.email,
            action="alert.created",
            detail=alert.title,
        )
    )
    db.commit()
    db.refresh(alert)
    return alert


@router.post("/{alert_id}/ack", response_model=AlertOut)
def ack_alert(
    alert_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_admin)],
) -> Alert:
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.status = "acknowledged"
    db.add(
        AuditEvent(
            actor=user.email,
            action="alert.acknowledged",
            detail=f"alert_id={alert.id}",
        )
    )
    db.commit()
    db.refresh(alert)
    return alert
