from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.agent.investigator import run_investigation
from app.auth import get_current_user, require_admin
from app.database import get_db
from app.models import Alert, Investigation, User
from app.schemas import InvestigateRequest, InvestigationOut

router = APIRouter(prefix="/api/investigations", tags=["investigations"])


@router.get("", response_model=list[InvestigationOut])
def list_investigations(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> list[Investigation]:
    return (
        db.query(Investigation)
        .options(joinedload(Investigation.traces))
        .order_by(Investigation.created_at.desc())
        .all()
    )


@router.get("/{investigation_id}", response_model=InvestigationOut)
def get_investigation(
    investigation_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> Investigation:
    inv = (
        db.query(Investigation)
        .options(joinedload(Investigation.traces))
        .filter(Investigation.id == investigation_id)
        .first()
    )
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return inv


@router.post("/alerts/{alert_id}/run", response_model=InvestigationOut)
def investigate_alert(
    alert_id: int,
    payload: InvestigateRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_admin)],
) -> Investigation:
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    inv = run_investigation(db, alert, actor=user.email, use_llm=payload.use_llm)
    return (
        db.query(Investigation)
        .options(joinedload(Investigation.traces))
        .filter(Investigation.id == inv.id)
        .one()
    )
