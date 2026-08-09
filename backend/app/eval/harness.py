from __future__ import annotations

import json
import time
from pathlib import Path

from sqlalchemy.orm import Session

from app.agent.investigator import run_investigation
from app.models import Alert
from app.schemas import EvalCaseResult, EvalReport

CASES = [
    {
        "case_id": "payments-db",
        "title": "Payments DB timeouts",
        "service": "payments-api",
        "severity": "critical",
        "message": "TimeoutError connecting to postgres primary; circuit_breaker_open",
        "expected_service": "payments-api",
        "expected_root_cause_contains": ["database", "postgres", "primary"],
    },
    {
        "case_id": "auth-jwt",
        "title": "Auth 401 spike",
        "service": "auth-service",
        "severity": "high",
        "message": "JWT_SECRET mismatch on canary pod causing 401s",
        "expected_service": "auth-service",
        "expected_root_cause_contains": ["jwt", "secret", "canary"],
    },
    {
        "case_id": "checkout-cdn",
        "title": "Checkout asset failures",
        "service": "checkout-web",
        "severity": "medium",
        "message": "CDN cache miss on checkout.js with CORS blocks",
        "expected_service": "checkout-web",
        "expected_root_cause_contains": ["cdn", "asset", "checkout"],
    },
    {
        "case_id": "ingest-lag",
        "title": "Ingest lag",
        "service": "ingest-worker",
        "severity": "critical",
        "message": "KafkaConsumerLagExceeded and OOMKilled workers",
        "expected_service": "ingest-worker",
        "expected_root_cause_contains": ["kafka", "lag", "oom", "ingest"],
    },
]


def _passed(root_cause: str, needles: list[str]) -> bool:
    text = root_cause.lower()
    return any(n.lower() in text for n in needles)


def run_eval(db: Session, use_llm: bool = False) -> EvalReport:
    results: list[EvalCaseResult] = []
    latencies: list[float] = []
    confidences: list[float] = []

    for case in CASES:
        alert = Alert(
            external_id=f"eval-{case['case_id']}-{int(time.time() * 1000)}",
            title=case["title"],
            service=case["service"],
            severity=case["severity"],
            status="open",
            source="eval",
            message=case["message"],
            raw_payload=json.dumps(case),
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)

        inv = run_investigation(db, alert, actor="eval-harness", use_llm=use_llm)
        ok = _passed(inv.root_cause, case["expected_root_cause_contains"])
        results.append(
            EvalCaseResult(
                case_id=case["case_id"],
                expected_service=case["expected_service"],
                predicted_service=alert.service,
                expected_root_cause_contains=case["expected_root_cause_contains"],
                root_cause=inv.root_cause,
                passed=ok,
                confidence=inv.confidence,
            )
        )
        latencies.append(float(inv.latency_ms))
        confidences.append(float(inv.confidence))

    passed = sum(1 for r in results if r.passed)
    report = EvalReport(
        total=len(results),
        passed=passed,
        accuracy=passed / len(results) if results else 0.0,
        avg_confidence=sum(confidences) / len(confidences) if confidences else 0.0,
        avg_latency_ms=sum(latencies) / len(latencies) if latencies else 0.0,
        results=results,
    )

    out = Path(__file__).resolve().parents[2] / "data" / "eval_report.json"
    out.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report
