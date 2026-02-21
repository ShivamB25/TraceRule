# TraceRule — Project Overview

## Purpose
Deterministic AI compliance compiler. Ingests legal/compliance PDFs, compiles policy text into PostgreSQL queries via PydanticAI/Claude, human reviews & approves the SQL, then APScheduler executes approved queries to detect violations. Zero LLM involvement during scan phase — fully deterministic and auditable.

## Tech Stack
- **Python 3.14** (managed with `uv`)
- **FastAPI** — async REST API
- **PydanticAI** (v1.62+) — structured LLM output via `anthropic:claude-sonnet-4-6` with adaptive thinking (`anthropic_thinking={"type":"adaptive"}` + `anthropic_effort`)
- **SQLAlchemy 2.x** — async ORM with PostgreSQL (asyncpg driver)
- **APScheduler 3.x** — background scan every N minutes (NOT v4)
- **pymupdf4llm** — PDF-to-markdown extraction
- **Pydantic v2** / **pydantic-settings** — validation + config
- **aiosqlite** — test-only (in-memory SQLite for pytest)

## 3-Phase Pipeline
1. **INGESTION** (BackgroundTasks): POST /upload → pymupdf4llm → CompilerAgent → list[CompiledRule] → DB (status=pending_review)
2. **HITL** (Frontend → API): GET /rules → human reviews SQL → PATCH /rules/{id}/approve → status=approved
3. **SCAN** (APScheduler, zero LLM): AsyncIOScheduler → fetch approved+deterministic rules → execute compiled_sql → save violations → ExplainerAgent for explanations

## Key Config (`.env`)
- `DATABASE_URL` — PostgreSQL connection (default: `postgresql+asyncpg://postgres:postgres@localhost:5432/tracerule`)
- `ANTHROPIC_API_KEY` — required for PDF compilation
- `SCAN_INTERVAL_MINUTES` — background scan frequency (default: 5)

## Forbidden Libraries
LangChain, LangGraph, Instructor, Celery, Redis, Docling, Alembic
