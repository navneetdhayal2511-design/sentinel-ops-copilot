# Sentinel Ops Copilot

Resume-ready fullstack + ML engineering project: an incident ops console where an agent triages alerts using tools, runbook retrieval (RAG), and an evaluation harness.

## What you can demo

- Auth with roles (`admin` / `engineer` / `viewer`)
- Alert inbox + ingest API
- Agent investigations with tool traces (metrics, logs, deploys, remediation)
- BM25 runbook retrieval
- Audit trail
- Eval suite with accuracy / confidence / latency report
- Optional OpenAI tool-calling path when `OPENAI_API_KEY` is set

## Stack

- **Backend:** FastAPI, SQLAlchemy, SQLite, JWT auth
- **Agent:** heuristic investigator (always works) + optional OpenAI tools
- **RAG:** rank-bm25 over ops runbooks
- **Frontend:** React + Vite
- **Eval:** deterministic cases under `/api/eval/run`

## Quick start (local)

One command serves both the API and the UI:

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env   # Windows
# cp .env.example .env   # macOS/Linux

uvicorn app.main:app --reload --port 8000
```

- UI: http://127.0.0.1:8000
- API docs: http://127.0.0.1:8000/docs

### Optional Vite frontend

If you have Node.js installed, you can also run the React app in `frontend/`:

```bash
cd frontend
npm install
npm run dev
```

UI: http://127.0.0.1:5173

### Demo accounts

| Email | Password | Role |
|---|---|---|
| admin@sentinel.dev | admin123 | admin |
| engineer@sentinel.dev | engineer123 | engineer |
| viewer@sentinel.dev | viewer123 | viewer |

## Optional LLM mode

Add to `backend/.env`:

```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

Without a key, investigations still work via `sentinel-heuristic-v1`.

## Eval

While logged in as admin/engineer in the UI, click **Run eval suite**, or:

```bash
curl -X POST http://127.0.0.1:8000/api/eval/run \
  -H "Authorization: Bearer <token>"
```

Report is also written to `backend/data/eval_report.json`.

## Docker

```bash
docker compose up --build
```

- API + UI: http://localhost:8000
- Optional Vite UI service: http://localhost:5173

## Resume bullets (suggested)

**Fullstack**
- Built a multi-role ops console with JWT auth, alert ingest, investigation workflow, and audit logging.
- Designed REST APIs and a React console for real-time incident triage and agent-trace inspection.

**ML / AI Eng**
- Implemented an alert investigation agent with tool use, runbook retrieval, and confidence-scored recommendations.
- Shipped an evaluation harness measuring root-cause accuracy, confidence, and latency across incident cases.

## Project layout

```text
sentinel-ops-copilot/
  backend/app/
    agent/          # investigator + tools
    rag/            # BM25 retriever
    eval/           # eval harness
    api/            # FastAPI routes
  frontend/src/     # React console
```
