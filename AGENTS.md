# TraceRule — Project Knowledge Base

**Generated:** 2026-02-21  
**Commit:** 91ca8d6  
**Branch:** main

## OVERVIEW

Deterministic AI compliance compiler. Ingests policy files (`.pdf` or `.md`), compiles policies into PostgreSQL queries via PydanticAI/Claude, human approves the SQL, APScheduler executes approved queries to detect violations. Zero LLM during scan phase.

**Stack:** FastAPI + PydanticAI + SQLAlchemy async + APScheduler 3.x + pymupdf4llm  
**Model:** `anthropic:claude-sonnet-4-6` with adaptive thinking  
**Python:** >=3.13 | **Package manager:** uv

## STRUCTURE

```
app/
├── main.py              # FastAPI app + lifespan (scheduler + DB init)
├── config.py            # pydantic-settings BaseSettings (.env)
├── database.py          # async engine, session factory, get_db()
├── models.py            # Policy, Rule, Violation (SQLAlchemy async)
├── schemas.py           # CompiledRule (agent output) + API req/res models
├── agents/
│   ├── compiler.py      # policy text -> list[CompiledRule] via Claude
│   └── explainer.py     # violation -> 2-sentence English explanation
├── services/
│   ├── ingestion.py     # policy upload (.pdf/.md) -> text -> compile -> save
│   └── scanner.py       # Execute approved SQL, log violations (zero LLM)
└── routes/
    ├── policies.py      # POST /api/v1/policies/upload
    ├── rules.py         # GET/PATCH rules (list, approve, reject)
    └── violations.py    # GET violations, POST /api/v1/scan
docs/
└── ARCHITECTURE_RESEARCH.md  # Hackathon/Devpost submission doc
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add API endpoint | `app/routes/` | `APIRouter` + `Depends(get_db)` |
| Add ORM model | `app/models.py` | Inherit `Base`, use `Mapped` types |
| Add response schema | `app/schemas.py` | Need `model_config = {"from_attributes": True}` for ORM |
| Add PydanticAI agent | `app/agents/` | MUST use `@lru_cache` factory — see compiler.py |
| Modify scan logic | `app/services/scanner.py` | Pure SQL, zero LLM |
| Modify ingestion | `app/services/ingestion.py` | Supports `.pdf` (pymupdf4llm) and `.md` (UTF-8 decode) |
| Change scan interval | `.env` | `SCAN_INTERVAL_MINUTES=5` |
| Register new router | `app/main.py:58-62` | `app.include_router(r, prefix="/api/v1")` |
| Background tasks | `app/routes/policies.py` | Manual session via `async_session_factory()` — NOT `Depends(get_db)` |

## CODE MAP

| Symbol | Type | File | Role |
|--------|------|------|------|
| `app` | FastAPI | `main.py:48` | App instance with lifespan |
| `lifespan` | asynccontextmanager | `main.py:24` | DB init + APScheduler lifecycle |
| `scheduled_scan` | async func | `main.py:17` | APScheduler job target |
| `Settings` / `settings` | BaseSettings | `config.py:4/14` | `DATABASE_URL`, `ANTHROPIC_API_KEY`, `SCAN_INTERVAL_MINUTES` |
| `engine` | AsyncEngine | `database.py:7` | Module-level singleton |
| `async_session_factory` | async_sessionmaker | `database.py:8` | Module-level singleton |
| `get_db` | async generator | `database.py:11` | FastAPI dependency |
| `Base` | DeclarativeBase | `models.py:9` | ORM base with `AsyncAttrs` mixin |
| `Policy` | ORM | `models.py:13` | `filename`, `markdown_text`, `status` |
| `Rule` | ORM | `models.py:23` | `title`, `source_quote`, `severity`, `compiled_sql`, `is_deterministic`, `status` |
| `Violation` | ORM | `models.py:37` | `record_pk`, `violating_data` (JSONB), `ai_explanation`, `status` |
| `CompiledRule` | Pydantic | `schemas.py:4` | Agent output schema |
| `CompilerDeps` | dataclass | `agents/compiler.py:11` | Agent deps — `db_schema_context: str` |
| `get_compiler_agent` | `@lru_cache` factory | `agents/compiler.py:27` | `Agent[CompilerDeps, list[CompiledRule]]` |
| `get_explainer_agent` | `@lru_cache` factory | `agents/explainer.py:6` | `Agent[None, str]` |
| `ingest_policy` | async func | `services/ingestion.py:53` | policy bytes -> text -> compile -> save rules |
| `_introspect_db_schema` | async func | `services/ingestion.py:17` | Queries `information_schema.columns`, skips internal tables |
| `run_deterministic_scan` | async func | `services/scanner.py:12` | Execute approved SQL, dedup by rule_id+record_pk, save violations |
| `_explain_new_violations` | async func | `services/scanner.py:48` | AI explanations for unexplained violations |

## 3-PHASE PIPELINE

```
Phase 1: INGESTION (BackgroundTasks)
POST /upload -> parse policy text (.pdf via pymupdf4llm, .md via decode) -> CompilerAgent -> list[CompiledRule] -> DB (status=pending_review)

Phase 2: HITL (Frontend -> API)
  GET /rules?status=pending_review -> human reviews SQL -> PATCH /rules/{id}/approve -> status=approved

Phase 3: SCAN (APScheduler, zero LLM)
  AsyncIOScheduler -> SELECT approved+deterministic rules -> execute compiled_sql -> save violations -> ExplainerAgent
```

## FRONTEND REQUEST FLOW (React)

```
Page load (App mount):
  Promise.all([GET /api/v3/rules, GET /api/v3/violations])

Upload flow:
  POST /api/v3/policies/upload -> returns {id, status="processing"}
  Background task runs ingest_policy() for SAME policy_id
  Frontend polls GET /api/v3/rules?policy_id={id} every 3s until rules exist

Review flow:
  PATCH /api/v3/rules/{id}/approve OR /reject
  Frontend updates local state for the changed rule

Scan flow:
  POST /api/v3/scan -> returns {violations_found}
  Frontend then GET /api/v3/violations
  If ai_explanation is null, frontend polls violations every 5s
```

- React dev mode (`StrictMode`) causes duplicate initial GETs on page load; this is expected locally and not a backend bug.
- Important fix (2026-02-21): background ingestion now updates the existing placeholder policy created by upload route, instead of creating a second policy row. Rule `policy_id` now matches upload response `id`.

## CONVENTIONS

### PydanticAI (verified against v0.7+ docs)
- Constructor: `output_type=` — NEVER `result_type=` (deprecated)
- Results: `result.output` — NEVER `result.data` (deprecated)
- Adaptive thinking: `AnthropicModelSettings(anthropic_thinking={"type": "adaptive"}, anthropic_effort="high")`
- Dynamic prompts: `@agent.system_prompt` with `RunContext[DepsType]`
- Lazy init: `@lru_cache(maxsize=1)` factory — agent validates API key at construction, crashes if missing

### SQLAlchemy 2.x async
- `DeclarativeBase` + `AsyncAttrs` mixin
- `Mapped[T]` + `mapped_column()` for all columns
- `async_sessionmaker(engine, expire_on_commit=False)`
- Routes: `Depends(get_db)` | Background tasks: `async_session_factory()` directly

### APScheduler 3.x (NOT v4)
- `AsyncIOScheduler(timezone="UTC")`
- `scheduler.add_job(fn, IntervalTrigger(minutes=N))`
- Lifecycle in FastAPI lifespan context manager

### FastAPI
- All routes: `/api/v1/` prefix
- ORM responses: `model_config = {"from_attributes": True}`
- Policy ingestion: `BackgroundTasks.add_task()`

## ANTI-PATTERNS

### Forbidden Libraries
LangChain, LangGraph, Instructor, Celery, Redis, Docling, Alembic

### Forbidden Patterns
| Don't | Do Instead |
|-------|------------|
| `Agent(..., result_type=X)` | `Agent(..., output_type=X)` |
| `result.data` | `result.output` |
| Module-level `Agent(...)` | `@lru_cache` factory function |
| `Any` type hints | Explicit types everywhere |
| Bare `db.execute(text(...))` in scanner | Wrap in try/except |
| `Depends(get_db)` in background tasks | `async_session_factory()` directly |
| Nested DDD directories | Flat folder structure |
| `@app.on_event("startup")` | Lifespan context manager |
| Alembic migrations | `Base.metadata.create_all()` in lifespan |

## COMMANDS

```bash
uv run uvicorn app.main:app --reload   # Dev server (docs: http://localhost:8000/docs)
uv sync                                 # Install deps
uv add <package>                        # Add dependency
```

## NOTES

- **Tests** — pytest + pytest-asyncio, in-memory SQLite via aiosqlite (`tests/conftest.py`, `tests/test_rules.py`, `tests/test_violations.py`, `tests/test_scanner.py`, `tests/test_policies.py`). Config in `pyproject.toml` only. 23 tests. No CI/CD.
- **Docker** — Multi-stage `Dockerfile` (build via `ghcr.io/astral-sh/uv`, runtime via `python:3.13-slim-bookworm`, non-root user) + `docker-compose.yml` with PostgreSQL service.
- **Ingestion formats** — `.pdf` uses `pymupdf4llm.to_markdown()` (`str | list[dict]` handled), `.md` uses UTF-8 decode
- **Inline imports** in `routes/policies.py` (lines 12, 27) avoid circular deps — intentional
- **Explanation cap** — `EXPLANATION_MODEL_LIMIT_PER_SCAN` (default 25) limits model-generated explanations per scan; overflow rows get deterministic fallback text.
- **Ruff** cache exists (`.ruff_cache/`) but no config file — run ad-hoc
