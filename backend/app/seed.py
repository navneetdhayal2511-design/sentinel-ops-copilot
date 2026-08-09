from __future__ import annotations

import json
import uuid

from sqlalchemy.orm import Session

from app.auth import hash_password
from app.config import RUNBOOKS_DIR
from app.models import Alert, Runbook, User

RUNBOOKS = [
    {
        "slug": "payments-db-timeouts",
        "title": "Payments API database timeouts",
        "service": "payments-api",
        "tags": "postgres timeout circuit_breaker",
        "content": """
Symptom: elevated 5xx, TimeoutError to postgres primary, circuit breaker open.
Checks:
1) Compare primary vs replica lag and connection saturation
2) Inspect recent schema migrations / long transactions
3) Confirm pool size after last deploy
Mitigation:
- Shift reads to replica
- Restart unhealthy payments-api pods
- Page DB on-call if primary recovery > 5 minutes
""".strip(),
    },
    {
        "slug": "auth-jwt-canary",
        "title": "Auth service JWT secret mismatch",
        "service": "auth-service",
        "tags": "jwt secret canary 401 oauth",
        "content": """
Symptom: 401 spike on /oauth/token after canary deploy.
Root pattern: canary pods mounted stale JWT_SECRET from old secret version.
Mitigation:
- Rollback canary
- Sync vault secret revision
- Bounce auth-service and watch token success rate
""".strip(),
    },
    {
        "slug": "checkout-cdn-assets",
        "title": "Checkout CDN asset failures",
        "service": "checkout-web",
        "tags": "cdn cors assets javascript",
        "content": """
Symptom: checkout page broken, missing checkout.js, CORS noise from partners.
Mitigation:
- Purge CDN path for release assets
- Verify content hash in release manifest
- Confirm partner origins in CORS allowlist
""".strip(),
    },
    {
        "slug": "ingest-kafka-lag",
        "title": "Ingest worker Kafka lag and OOM",
        "service": "ingest-worker",
        "tags": "kafka lag oom consumer",
        "content": """
Symptom: KafkaConsumerLagExceeded and OOMKilled replicas.
Mitigation:
- Scale workers and raise memory limits
- Pause low-priority consumers
- Inspect message size distribution and poison pills
""".strip(),
    },
]

DEMO_ALERTS = [
    {
        "title": "High 5xx on checkout payments",
        "service": "payments-api",
        "severity": "critical",
        "message": "TimeoutError connecting to postgres primary; circuit_breaker_open: payments-db",
    },
    {
        "title": "OAuth token failure spike",
        "service": "auth-service",
        "severity": "high",
        "message": "JWT_SECRET mismatch on canary pod; 401 rate up 9x on /oauth/token",
    },
    {
        "title": "Checkout bundle failing to load",
        "service": "checkout-web",
        "severity": "medium",
        "message": "CDN cache miss storm on /assets/checkout.js and partner CORS blocks",
    },
    {
        "title": "Event ingest lag critical",
        "service": "ingest-worker",
        "severity": "critical",
        "message": "KafkaConsumerLagExceeded topic=events.raw; OOMKilled replica ingest-worker-7",
    },
]


def seed_if_empty(db: Session) -> None:
    if db.query(User).count() == 0:
        db.add_all(
            [
                User(
                    email="admin@sentinel.dev",
                    full_name="Avery Admin",
                    hashed_password=hash_password("admin123"),
                    role="admin",
                ),
                User(
                    email="engineer@sentinel.dev",
                    full_name="Riley Engineer",
                    hashed_password=hash_password("engineer123"),
                    role="engineer",
                ),
                User(
                    email="viewer@sentinel.dev",
                    full_name="Casey Viewer",
                    hashed_password=hash_password("viewer123"),
                    role="viewer",
                ),
            ]
        )

    if db.query(Runbook).count() == 0:
        for rb in RUNBOOKS:
            path = RUNBOOKS_DIR / f"{rb['slug']}.md"
            path.write_text(f"# {rb['title']}\n\n{rb['content']}\n", encoding="utf-8")
            db.add(Runbook(**rb))

    if db.query(Alert).count() == 0:
        for item in DEMO_ALERTS:
            db.add(
                Alert(
                    external_id=f"demo-{uuid.uuid4().hex[:10]}",
                    title=item["title"],
                    service=item["service"],
                    severity=item["severity"],
                    status="open",
                    source="seed",
                    message=item["message"],
                    raw_payload=json.dumps(item),
                )
            )

    db.commit()
