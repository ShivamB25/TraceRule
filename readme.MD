# TraceRule

Deterministic AI compliance compiler. Upload a policy PDF, get PostgreSQL queries that find violations automatically.

## How it works

1. **Upload** a compliance PDF → Claude compiles it into SQL queries (one per rule)
2. **Review** the generated SQL → approve or reject each rule
3. **Scan** runs on a schedule → executes approved queries, flags violations

The LLM is only involved during step 1. Steps 2 and 3 are pure SQL — deterministic, auditable, zero hallucinations.

## Stack

- **FastAPI** — async API
- **PydanticAI** — structured LLM output via Claude Sonnet 4.6 (adaptive thinking)
- **SQLAlchemy** — async ORM with PostgreSQL
- **APScheduler** — background scan every 5 minutes
- **pymupdf4llm** — PDF to markdown in <200ms

## Setup

```bash
# Prerequisites: Python 3.14+, PostgreSQL, uv
createdb tracerule

cp .env.example .env
# Set ANTHROPIC_API_KEY in .env

uv sync
uv run uvicorn app.main:app --reload
```

API docs at [http://localhost:8000/docs](http://localhost:8000/docs)

## API

| Method | Endpoint | What it does |
|--------|----------|--------------|
| POST | `/api/v1/policies/upload` | Upload PDF, kicks off compilation |
| GET | `/api/v1/rules` | List rules (filter by `?status=pending_review`) |
| PATCH | `/api/v1/rules/{id}/approve` | Approve a rule for scanning |
| PATCH | `/api/v1/rules/{id}/reject` | Reject a rule |
| GET | `/api/v1/violations` | List detected violations |
| POST | `/api/v1/scan` | Trigger scan manually |

## Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/tracerule` | PostgreSQL connection |
| `ANTHROPIC_API_KEY` | — | Required for PDF compilation |
| `SCAN_INTERVAL_MINUTES` | `5` | Background scan frequency |
