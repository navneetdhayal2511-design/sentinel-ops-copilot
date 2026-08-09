# Sentinel Ops Copilot

Fullstack + ML engineering project: an incident ops console where an agent triages alerts with tools, hybrid runbook RAG, human feedback, observability, and a measurable evaluation harness.

**Repo:** https://github.com/navneetdhayal2511-design/sentinel-ops-copilot

---

## Case study

### Problem
On-call engineers drown in noisy alerts. Chatbot wrappers rarely help because they lack tools, citations, feedback loops, and quality measurement.

### Solution
Sentinel ingests alerts (UI + webhook), runs an investigation agent, retrieves runbooks, proposes root cause + remediation, and records traces/audit events. Humans can approve, reject, or edit recommendations. An eval suite tracks accuracy, citation hit rate, hallucination rate, confidence, and latency.

### Architecture

```text
Alert (UI / Webhook)
   → FastAPI API (JWT + refresh tokens)
   → Investigator agent
        ├─ Tools: metrics, logs, deploys, remediation
        ├─ Hybrid RAG: BM25 + hashing embeddings (+ optional OpenAI embeddings)
        └─ Traces + citations persisted
   → Human feedback (approve / reject / edit)
   → Eval harness + observability dashboard
```

### Design tradeoffs
| Choice | Why |
|---|---|
| Heuristic investigator by default | Reliable offline demos, deterministic evals |
| Optional LLM tool-calling | Stronger reasoning when `OPENAI_API_KEY` is set |
| Hybrid RAG | Works without embedding API; upgrades automatically with OpenAI |
| SQLite default / Postgres optional | Fast local start; production-ready DB path |
| In-process background jobs | Simple async investigations without Redis for MVP |

### Example eval snapshot (heuristic mode)
- Cases: 6 incident scenarios
- Metrics: accuracy, precision/recall proxy, citation hit rate, hallucination rate, latency
- Run via UI (**Run eval suite**) or `POST /api/eval/run`

---

## Features
- Role-based auth (`admin` / `engineer` / `viewer`) + refresh tokens
- Alert inbox, manual ingest, PagerDuty-style webhook ingest
- Agent investigations with tool traces
- Hybrid RAG citations in the investigation panel
- Human-in-the-loop feedback
- Observability endpoint (latency, feedback rates, taxonomy, eval trend)
- Eval harness with persisted eval runs
- Docker Compose (API + Postgres + optional Vite UI)
- GitHub Actions CI
- Deploy blueprints for Render / Railway

---

## Quick start (Windows)

**Easiest:** double-click `Start Sentinel.bat` on your Desktop  
(or `sentinel-ops-copilot\start-sentinel.bat`).

Then open http://127.0.0.1:8000

**Autostart at login (already installable):**
```powershell
powershell -ExecutionPolicy Bypass -File .\install-autostart.ps1
```

**Manual:**
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

- UI: http://127.0.0.1:8000
- API docs: http://127.0.0.1:8000/docs

### Demo accounts

| Email | Password | Role |
|---|---|---|
| admin@sentinel.dev | admin123 | admin |
| engineer@sentinel.dev | engineer123 | engineer |
| viewer@sentinel.dev | viewer123 | viewer |

### Optional LLM / embeddings
```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
```

### Tests
```bash
cd backend
pytest -q
```

### Deploy
See [DEPLOY.md](./DEPLOY.md).

---

## Webhook ingest

```bash
curl -X POST http://127.0.0.1:8000/api/webhooks/alerts \
  -H "Content-Type: application/json" \
  -H "X-Sentinel-Token: sentinel-webhook-dev-token" \
  -d "{\"title\":\"High 5xx\",\"service\":\"payments-api\",\"severity\":\"critical\",\"message\":\"TimeoutError connecting to postgres primary\",\"auto_investigate\":true}"
```

---

## Resume bullets

**Fullstack**
- Built a multi-role incident console with JWT/refresh auth, webhook ingest, async investigation jobs, and audit logging.
- Shipped observability surfaces (latency, feedback rates, failure taxonomy, eval trend) and Docker/Postgres deploy paths.

**ML / AI Eng**
- Implemented a hybrid RAG investigator (BM25 + embeddings) with citations, tool use, and human feedback loop.
- Created an evaluation harness measuring accuracy, citation hit rate, hallucination rate, confidence, and latency.

---

## Project layout

```text
sentinel-ops-copilot/
  backend/app/
    agent/          # investigator + tools
    rag/            # hybrid retriever
    eval/           # eval harness
    api/            # FastAPI routes (auth, alerts, webhooks, feedback)
    static/         # ops console UI
  frontend/         # optional Vite React app
  .github/workflows # CI
  DEPLOY.md
```
