# Deploy Sentinel Ops Copilot

## Option A — Render (recommended free tier)

1. Push this repo to GitHub (already done if you followed setup).
2. Go to [https://render.com](https://render.com) → **New** → **Blueprint**.
3. Select `navneetdhayal2511-design/sentinel-ops-copilot` and apply `render.yaml`.
4. Set `PUBLIC_BASE_URL` to your Render URL after first deploy.
5. Optional: set `OPENAI_API_KEY` for LLM mode.

Demo login after deploy: `admin@sentinel.dev` / `admin123`

## Option B — Railway

1. Create a new Railway project from this GitHub repo.
2. Add a Postgres plugin and set:
   - `DATABASE_URL` = Railway Postgres URL (use `postgresql+psycopg2://...`)
   - `SECRET_KEY` = long random string
   - `WEBHOOK_TOKEN` = random token
   - `PUBLIC_BASE_URL` = your Railway domain
3. Deploy using `backend/Dockerfile` / `railway.toml`.

## Option C — Docker Compose (local prod-like)

```bash
docker compose up --build
```

- API/UI: http://localhost:8000
- Postgres: localhost:5432 (`sentinel` / `sentinel`)

## Webhook example

```bash
curl -X POST "$PUBLIC_BASE_URL/api/webhooks/alerts" \
  -H "Content-Type: application/json" \
  -H "X-Sentinel-Token: $WEBHOOK_TOKEN" \
  -d '{
    "title": "High 5xx on payments",
    "service": "payments-api",
    "severity": "critical",
    "message": "TimeoutError connecting to postgres primary",
    "auto_investigate": true
  }'
```
