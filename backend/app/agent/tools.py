from __future__ import annotations

import json
from datetime import datetime, timedelta

# Deterministic "telemetry" so demos and evals are reproducible without live infra.


SERVICE_METRICS = {
    "payments-api": {
        "error_rate": 0.18,
        "p99_ms": 2400,
        "cpu": 0.72,
        "deploy": "v2.14.3 rolled out 22m ago",
        "recent_errors": [
            "TimeoutError connecting to postgres primary",
            "circuit_breaker_open: payments-db",
        ],
    },
    "auth-service": {
        "error_rate": 0.09,
        "p99_ms": 1100,
        "cpu": 0.41,
        "deploy": "v1.8.1 stable for 3d",
        "recent_errors": [
            "JWT_SECRET mismatch on canary pod",
            "401 spike from /oauth/token",
        ],
    },
    "checkout-web": {
        "error_rate": 0.04,
        "p99_ms": 1800,
        "cpu": 0.33,
        "deploy": "v5.2.0 1h ago",
        "recent_errors": [
            "CDN cache miss storm on /assets/checkout.js",
            "CORS blocked from partner.example",
        ],
    },
    "ingest-worker": {
        "error_rate": 0.22,
        "p99_ms": 5000,
        "cpu": 0.91,
        "deploy": "v0.9.4 40m ago",
        "recent_errors": [
            "KafkaConsumerLagExceeded topic=events.raw",
            "OOMKilled replica ingest-worker-7",
        ],
    },
}


def get_service_metrics(service: str) -> dict:
    key = service.lower().strip()
    metrics = SERVICE_METRICS.get(key)
    if not metrics:
        return {
            "service": service,
            "error_rate": 0.02,
            "p99_ms": 300,
            "cpu": 0.2,
            "deploy": "unknown",
            "recent_errors": ["no synthetic telemetry for this service"],
        }
    return {"service": key, **metrics}


def get_recent_deploys(service: str) -> list[dict]:
    now = datetime.utcnow()
    base = get_service_metrics(service)
    return [
        {
            "service": service,
            "version": base.get("deploy", "unknown"),
            "at": (now - timedelta(minutes=30)).isoformat() + "Z",
            "author": "ci-bot",
        }
    ]


def search_logs(service: str, query: str) -> list[dict]:
    metrics = get_service_metrics(service)
    hits = []
    for err in metrics.get("recent_errors", []):
        if not query or any(tok in err.lower() for tok in query.lower().split()):
            hits.append(
                {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "service": service,
                    "level": "ERROR",
                    "message": err,
                }
            )
    if not hits:
        hits.append(
            {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "service": service,
                "level": "INFO",
                "message": f"No log lines matched query={query!r}",
            }
        )
    return hits


def propose_remediation(service: str, root_cause: str) -> dict:
    playbooks = {
        "payments-api": [
            "Failover read traffic to payments-db replica",
            "Increase connection pool + restart payments-api canary",
            "Page DB on-call if primary still unhealthy after 5m",
        ],
        "auth-service": [
            "Rollback canary pods with mismatched JWT_SECRET",
            "Re-sync secrets from vault and bounce auth-service",
            "Invalidate bad tokens and monitor /oauth/token 401 rate",
        ],
        "checkout-web": [
            "Purge CDN path /assets/checkout.js",
            "Tighten CORS allowlist for partner origins",
            "Verify asset hash in release manifest",
        ],
        "ingest-worker": [
            "Scale ingest-worker replicas and raise memory limit",
            "Pause non-critical consumers until lag < threshold",
            "Inspect OOM events and recent message size spike",
        ],
    }
    actions = playbooks.get(service.lower(), ["Gather more signals", "Page service owner"])
    return {
        "service": service,
        "root_cause": root_cause,
        "actions": actions,
        "rollback_candidate": True,
        "notes": "Actions are suggested, not auto-executed.",
    }


TOOL_SPECS = {
    "get_service_metrics": get_service_metrics,
    "get_recent_deploys": get_recent_deploys,
    "search_logs": search_logs,
    "propose_remediation": propose_remediation,
}


def run_tool(name: str, **kwargs) -> str:
    fn = TOOL_SPECS.get(name)
    if not fn:
        return json.dumps({"error": f"unknown tool {name}"})
    return json.dumps(fn(**kwargs), default=str)
