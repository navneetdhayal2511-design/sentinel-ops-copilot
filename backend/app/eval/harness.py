from __future__ import annotations

import json
import time
from pathlib import Path

from sqlalchemy.orm import Session

from app.agent.investigator import run_investigation
from app.models import Alert, EvalRun
from app.schemas import EvalCaseResult, EvalReport

KNOWN_SERVICES = {"payments-api", "auth-service", "checkout-web", "ingest-worker"}

CASES = [
    {
        "case_id": "payments-db",
        "title": "Payments DB timeouts",
        "service": "payments-api",
        "severity": "critical",
        "message": "TimeoutError connecting to postgres primary; circuit_breaker_open",
        "expected_service": "payments-api",
        "expected_root_cause_contains": ["database", "postgres", "primary"],
        "expected_runbook": "payments-db-timeouts",
    },
    {
        "case_id": "auth-jwt",
        "title": "Auth 401 spike",
        "service": "auth-service",
        "severity": "high",
        "message": "JWT_SECRET mismatch on canary pod causing 401s",
        "expected_service": "auth-service",
        "expected_root_cause_contains": ["jwt", "secret", "canary"],
        "expected_runbook": "auth-jwt-canary",
    },
    {
        "case_id": "checkout-cdn",
        "title": "Checkout asset failures",
        "service": "checkout-web",
        "severity": "medium",
        "message": "CDN cache miss on checkout.js with CORS blocks",
        "expected_service": "checkout-web",
        "expected_root_cause_contains": ["cdn", "asset", "checkout"],
        "expected_runbook": "checkout-cdn-assets",
    },
    {
        "case_id": "ingest-lag",
        "title": "Ingest lag",
        "service": "ingest-worker",
        "severity": "critical",
        "message": "KafkaConsumerLagExceeded and OOMKilled workers",
        "expected_service": "ingest-worker",
        "expected_root_cause_contains": ["kafka", "lag", "oom", "ingest"],
        "expected_runbook": "ingest-kafka-lag",
    },
    {
        "case_id": "payments-pool",
        "title": "Connection pool exhaustion",
        "service": "payments-api",
        "severity": "high",
        "message": "postgres connection pool saturated after deploy; timeouts rising",
        "expected_service": "payments-api",
        "expected_root_cause_contains": ["database", "postgres", "connection"],
        "expected_runbook": "payments-db-timeouts",
    },
    {
        "case_id": "auth-oauth",
        "title": "OAuth endpoint failures",
        "service": "auth-service",
        "severity": "medium",
        "message": "401 spike from /oauth/token after canary secret drift",
        "expected_service": "auth-service",
        "expected_root_cause_contains": ["jwt", "secret", "token", "canary", "auth"],
        "expected_runbook": "auth-jwt-canary",
    },
]


def _passed(root_cause: str, needles: list[str]) -> bool:
    text = root_cause.lower()
    return any(n.lower() in text for n in needles)


def _hallucinated(root_cause: str, expected_service: str) -> bool:
    text = root_cause.lower()
    for svc in KNOWN_SERVICES:
        if svc == expected_service:
            continue
        if svc in text and expected_service not in text:
            return True
    return False


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
        try:
            citations = json.loads(inv.citations_json or "[]")
        except json.JSONDecodeError:
            citations = []
        citation_hit = any(c.get("slug") == case.get("expected_runbook") for c in citations)
        hallucinated = _hallucinated(inv.root_cause, case["expected_service"])

        results.append(
            EvalCaseResult(
                case_id=case["case_id"],
                expected_service=case["expected_service"],
                predicted_service=alert.service,
                expected_root_cause_contains=case["expected_root_cause_contains"],
                root_cause=inv.root_cause,
                passed=ok and not hallucinated,
                confidence=inv.confidence,
                hallucinated_service=hallucinated,
                citation_hit=citation_hit,
                latency_ms=float(inv.latency_ms),
            )
        )
        latencies.append(float(inv.latency_ms))
        confidences.append(float(inv.confidence))

    passed = sum(1 for r in results if r.passed)
    # Treat keyword match as relevant retrieval proxy for precision/recall on this suite
    tp = passed
    fp = sum(1 for r in results if not r.passed)
    fn = sum(1 for r in results if not r.citation_hit)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    hallucination_rate = sum(1 for r in results if r.hallucinated_service) / len(results)
    citation_hit_rate = sum(1 for r in results if r.citation_hit) / len(results)

    report = EvalReport(
        total=len(results),
        passed=passed,
        accuracy=passed / len(results) if results else 0.0,
        precision=precision,
        recall=recall,
        hallucination_rate=hallucination_rate,
        citation_hit_rate=citation_hit_rate,
        avg_confidence=sum(confidences) / len(confidences) if confidences else 0.0,
        avg_latency_ms=sum(latencies) / len(latencies) if latencies else 0.0,
        results=results,
    )

    db.add(
        EvalRun(
            accuracy=report.accuracy,
            precision=report.precision,
            recall=report.recall,
            hallucination_rate=report.hallucination_rate,
            avg_confidence=report.avg_confidence,
            avg_latency_ms=report.avg_latency_ms,
            total=report.total,
            passed=report.passed,
            report_json=report.model_dump_json(),
        )
    )
    db.commit()

    out = Path(__file__).resolve().parents[2] / "data" / "eval_report.json"
    out.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report
