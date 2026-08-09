from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.agent.tools import (
    get_recent_deploys,
    get_service_metrics,
    propose_remediation,
    run_tool,
    search_logs,
)
from app.config import settings
from app.models import AgentTrace, Alert, AuditEvent, Investigation
from app.rag.retriever import RunbookRetriever


@dataclass
class InvestigationResult:
    summary: str
    root_cause: str
    recommended_actions: str
    confidence: float
    model_name: str
    latency_ms: int
    cost_usd: float
    citations: list[dict] = field(default_factory=list)
    traces: list[dict] = field(default_factory=list)


def _trace(traces: list[dict], step: int, kind: str, content: str) -> None:
    traces.append({"step": step, "kind": kind, "content": content})


def _heuristic_investigate(alert: Alert, retriever: RunbookRetriever) -> InvestigationResult:
    traces: list[dict] = []
    step = 1
    query = f"{alert.service} {alert.title} {alert.message}"
    _trace(traces, step, "plan", "Collect metrics, logs, deploys, and matching runbooks.")
    step += 1

    metrics = get_service_metrics(alert.service)
    _trace(traces, step, "tool:get_service_metrics", json.dumps(metrics, indent=2))
    step += 1

    logs = search_logs(alert.service, alert.title)
    _trace(traces, step, "tool:search_logs", json.dumps(logs, indent=2))
    step += 1

    deploys = get_recent_deploys(alert.service)
    _trace(traces, step, "tool:get_recent_deploys", json.dumps(deploys, indent=2))
    step += 1

    docs = retriever.search(query, top_k=3)
    _trace(traces, step, "rag:runbooks", json.dumps(docs, indent=2))
    step += 1

    error_blob = " ".join(metrics.get("recent_errors", [])).lower()
    msg = f"{alert.message} {error_blob}".lower()

    if "postgres" in msg or "db" in msg or "connection" in msg:
        root = "Database connectivity degradation on primary (timeouts / circuit breaker)."
        conf = 0.86
    elif "jwt" in msg or "secret" in msg or "401" in msg:
        root = "Auth canary misconfiguration (JWT secret mismatch) causing token failures."
        conf = 0.84
    elif "cdn" in msg or "cors" in msg or "asset" in msg:
        root = "Frontend asset / CDN delivery issue after recent checkout release."
        conf = 0.8
    elif "kafka" in msg or "oom" in msg or "lag" in msg:
        root = "Ingest pipeline saturation: consumer lag with OOM-killed workers."
        conf = 0.88
    else:
        root = f"Elevated errors on {alert.service}; likely related to recent deploy or dependency pressure."
        conf = 0.62

    remediation = propose_remediation(alert.service, root)
    _trace(traces, step, "tool:propose_remediation", json.dumps(remediation, indent=2))
    step += 1

    citation_slugs = ", ".join(d["slug"] for d in docs) or "none"
    summary = (
        f"Alert '{alert.title}' on {alert.service} ({alert.severity}). "
        f"error_rate={metrics.get('error_rate')}, p99={metrics.get('p99_ms')}ms. "
        f"Runbooks consulted: {citation_slugs}."
    )
    actions = "\n".join(f"- {a}" for a in remediation["actions"])
    _trace(traces, step, "conclusion", f"{root}\n\nActions:\n{actions}")

    return InvestigationResult(
        summary=summary,
        root_cause=root,
        recommended_actions=actions,
        confidence=conf,
        model_name="sentinel-heuristic-v1",
        latency_ms=120,
        cost_usd=0.0,
        citations=docs,
        traces=traces,
    )


def _llm_investigate(alert: Alert, retriever: RunbookRetriever) -> InvestigationResult:
    if not settings.openai_api_key:
        return _heuristic_investigate(alert, retriever)

    try:
        from openai import OpenAI
    except ImportError:
        return _heuristic_investigate(alert, retriever)

    started = time.perf_counter()
    traces: list[dict] = []
    docs = retriever.search(f"{alert.service} {alert.title} {alert.message}", top_k=3)
    _trace(traces, 1, "rag:runbooks", json.dumps(docs, indent=2))

    client = OpenAI(api_key=settings.openai_api_key)
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_service_metrics",
                "description": "Get live-ish service health metrics",
                "parameters": {
                    "type": "object",
                    "properties": {"service": {"type": "string"}},
                    "required": ["service"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search_logs",
                "description": "Search recent error logs",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "service": {"type": "string"},
                        "query": {"type": "string"},
                    },
                    "required": ["service", "query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_recent_deploys",
                "description": "List recent deploys",
                "parameters": {
                    "type": "object",
                    "properties": {"service": {"type": "string"}},
                    "required": ["service"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "propose_remediation",
                "description": "Propose remediation steps",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "service": {"type": "string"},
                        "root_cause": {"type": "string"},
                    },
                    "required": ["service", "root_cause"],
                },
            },
        },
    ]

    messages = [
        {
            "role": "system",
            "content": (
                "You are Sentinel, an SRE incident copilot. "
                "Use tools, cite runbooks, and return a final JSON object with keys: "
                "summary, root_cause, recommended_actions (array of strings), confidence (0-1)."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "alert": {
                        "title": alert.title,
                        "service": alert.service,
                        "severity": alert.severity,
                        "message": alert.message,
                    },
                    "runbooks": docs,
                }
            ),
        },
    ]

    step = 2
    final_text = ""
    for _ in range(6):
        resp = client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=0.2,
        )
        msg = resp.choices[0].message
        if msg.tool_calls:
            messages.append(msg)
            for call in msg.tool_calls:
                args = json.loads(call.function.arguments or "{}")
                result = run_tool(call.function.name, **args)
                _trace(traces, step, f"tool:{call.function.name}", result)
                step += 1
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": result,
                    }
                )
            continue
        final_text = msg.content or ""
        _trace(traces, step, "llm:final", final_text)
        break

    latency_ms = int((time.perf_counter() - started) * 1000)
    parsed = _extract_json(final_text)
    if not parsed:
        fallback = _heuristic_investigate(alert, retriever)
        fallback.traces = traces + fallback.traces
        fallback.citations = docs or fallback.citations
        fallback.model_name = settings.openai_model + "+heuristic-fallback"
        fallback.latency_ms = latency_ms
        return fallback

    actions = parsed.get("recommended_actions", [])
    if isinstance(actions, list):
        actions_text = "\n".join(f"- {a}" for a in actions)
    else:
        actions_text = str(actions)

    return InvestigationResult(
        summary=str(parsed.get("summary", "")),
        root_cause=str(parsed.get("root_cause", "")),
        recommended_actions=actions_text,
        confidence=float(parsed.get("confidence", 0.7)),
        model_name=settings.openai_model,
        latency_ms=latency_ms,
        cost_usd=0.002,
        citations=docs,
        traces=traces,
    )


def _extract_json(text: str) -> dict | None:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None


def run_investigation(
    db: Session,
    alert: Alert,
    actor: str,
    use_llm: bool = True,
) -> Investigation:
    retriever = RunbookRetriever.from_db(db)
    started = time.perf_counter()
    if use_llm and settings.openai_api_key:
        result = _llm_investigate(alert, retriever)
    else:
        result = _heuristic_investigate(alert, retriever)
    if result.latency_ms == 0:
        result.latency_ms = int((time.perf_counter() - started) * 1000)

    inv = Investigation(
        alert_id=alert.id,
        status="completed",
        summary=result.summary,
        root_cause=result.root_cause,
        recommended_actions=result.recommended_actions,
        citations_json=json.dumps(result.citations),
        confidence=result.confidence,
        model_name=result.model_name,
        latency_ms=result.latency_ms,
        cost_usd=result.cost_usd,
        feedback_status="pending",
    )
    db.add(inv)
    db.flush()

    for t in result.traces:
        db.add(
            AgentTrace(
                investigation_id=inv.id,
                step=t["step"],
                kind=t["kind"],
                content=t["content"],
            )
        )

    alert.status = "investigating"
    db.add(
        AuditEvent(
            investigation_id=inv.id,
            actor=actor,
            action="investigation.completed",
            detail=f"confidence={result.confidence:.2f} model={result.model_name}",
        )
    )
    db.commit()
    db.refresh(inv)
    return inv
