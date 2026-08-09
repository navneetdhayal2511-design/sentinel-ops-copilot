from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str = Field(min_length=6)
    role: str = "viewer"


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: str
    is_active: bool

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AlertCreate(BaseModel):
    external_id: str | None = None
    title: str
    service: str
    severity: str = "medium"
    source: str = "manual"
    message: str
    raw_payload: dict | None = None


class AlertOut(BaseModel):
    id: int
    external_id: str
    title: str
    service: str
    severity: str
    status: str
    source: str
    message: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TraceOut(BaseModel):
    id: int
    step: int
    kind: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class InvestigationOut(BaseModel):
    id: int
    alert_id: int
    status: str
    summary: str
    root_cause: str
    recommended_actions: str
    confidence: float
    model_name: str
    latency_ms: int
    cost_usd: float
    created_at: datetime
    traces: list[TraceOut] = []

    model_config = {"from_attributes": True}


class InvestigateRequest(BaseModel):
    use_llm: bool = True


class AuditOut(BaseModel):
    id: int
    investigation_id: int | None
    actor: str
    action: str
    detail: str
    created_at: datetime

    model_config = {"from_attributes": True}


class StatsOut(BaseModel):
    open_alerts: int
    critical_alerts: int
    investigations: int
    avg_confidence: float
    avg_latency_ms: float


class EvalCaseResult(BaseModel):
    case_id: str
    expected_service: str
    predicted_service: str
    expected_root_cause_contains: list[str]
    root_cause: str
    passed: bool
    confidence: float


class EvalReport(BaseModel):
    total: int
    passed: int
    accuracy: float
    avg_confidence: float
    avg_latency_ms: float
    results: list[EvalCaseResult]
