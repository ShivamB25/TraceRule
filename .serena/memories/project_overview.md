# TraceRule — Project Overview

Neuro-symbolic compliance compiler. Policy PDFs in → deontic logic ASTs + PostgreSQL queries out → human approves → scheduler scans → adversarial courtroom judges subjective clauses.

## Two Pipelines (V1 + V3 coexist)

### V1 Pipeline (original, still works)
1. POST /api/v1/policies/upload → pymupdf4llm → Claude compiler agent → raw SQL rules (status=pending_review)
2. Human approves/rejects via PATCH
3. APScheduler runs approved SQL every N minutes, logs violations, generates AI explanations

### V3 Pipeline (neuro-symbolic, current focus)
1. POST /api/v3/policies/upload → pymupdf4llm → Global Ontology extraction → Claude extractor agent → Deontic Logic AST (LogicNode/Condition trees) → AST compiler → SQL with `1=1` for vague clauses
2. Extractor agent has `@output_validator` reflexion — runs `EXPLAIN` on generated SQL, bounces Postgres errors back to Claude via `ModelRetry`
3. Human approves/rejects V3 rules via PATCH
4. Scanner runs approved rules:
   - **Pure deterministic** (no IS_VAGUE): Execute compiled SQL, save violations (confidence=1.0)
   - **Mixed** (deterministic + IS_VAGUE): SQL pre-filter returns superset (IS_VAGUE=`1=1`), then adversarial courtroom evaluates each candidate
   - **Pure vague**: BM25 text search on company_records → courtroom evaluates candidates
5. Courtroom: Prosecutor + Defender run in parallel via asyncio.gather, Chief Justice renders final Verdict with confidence_score

## Stack

Python >=3.13, FastAPI, PydanticAI (claude-sonnet-4-6), SQLAlchemy 2.x async (asyncpg), APScheduler 3.x, pymupdf4llm. Package manager: uv.

**Removed:** pgvector, numpy (embedding structured data is an anti-pattern; courtroom IS the semantic reranker)

## Config (.env)

- `DATABASE_URL` — Postgres connection string (asyncpg)
- `ANTHROPIC_API_KEY` — required for compilation + courtroom
- `SCAN_INTERVAL_MINUTES` — default 5
- `EXPLANATION_MODEL_LIMIT_PER_SCAN` — default 25

## Test State

78 tests across 10 files, all passing. In-memory SQLite via aiosqlite. No API key needed for tests.

## Forbidden

LangChain, LangGraph, Instructor, Celery, Redis, Docling, Alembic, pgvector, numpy.
