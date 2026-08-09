from __future__ import annotations

import json

from app.models import Investigation
from app.schemas import CitationOut, InvestigationOut, TraceOut


def investigation_to_out(inv: Investigation) -> InvestigationOut:
    try:
        citations_raw = json.loads(inv.citations_json or "[]")
    except json.JSONDecodeError:
        citations_raw = []
    citations = []
    for c in citations_raw:
        citations.append(
            CitationOut(
                slug=c.get("slug", ""),
                title=c.get("title", ""),
                service=c.get("service", ""),
                score=float(c.get("score", 0)),
                excerpt=c.get("excerpt", ""),
                method=c.get("method"),
                citation=c.get("citation"),
            )
        )
    traces = [
        TraceOut(
            id=t.id,
            step=t.step,
            kind=t.kind,
            content=t.content,
            created_at=t.created_at,
        )
        for t in sorted(inv.traces, key=lambda x: x.step)
    ]
    return InvestigationOut(
        id=inv.id,
        alert_id=inv.alert_id,
        status=inv.status,
        summary=inv.summary,
        root_cause=inv.root_cause,
        recommended_actions=inv.recommended_actions,
        citations=citations,
        confidence=inv.confidence,
        model_name=inv.model_name,
        latency_ms=inv.latency_ms,
        cost_usd=inv.cost_usd,
        feedback_status=getattr(inv, "feedback_status", "pending") or "pending",
        created_at=inv.created_at,
        traces=traces,
    )
