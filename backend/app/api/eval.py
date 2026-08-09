from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import require_admin
from app.database import get_db
from app.eval.harness import run_eval
from app.models import User
from app.schemas import EvalReport

router = APIRouter(prefix="/api/eval", tags=["eval"])


@router.post("/run", response_model=EvalReport)
def eval_run(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_admin)],
    use_llm: bool = Query(default=False),
) -> EvalReport:
    return run_eval(db, use_llm=use_llm)
