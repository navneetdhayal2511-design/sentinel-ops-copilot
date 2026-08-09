from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy.orm import Session

from app.agent.investigator import run_investigation
from app.database import SessionLocal
from app.models import Alert, BackgroundJob


def enqueue_investigation(db: Session, alert_id: int, actor: str, use_llm: bool = True) -> BackgroundJob:
    job = BackgroundJob(
        kind="investigate_alert",
        status="queued",
        payload_json=json.dumps(
            {"alert_id": alert_id, "actor": actor, "use_llm": use_llm}
        ),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def process_investigation_job(job_id: int) -> None:
    db = SessionLocal()
    try:
        job = db.query(BackgroundJob).filter(BackgroundJob.id == job_id).first()
        if not job:
            return
        job.status = "running"
        db.commit()

        payload = json.loads(job.payload_json or "{}")
        alert = db.query(Alert).filter(Alert.id == payload.get("alert_id")).first()
        if not alert:
            job.status = "failed"
            job.error = "alert not found"
            job.finished_at = datetime.utcnow()
            db.commit()
            return

        inv = run_investigation(
            db,
            alert,
            actor=payload.get("actor", "worker"),
            use_llm=bool(payload.get("use_llm", True)),
        )
        job.status = "completed"
        job.result_json = json.dumps({"investigation_id": inv.id})
        job.finished_at = datetime.utcnow()
        db.commit()
    except Exception as exc:  # noqa: BLE001
        job = db.query(BackgroundJob).filter(BackgroundJob.id == job_id).first()
        if job:
            job.status = "failed"
            job.error = str(exc)
            job.finished_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()
