from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field


class Token(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


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


class WebhookAlertIn(BaseModel):
    """PagerDuty / Slack-style flexible webhook payload."""

    id: str | None = None
    external_id: str | None = None
    title: str | None = None
    summary: str | None = None
    service: str | None = None
    severity: str | None = "high"
    message: str | None = None
    description: str | None = None
    source: str | None = "webhook"
    auto_investigate: bool = False
    raw: dict[str, Any] | None = None


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


class CitationOut(BaseModel):
    slug: str
    title: str
    service: str
    score: float
    excerpt: str
    method: str | None = None
    citation: str | None = None


class InvestigationOut(BaseModel):
    id: int
    alert_id: int
    status: str
    summary: str
    root_cause: str
    recommended_actions: str
    citations: list[CitationOut] = []
    confidence: float
    model_name: str
    latency_ms: int
    cost_usd: float
    feedback_status: str = "pending"
    created_at: datetime
    traces: list[TraceOut] = []

    model_config = {"from_attributes": True}


class InvestigateRequest(BaseModel):
    use_llm: bool = True
    async_mode: bool = False


class FeedbackIn(BaseModel):
    decision: str = Field(pattern="^(approved|rejected|edited)$")
    notes: str = ""
    edited_root_cause: str = ""


class FeedbackOut(BaseModel):
    id: int
    investigation_id: int
    actor: str
    decision: str
    notes: str
    edited_root_cause: str
    created_at: datetime

    model_config = {"from_attributes": True}


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
    feedback_approved: int = 0
    feedback_rejected: int = 0
    latest_eval_accuracy: float | None = None
    jobs_queued: int = 0


class ObservabilityOut(BaseModel):
    total_investigations: int
    avg_latency_ms: float
    avg_confidence: float
    avg_cost_usd: float
    feedback_rates: dict[str, float]
    failure_taxonomy: dict[str, int]
    recent_eval_accuracy: list[float]
    jobs_by_status: dict[str, int]


class EvalCaseResult(BaseModel):
    case_id: str
    expected_service: str
    predicted_service: str
    expected_root_cause_contains: list[str]
    root_cause: str
    passed: bool
    confidence: float
    hallucinated_service: bool = False
    citation_hit: bool = False
    latency_ms: float = 0


class EvalReport(BaseModel):
    total: int
    passed: int
    accuracy: float
    precision: float
    recall: float
    hallucination_rate: float
    citation_hit_rate: float
    avg_confidence: float
    avg_latency_ms: float
    results: list[EvalCaseResult]


class JobOut(BaseModel):
    id: int
    kind: str
    status: str
    payload_json: str
    result_json: str
    error: str
    created_at: datetime
    finished_at: datetime | None

    model_config = {"from_attributes": True}
