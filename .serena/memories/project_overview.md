# TraceRule — Project overview (quick reference)

Deterministic compliance compiler. PDF in, PostgreSQL queries out, human approves, scheduler scans.

## Pipeline

1. **Ingest**: POST /upload → pymupdf4llm → Claude compiler agent → SQL rules (status=pending_review)
2. **Review**: Human approves/rejects each SQL rule via PATCH endpoint
3. **Scan**: APScheduler runs approved SQL every N minutes, logs violations, no LLM involved

## Stack

Python >=3.13, FastAPI, PydanticAI (claude-sonnet-4-6 with adaptive thinking), SQLAlchemy 2.x async (asyncpg), APScheduler 3.x, pymupdf4llm. Package manager: uv.

## Config (.env)

- `DATABASE_URL` — Postgres connection string
- `ANTHROPIC_API_KEY` — required for compilation
- `SCAN_INTERVAL_MINUTES` — default 5

## Forbidden

LangChain, LangGraph, Instructor, Celery, Redis, Docling, Alembic.
