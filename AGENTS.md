# TraceRule — Project Knowledge Base

**Updated:** 2026-02-22
**Branch:** main

## OVERVIEW

Neuro-symbolic compliance compiler. Two coexisting pipelines:

- **V1**: Policy PDF → Claude compiles to raw SQL → human approves → scheduler executes SQL → violations logged. Zero LLM during scan.
- **V3**: Policy PDF → global ontology extraction → Claude compiles to deontic logic ASTs → pure-Python AST→SQL compiler → SQL auto-healed via EXPLAIN → human approves → scanner routes to deterministic SQL, SQL+courtroom, or BM25+courtroom paths → violations with confidence scores.

The model runs during rule creation (and courtroom evaluation for subjective clauses). Deterministic scanning never touches the LLM.

**Stack:** FastAPI + PydanticAI + SQLAlchemy async + APScheduler 3.x + pymupdf4llm
**Model:** `claude-sonnet-4-6` with configurable thinking budgets
**Python:** >=3.13 | **Package manager:** uv

## STRUCTURE

```
app/
├── main.py              # FastAPI app + lifespan (scheduler + DB init), CORS, health
├── config.py            # pydantic-settings BaseSettings (.env)
├── database.py          # async engine, session factory, get_db()
├── models.py            # Policy, Rule, Violation, CompanyRecord, V3Rule, V3Violation + TypeDecorators
├── schemas.py           # V1 CompiledRule + V3 GlobalOntology, Condition, LogicNode, SymbolicRule, responses
├── ast_compiler.py      # Pure-Python recursive AST→SQL compiler (no LLM)
├── agents/
│   ├── compiler.py      # V1: policy text → list[CompiledRule] via Claude
│   ├── explainer.py     # V1: violation → 2-sentence explanation via Claude
│   ├── extractor.py     # V3: policy text → list[SymbolicRule] (deontic AST) with @output_validator reflexion
│   └── courtroom.py     # V3: Prosecutor + Defender + Chief Justice adversarial debate
├── services/
│   ├── ingestion.py     # V1 ingest_policy() + V3 ingest_policy_v3() with global ontology + chunking
│   └── scanner.py       # V1 run_deterministic_scan() + V3 run_v3_scan() with 3-path routing
├── routes/              # V1 endpoints (/api/v1/)
│   ├── policies.py      # POST /policies/upload
│   ├── rules.py         # GET/PATCH rules
│   └── violations.py    # GET violations, POST /scan
└── api/                 # V3 endpoints (/api/v3/)
    ├── __init__.py
    └── router.py        # POST upload, GET/PATCH rules, GET violations, POST scan

tests/                   # 78 tests, pytest + pytest-asyncio, in-memory SQLite via aiosqlite
├── conftest.py          # DB fixtures, app overrides
├── test_ast_compiler.py # 23 tests: all operators, logic types, edge cases
├── test_policies.py     # 5 tests: V1 upload, missing file, health
├── test_rules.py        # 10 tests: V1 rule CRUD, filters, approve/reject
├── test_scanner.py      # 4 tests: V1 scanner, bad SQL, explanation limit
├── test_violations.py   # 7 tests: V1 violation CRUD, filters
├── test_v3_policies.py  # 4 tests: V3 upload PDF/MD, 422, 400
├── test_v3_rules.py     # 11 tests: V3 rule CRUD, filters, approve/reject
├── test_v3_scanner.py   # 7 tests: V3 scanner, bad SQL, dedup, endpoint
└── test_v3_violations.py # 6 tests: V3 violation CRUD, filters

frontend/                # React 19 + Vite + Tailwind v4
docs/                    # Architecture docs, demo runbooks, agent collaboration diagrams
scripts/                 # Demo data extraction, loading, DB reset
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add V1 API endpoint | `app/routes/` | `APIRouter` + `Depends(get_db)` |
| Add V3 API endpoint | `app/api/router.py` | Same patterns as V1, `/api/v3/` prefix |
| Add ORM model | `app/models.py` | Inherit `Base`, use `Mapped` types, add TypeDecorators for SQLite compat |
| Add response schema | `app/schemas.py` | Need `model_config = {"from_attributes": True}` for ORM |
| Add PydanticAI agent | `app/agents/` | MUST use `@lru_cache` factory |
| Add AST operator | `app/ast_compiler.py` | Update `_compile_condition()` and add tests in `test_ast_compiler.py` |
| Modify V1 scan logic | `app/services/scanner.py` | `run_deterministic_scan()`, pure SQL |
| Modify V3 scan logic | `app/services/scanner.py` | `run_v3_scan()`, 3-path routing |
| Modify V1 ingestion | `app/services/ingestion.py` | `ingest_policy()` |
| Modify V3 ingestion | `app/services/ingestion.py` | `ingest_policy_v3()`, ontology + chunking + extractor |
| Modify courtroom | `app/agents/courtroom.py` | Prosecutor, Defender, Chief Justice agents |
| Change scan interval | `.env` | `SCAN_INTERVAL_MINUTES=5` |
| Register new router | `app/main.py` | `app.include_router(r, prefix="/api/v3")` |
| Background tasks | `app/routes/policies.py`, `app/api/router.py` | Manual session via `async_session_factory()`, NOT `Depends(get_db)` |

## AGENTS

Seven Claude agents, all using `claude-sonnet-4-6`. No agent calls another directly. The service layer (`ingestion.py`, `scanner.py`) passes typed Pydantic schemas between them.

| Agent | File | Output type | Thinking config | When it runs |
|-------|------|-------------|-----------------|-------------|
| Lexicon | `ingestion.py` (inline) | `GlobalOntology` | enabled, 4K budget | Once per V3 ingestion (first 12K chars) |
| Compiler | `agents/compiler.py` | `list[CompiledRule]` | adaptive, high effort | Once per V1 ingestion |
| Extractor | `agents/extractor.py` | `list[SymbolicRuleDraft]` | enabled, 10K budget | Per chunk during V3 ingestion |
| Explainer | `agents/explainer.py` | `str` | adaptive, medium effort | Post-V1-scan, capped at 25 |
| Prosecutor | `agents/courtroom.py` | `LegalArgument` | enabled, 8K budget | Per candidate in V3 semantic scan |
| Defender | `agents/courtroom.py` | `LegalArgument` | enabled, 8K budget | Per candidate, parallel with Prosecutor |
| Chief Justice | `agents/courtroom.py` | `Verdict` | enabled, 16K budget | Per candidate, after both arguments |

### Agent data flow

```
Ingestion:  Lexicon → GlobalOntology → Extractor → SymbolicRuleDraft → AST Compiler → SQL → @output_validator (EXPLAIN) → V3Rule

Scan:       Scanner → record_data+rubric → Prosecutor ─┐
                                           Defender  ───┤ asyncio.gather
                                           Chief Justice ← both arguments → Verdict → V3Violation
```

### Reflexion loop (extractor only)

The `@output_validator` on the extractor agent compiles each AST to SQL, runs `EXPLAIN` in a sandboxed nested transaction, and raises `ModelRetry` with the full Postgres stack trace on failure. Claude sees "column 'emplyee_age' does not exist" and self-corrects. Up to 4 retries. SQL that passes EXPLAIN is guaranteed executable.

### Adversarial courtroom

Prosecutor and Defender run in parallel via `asyncio.gather`. Both produce `LegalArgument{points, evidence_citations}`. The Chief Justice receives both arguments plus the original evidence, then renders `Verdict{is_violation, confidence_score, reasoning}`.

## CODE MAP

| Symbol | Type | File | Role |
|--------|------|------|------|
| `app` | FastAPI | `main.py` | App instance with lifespan |
| `lifespan` | asynccontextmanager | `main.py` | DB init + APScheduler lifecycle |
| `scheduled_scan` | async func | `main.py` | APScheduler job target |
| `Settings` / `settings` | BaseSettings | `config.py` | `DATABASE_URL`, `ANTHROPIC_API_KEY`, `SCAN_INTERVAL_MINUTES` |
| `engine` | AsyncEngine | `database.py` | Module-level singleton |
| `async_session_factory` | async_sessionmaker | `database.py` | Module-level singleton |
| `get_db` | async generator | `database.py` | FastAPI dependency |
| `Base` | DeclarativeBase | `models.py` | ORM base with `AsyncAttrs` mixin |
| `JSONVariant` | TypeDecorator | `models.py` | JSONB on Postgres, JSON on SQLite |
| `TSVectorVariant` | TypeDecorator | `models.py` | TSVECTOR on Postgres, Text on SQLite |
| `Policy` | ORM | `models.py` | `filename`, `markdown_text`, `status` |
| `Rule` | ORM | `models.py` | V1: `title`, `source_quote`, `severity`, `compiled_sql`, `is_deterministic`, `status` |
| `Violation` | ORM | `models.py` | V1: `record_pk`, `violating_data` (JSONB), `ai_explanation`, `status` |
| `CompanyRecord` | ORM | `models.py` | BM25 store: `table_name`, `data_payload`, `search_text`, `ts_vector` (GIN) |
| `V3Rule` | ORM | `models.py` | `rule_id`, `logic_tree_json`, `requires_semantic_scan`, `compiled_sql`, `target_table` |
| `V3Violation` | ORM | `models.py` | `record_id`, `violation_data`, `confidence_score`, `verdict_reasoning` |
| `CompiledRule` | Pydantic | `schemas.py` | V1 agent output schema |
| `GlobalOntology` | Pydantic | `schemas.py` | `definitions: dict[str, str]` |
| `Condition` | Pydantic | `schemas.py` | AST leaf: `subject_column`, `operator`, `value`, `semantic_rubric` |
| `LogicNode` | Pydantic | `schemas.py` | AST interior: `logic_type` (AND/OR/UNLESS), `children` (recursive) |
| `SymbolicRuleDraft` | Pydantic | `schemas.py` | Extractor output with `logic_tree` as JSON string |
| `PaginatedViolationsResponse` | Pydantic | `schemas.py` | V3 violations: `items`, `total_count`, `limit`, `offset` |
| `CompilerDeps` | dataclass | `agents/compiler.py` | `db_schema_context: str` |
| `get_compiler_agent` | `@lru_cache` factory | `agents/compiler.py` | `Agent[CompilerDeps, list[CompiledRule]]` |
| `get_explainer_agent` | `@lru_cache` factory | `agents/explainer.py` | `Agent[None, str]` |
| `ExtractorDeps` | dataclass | `agents/extractor.py` | `db: AsyncSession`, `db_schema_context`, `global_ontology` |
| `get_extractor_agent` | `@lru_cache` factory | `agents/extractor.py` | `Agent[ExtractorDeps, list[SymbolicRuleDraft]]` with `@output_validator` |
| `LegalArgument` | Pydantic | `agents/courtroom.py` | `points: list[str]`, `evidence_citations: list[str]` |
| `Verdict` | Pydantic | `agents/courtroom.py` | `is_violation`, `confidence_score`, `reasoning` |
| `run_semantic_debate` | async func | `agents/courtroom.py` | Entry point: parallel Prosecutor+Defender, then Chief Justice |
| `compile_ast_to_sql` | func | `ast_compiler.py` | LogicNode → SQL WHERE clause (IS_VAGUE → `1=1`) |
| `ingest_policy` | async func | `services/ingestion.py` | V1: bytes → text → compile → save rules |
| `ingest_policy_v3` | async func | `services/ingestion.py` | V3: bytes → ontology → chunks → extract → validate → save |
| `_extract_global_ontology` | async func | `services/ingestion.py` | Lexicon agent, reads first 12K chars |
| `_introspect_db_schema` | async func | `services/ingestion.py` | Queries `information_schema.columns`, skips internal tables |
| `_chunk_policy_text` | func | `services/ingestion.py` | 4000 chars, 500 overlap |
| `run_deterministic_scan` | async func | `services/scanner.py` | V1: execute approved SQL, dedup, save violations |
| `run_v3_scan` | async func | `services/scanner.py` | V3: 3-path routing (deterministic / mixed / pure-vague) |
| `_scan_deterministic_v3` | async func | `services/scanner.py` | Path A: SQL only, confidence=1.0 |
| `_scan_semantic_v3` | async func | `services/scanner.py` | Paths B+C: SQL or BM25 candidates → courtroom |
| `_find_bm25_candidates` | async func | `services/scanner.py` | Postgres-native ts_rank + websearch_to_tsquery |
| `_collect_semantic_rubrics` | func | `services/scanner.py` | Walk AST, collect IS_VAGUE rubrics |

## PIPELINES

### V1 pipeline

```
Phase 1 — INGESTION (BackgroundTasks)
  POST /api/v1/policies/upload → parse text (.pdf or .md)
  → _introspect_db_schema() → CompilerAgent → list[CompiledRule]
  → Rule rows (status=pending_review)

Phase 2 — HUMAN REVIEW
  GET /api/v1/rules → human reviews SQL → PATCH /approve or /reject

Phase 3 — SCAN (APScheduler or manual POST /api/v1/scan, zero LLM)
  SELECT approved+deterministic rules → db.execute(compiled_sql) → save violations
  → ExplainerAgent generates explanations (capped at 25/scan)
```

### V3 pipeline

```
Phase 1 — NEURO-SYMBOLIC INGESTION (BackgroundTasks)
  POST /api/v3/policies/upload → parse text
  → Lexicon Agent → GlobalOntology (shared vocabulary)
  → _introspect_db_schema() → schema context
  → _chunk_policy_text() → overlapping chunks
  → For each chunk: Extractor Agent → list[SymbolicRuleDraft]
    → @output_validator: AST Compiler → SQL → EXPLAIN sandbox
    → On failure: ModelRetry with Postgres stack trace → Claude self-corrects
  → V3Rule rows (status=pending_review, logic_tree_json + compiled_sql)

Phase 2 — HUMAN REVIEW
  GET /api/v3/rules → human reviews logic tree + SQL → PATCH /approve or /reject

Phase 3 — THREE-PATH SCAN (manual POST /api/v3/scan)
  For each approved V3 rule:
    Path A (pure deterministic): Execute SQL → violations (confidence=1.0)
    Path B (mixed det+vague): SQL pre-filter (IS_VAGUE→1=1 superset) → courtroom per candidate
    Path C (pure vague): BM25 text search on company_records → courtroom per candidate

  Courtroom: Prosecutor + Defender (parallel) → Chief Justice → Verdict{is_violation, confidence_score}
```

## FRONTEND REQUEST FLOW (React)

```
Page load (App mount):
  Promise.all([GET /api/v3/rules, GET /api/v3/violations])

Upload flow:
  POST /api/v3/policies/upload → returns {id, status="processing"}
  Background task runs ingest_policy_v3() for SAME policy_id
  Frontend polls GET /api/v3/rules?policy_id={id} every 3s until rules exist

Review flow:
  PATCH /api/v3/rules/{id}/approve OR /reject
  Frontend updates local state for the changed rule

Scan flow:
  POST /api/v3/scan → returns {deterministic_violations, semantic_violations, total}
  Frontend then GET /api/v3/violations (paginated, 25 per page)

Violations polling:
  If any violation has null verdict_reasoning, poll violations every 5s
```

- React dev mode (`StrictMode`) causes duplicate initial GETs on page load; expected locally.
- Background ingestion updates the existing placeholder policy created by the upload route, not a second row. Rule `policy_id` matches upload response `id`.
- V3 violations are paginated: `{items, total_count, limit, offset}`. Frontend accepts both paginated and legacy array responses.

## CONVENTIONS

### PydanticAI (v1.0.5+)
- Constructor: `output_type=` (NEVER `result_type=`)
- Results: `result.output` (NEVER `result.data`)
- Validators: `@agent.output_validator` (NEVER `@result_validator`)
- Agent deps: plain `@dataclass`, not Pydantic BaseModel
- Agent factories: `@lru_cache(maxsize=1)`, agent validates API key at construction
- Dynamic prompts: `@agent.system_prompt` with `RunContext[DepsType]`
- Self-healing: `@output_validator` + `ModelRetry` with Postgres stack trace (extractor.py)
- Streaming: `agent.run_stream()` + `await response.get_output()` (courtroom.py)
- Thinking configs:
  - Compiler: `{"type": "adaptive"}`, `anthropic_effort="high"`
  - Extractor: `{"type": "enabled", "budget_tokens": 10000}`, `max_tokens=20000`
  - Courtroom Prosecutor/Defender: `{"type": "enabled", "budget_tokens": 8000}`, `max_tokens=16000`
  - Courtroom Chief Justice: `{"type": "enabled", "budget_tokens": 16000}`, `max_tokens=32000`
  - Explainer: `{"type": "adaptive"}`, `anthropic_effort="medium"`
  - Lexicon: `{"type": "enabled", "budget_tokens": 4000}`, `max_tokens=8000`

### SQLAlchemy 2.x async
- `DeclarativeBase` + `AsyncAttrs` mixin
- `Mapped[T]` + `mapped_column()` for all columns
- `async_sessionmaker(engine, expire_on_commit=False)`
- Routes: `Depends(get_db)` | Background tasks: `async_session_factory()` directly
- TypeDecorators for SQLite test compat: `JSONVariant`, `TSVectorVariant`
- GIN index on `company_records.ts_vector` uses `postgresql_using="gin"`, SQLAlchemy silently ignores on SQLite

### APScheduler 3.x (NOT v4)
- `AsyncIOScheduler(timezone="UTC")`
- `scheduler.add_job(fn, IntervalTrigger(minutes=N))`
- Lifecycle in FastAPI lifespan context manager

### FastAPI
- V1 routes: `/api/v1/` prefix (`app/routes/`)
- V3 routes: `/api/v3/` prefix (`app/api/`)
- ORM responses: `model_config = {"from_attributes": True}`
- Policy ingestion: `BackgroundTasks.add_task()`
- Lifespan context manager, not `@app.on_event("startup")`

### AST compiler
- Pure Python, no LLM, deterministic
- AND/OR → SQL AND/OR
- UNLESS → `AND NOT` (defeasible logic)
- IS_VAGUE → `1=1` (deliberate superset for courtroom)
- CONTAINS → `ILIKE '%value%'`
- IS_NULL / IS_NOT_NULL → SQL IS NULL / IS NOT NULL
- Bool check before numeric check (Python `bool` subclasses `int`)

## ANTI-PATTERNS

### Forbidden libraries
LangChain, LangGraph, Instructor, Celery, Redis, Docling, Alembic, pgvector, numpy

### Forbidden patterns
| Don't | Do instead |
|-------|-----------|
| `Agent(..., result_type=X)` | `Agent(..., output_type=X)` |
| `result.data` | `result.output` |
| `@result_validator` | `@agent.output_validator` |
| Module-level `Agent(...)` | `@lru_cache` factory function |
| `Any` type hints | Explicit types everywhere |
| Bare `db.execute(text(...))` in scanner | Wrap in try/except |
| `Depends(get_db)` in background tasks | `async_session_factory()` directly |
| Nested DDD directories | Flat folder structure |
| `@app.on_event("startup")` | Lifespan context manager |
| Alembic migrations | `Base.metadata.create_all()` in lifespan |
| pgvector / numpy / embeddings | BM25 (ts_rank) for text search |
| `CREATE EXTENSION vector` | Not needed, no pgvector |
| Single-agent "is this a violation?" | Adversarial courtroom (Prosecutor + Defender + Chief Justice) |

## COMMANDS

```bash
uv run uvicorn app.main:app --reload   # Dev server (docs: http://localhost:8000/docs)
uv sync                                 # Install deps
uv add <package>                        # Add dependency
uv run pytest                            # 78 tests, ~0.7s, no API key needed
uv run pytest -v                         # Verbose
uv run ruff check app/ tests/ --ignore E402
uv run ruff format app/ tests/
```

### Demo data
```bash
uv run python scripts/extract_aml_demo.py --profile small --budget-gb 1.5
uv run python scripts/load_aml_demo_to_db.py --max-trans-rows 50000
uv run python scripts/reset_db.py --yes
```

## NOTES

- **Tests**: 78 tests across 10 files. pytest + pytest-asyncio, in-memory SQLite via aiosqlite. No Postgres, no API key needed. Config in `pyproject.toml` only (`asyncio_mode = "auto"`, `pythonpath = "."`).
- **Docker**: Multi-stage `Dockerfile` (uv build stage, python:3.13-slim runtime, non-root user) + `docker-compose.yml` with PostgreSQL service. No pgvector extension needed.
- **Ingestion formats**: `.pdf` uses `pymupdf4llm.to_markdown()` (`str | list[dict]` handled), `.md` uses UTF-8 decode.
- **Inline imports** in `routes/policies.py` and `api/router.py` avoid circular deps. Intentional.
- **Explanation cap**: `EXPLANATION_MODEL_LIMIT_PER_SCAN` (default 25) limits V1 model-generated explanations per scan; overflow rows get deterministic fallback text.
- **Semantic candidate cap**: `semantic_candidate_limit_per_rule` limits how many records enter the courtroom per V3 rule.
- **V3 violations pagination**: `GET /api/v3/violations` returns `{items, total_count, limit, offset}`. Frontend accepts both paginated and legacy array shapes.
- **Ruff**: cache exists (`.ruff_cache/`) but no config file.
- **Agent collaboration diagrams**: `docs/AGENT_COLLABORATION.md` has Mermaid diagrams of all agent interactions, data contracts, and scan path routing.
