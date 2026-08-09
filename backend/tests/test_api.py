import pytest
from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine
from app.main import app
from app.seed import seed_if_empty


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()
    yield


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _login(client: TestClient) -> str:
    res = client.post(
        "/api/auth/login/json",
        json={"email": "admin@sentinel.dev", "password": "admin123"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["access_token"]
    assert data["refresh_token"]
    return data["access_token"]


def test_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_login_and_alerts(client):
    token = _login(client)
    res = client.get("/api/alerts", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert len(res.json()) >= 4


def test_investigate_and_citations(client):
    token = _login(client)
    alerts = client.get("/api/alerts", headers={"Authorization": f"Bearer {token}"}).json()
    alert_id = alerts[0]["id"]
    res = client.post(
        f"/api/investigations/alerts/{alert_id}/run",
        headers={"Authorization": f"Bearer {token}"},
        json={"use_llm": False},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["root_cause"]
    assert isinstance(body["citations"], list)
    assert len(body["citations"]) >= 1


def test_webhook_ingest(client):
    res = client.post(
        "/api/webhooks/alerts",
        headers={"X-Sentinel-Token": "test-webhook"},
        json={
            "title": "Webhook DB issue",
            "service": "payments-api",
            "severity": "critical",
            "message": "postgres timeout from webhook",
            "auto_investigate": False,
        },
    )
    assert res.status_code == 200
    assert res.json()["source"] == "webhook"


def test_feedback_and_eval(client):
    token = _login(client)
    headers = {"Authorization": f"Bearer {token}"}
    alerts = client.get("/api/alerts", headers=headers).json()
    inv = client.post(
        f"/api/investigations/alerts/{alerts[0]['id']}/run",
        headers=headers,
        json={"use_llm": False},
    ).json()
    fb = client.post(
        f"/api/investigations/{inv['id']}/feedback",
        headers=headers,
        json={"decision": "approved", "notes": "looks good"},
    )
    assert fb.status_code == 200
    assert fb.json()["decision"] == "approved"

    ev = client.post("/api/eval/run?use_llm=false", headers=headers)
    assert ev.status_code == 200
    report = ev.json()
    assert report["total"] >= 4
    assert "citation_hit_rate" in report
    assert report["accuracy"] >= 0.5


def test_refresh_token(client):
    login = client.post(
        "/api/auth/login/json",
        json={"email": "admin@sentinel.dev", "password": "admin123"},
    ).json()
    refreshed = client.post(
        "/api/auth/refresh",
        json={"refresh_token": login["refresh_token"]},
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"]
