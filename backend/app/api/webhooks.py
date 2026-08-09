from __future__ import annotations

import json
import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.jobs import enqueue_investigation, process_investigation_job
from app.models import Alert, AuditEvent
from app.schemas import AlertOut, WebhookAlertIn

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


def _authorize(token: str | None) -> None:
    expected = settings.webhook_token
    if not token or token.replace("Bearer ", "") != expected:
        raise HTTPException(status_code=401, detail="Invalid webhook token")


@router.post("/alerts", response_model=AlertOut)
def ingest_alert_webhook(
    payload: WebhookAlertIn,
    background: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
    x_sentinel_token: Annotated[str | None, Header()] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> Alert:
    _authorize(x_sentinel_token or authorization)

    title = payload.title or payload.summary or "Webhook alert"
    message = payload.message or payload.description or title
    service = payload.service or "unknown-service"
    severity = (payload.severity or "high").lower()
    external_id = payload.external_id or payload.id or f"wh-{uuid.uuid4().hex[:12]}"

    existing = db.query(Alert).filter(Alert.external_id == external_id).first()
    if existing:
        return existing

    alert = Alert(
        external_id=external_id,
        title=title,
        service=service,
        severity=severity,
        source=payload.source or "webhook",
        message=message,
        raw_payload=json.dumps(payload.model_dump()),
        status="open",
    )
    db.add(alert)
    db.add(
        AuditEvent(
            actor="webhook",
            action="alert.ingested",
            detail=f"{external_id}:{title}",
        )
    )
    db.commit()
    db.refresh(alert)

    if payload.auto_investigate:
        job = enqueue_investigation(db, alert.id, actor="webhook", use_llm=False)
        background.add_task(process_investigation_job, job.id)

    return alert
