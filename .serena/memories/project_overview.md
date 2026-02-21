# TraceRule — Project overview (quick reference)

Deterministic compliance compiler. PDF in, PostgreSQL queries out, human approves, scheduler scans.

## Pipeline

1. **Ingest**: POST /upload → pymupdf4llm → Claude compiler agent → SQL rules (status=pending_review)
2. **Review**: Human approves/rejects each SQL rule via PATCH endpoint
3. **Scan**: APScheduler runs approved SQL every N minutes, logs violations, no LLM involved

## Stack

Python >=3.13, FastAPI, PydanticAI (claude-sonnet-4-6 with adaptive thinking), SQLAlchemy 2.x async (asyncpg), APScheduler 3.x, pymupdf4llm. Package manager: uv.

## Live-tested (2026-02-21)

Full end-to-end pipeline verified with live Anthropic API:
- PDF upload → Claude compiles 3 rules from employee policy → correct SQL generated
- HITL approve → scan detects 6 violations across 7 employees → AI explanations generated
- Dedup confirmed: re-scan returns 0 new violations
- All edge cases pass: 404s, 422s, 400 bad status, filter params

## Config (.env)

- `DATABASE_URL` — Postgres connection string
- `ANTHROPIC_API_KEY` — required for compilation (bridged to os.environ by config.py)
- `SCAN_INTERVAL_MINUTES` — default 5

## Gotchas discovered during live testing

- PydanticAI reads `ANTHROPIC_API_KEY` from `os.environ`, not from pydantic-settings. Config.py bridges this gap.
- PostgreSQL `NUMERIC` columns return `Decimal` objects. Scanner's `_make_json_safe()` coerces them to `float` before JSONB insert.
- `pymupdf4llm.to_markdown()` returns `str | list[dict]` — runtime type narrowing in ingestion.py.

## Forbidden

LangChain, LangGraph, Instructor, Celery, Redis, Docling, Alembic.


## Recent updates (2026-02-22)

- Upload/ingestion policy consistency fix: background ingestion now uses the same `policy_id` created by upload route (no duplicate policy row for one upload).
- Frontend now includes a dedicated live request timeline panel with endpoint-level technical trace mode.
- Demo data workflow no longer requires full AML unzip; capped extraction + loader scripts support 1-2GB demo footprint.


## Baseline decisions kept from 2026-02-21

- Compiler uses `claude-sonnet-4-6` with adaptive thinking at `high` effort.
- Explainer uses the same model with adaptive thinking at `medium` effort.
- `/scan` route uses `Depends(get_db)` (not manual session factory) to keep tests isolated.
- Pytest config is centralized in `pyproject.toml` (no separate `pytest.ini`).
- Docker build follows multi-stage uv pattern; Python baseline is `>=3.13`.

## Validation snapshot

- Backend regression suite: 23 tests passing across rules, violations, scanner, and policies.
- Live E2E snapshot: 3 compiled rules, 6 violations from 7 records, and re-scan dedup produced 0 new violations.
