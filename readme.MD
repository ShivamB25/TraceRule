# TraceRule

Neuro-symbolic compliance compiler. Policy PDFs become deontic logic ASTs, then auto-healed SQL, then adversarial multi-agent courtroom verdicts. Deterministic scanning costs zero tokens.

Two coexisting pipelines:

- **V1**: Policy PDF → Claude compiles to raw SQL → human approves → scheduler executes SQL → violations logged. Zero LLM during scan.
- **V3**: Policy PDF → global ontology extraction → Claude compiles to deontic logic ASTs → pure-Python AST→SQL compiler → SQL auto-healed via EXPLAIN → human approves → scanner routes to deterministic SQL, SQL+courtroom, or BM25+courtroom paths → violations with confidence scores.

## For judges

- Architecture + runtime flow: `docs/ARCHITECTURE_AND_CODE_FLOW.md`
- Agent interaction diagrams (Mermaid): `docs/AGENT_COLLABORATION.md`
- AML demo runbook: `docs/RUN_DEMO_WITH_AML.md`
- Demo policy content (export to PDF): `docs/AML_POLICY_DEMO_CONTENT.md`

## Model strategy

Primary model: **Claude Sonnet 4.6** (`claude-sonnet-4-6`) with configurable thinking budgets. Seven agents total. No agent calls another directly; the service layer passes typed Pydantic schemas between them.

| Agent | Thinking | When it runs |
|-------|----------|-------------|
| Lexicon | enabled, 4K budget | Once per V3 ingestion (first 12K chars) |
| Compiler | adaptive, high effort | Once per V1 ingestion |
| Extractor | enabled, 10K budget | Per chunk during V3 ingestion |
| Explainer | adaptive, medium effort | Post-V1-scan, capped at 25 |
| Prosecutor | enabled, 8K budget | Per candidate in V3 semantic scan |
| Defender | enabled, 8K budget | Per candidate, parallel with Prosecutor |
| Chief Justice | enabled, 16K budget | Per candidate, after both arguments |

Deterministic scan paths (V1 scans and V3 Path A) cost zero tokens. The courtroom only fires for rules containing subjective (`IS_VAGUE`) conditions.

## How It Works

### V1 pipeline

```
Policy File ──→ Claude compiles to SQL ──→ Human reviews ──→ Scheduler scans DB
                  (one-time AI)            (approve/reject)    (zero AI, ~2ms/rule)
```

1. **Upload** a compliance policy file (`.pdf` or `.md`) → Claude Sonnet 4.6 reads the policy text and your database schema, then compiles each enforceable clause into a PostgreSQL SELECT query that returns violating records
2. **Review** each generated SQL rule in the dashboard → approve or reject. Nothing runs without human sign-off
3. **Scan** runs every 5 minutes via APScheduler → executes approved queries against your database, flags violations, generates plain-English explanations

### V3 pipeline

```
Policy File → Lexicon → Ontology → Chunker → Extractor → AST → EXPLAIN loop → Human review → 3-path scan
```

1. **Upload** a policy file → Lexicon Agent reads the first 12K chars and produces a `GlobalOntology` (shared vocabulary of domain terms). The database schema is introspected in parallel.
2. **Chunk** the policy text into overlapping segments (4000 chars, 500 overlap) so each fits Claude's working context.
3. **Extract** deontic logic ASTs from each chunk. The Extractor Agent produces `SymbolicRuleDraft` objects. An `@output_validator` compiles each AST to SQL via the pure-Python AST compiler, then runs `EXPLAIN` in a sandboxed nested transaction. If Postgres rejects the SQL, `ModelRetry` sends the exact error back to Claude ("column 'emplyee_age' does not exist"). Up to 4 retries. SQL that passes EXPLAIN is guaranteed executable at scan time.
4. **Review** logic trees and compiled SQL in the dashboard. Approve or reject each rule.
5. **Scan** routes each approved rule to one of three paths:
   - **Path A** (pure deterministic): Execute compiled SQL directly. `confidence = 1.0`.
   - **Path B** (mixed deterministic + vague): SQL pre-filter runs with `IS_VAGUE` conditions compiled to `1=1` (deliberate superset). Each candidate row enters the courtroom.
   - **Path C** (pure vague): BM25 text search (`ts_rank` + `websearch_to_tsquery`) on `company_records`. Each candidate enters the courtroom.
6. **Courtroom**: Prosecutor and Defender run in parallel via `asyncio.gather`. Both produce `LegalArgument{points, evidence_citations}`. The Chief Justice receives both arguments plus the original evidence, then renders `Verdict{is_violation, confidence_score, reasoning}`.

## Prerequisites

| Requirement | Version | Check |
|---|---|---|
| Python | >= 3.13 | `python --version` |
| PostgreSQL | any recent | `pg_isready` |
| uv | any recent | `uv --version` |
| Node.js | >= 18 | `node --version` (frontend only) |
| Anthropic API key | — | [console.anthropic.com](https://console.anthropic.com/) |

Or skip all of the above and use [Docker Compose](#docker-compose).

## Quick Start (Local)

### 1. Create the database

```bash
createdb tracerule
```

If Postgres isn't running yet:

```bash
# macOS (Homebrew)
brew services start postgresql@16

# Linux
sudo systemctl start postgresql
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set your Anthropic API key:

```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/tracerule
ANTHROPIC_API_KEY=sk-ant-...
SCAN_INTERVAL_MINUTES=5
```

If your Postgres uses a different user/password/port, update `DATABASE_URL` accordingly.

### 3. Install dependencies and start the API

```bash
uv sync
uv run uvicorn app.main:app --reload
```

The API starts at [http://localhost:8000](http://localhost:8000). Tables are created automatically on startup via `Base.metadata.create_all()`.

Swagger docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### 4. Start the frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

The frontend starts at [http://localhost:3000](http://localhost:3000). It proxies all `/api` requests to the backend at `localhost:8000` via Vite's dev server.

### 5. Use it

1. Open [http://localhost:3000](http://localhost:3000)
2. Drop a compliance policy file (`.pdf` or `.md`) onto the upload area
3. Wait for compilation (Claude processes the policy text in the background, usually 10-30 seconds)
4. Review the generated rules: logic trees, compiled SQL, source quotes. Approve or reject each one
5. Click **Trigger Scan** or wait for the scheduler (every 5 minutes)
6. View detected violations. Deterministic violations show record data; semantic violations include courtroom verdict reasoning with confidence scores

**Important:** The compiler introspects your database schema and passes it to Claude so the generated SQL references real tables and columns. If you upload a policy file against an empty database (no tables besides the internal ones), the compiler will have no schema context. Load your business data first, then upload the policy.

## Docker Compose

Runs both PostgreSQL and the API in containers. No local Postgres or Python needed.

```bash
cp .env.example .env
```

Set your API key (either method works):

```bash
# Option A: Export in shell (not stored in .env)
export ANTHROPIC_API_KEY=sk-ant-...
docker compose up --build

# Option B: Put it directly in .env
# ANTHROPIC_API_KEY=sk-ant-...
docker compose up --build
```

- API: [http://localhost:8000/docs](http://localhost:8000/docs)
- Postgres is exposed on port `5432` (user: `postgres`, password: `postgres`, db: `tracerule`)
- Data persists in a Docker volume (`pgdata`). Run `docker compose down -v` to wipe it

The compose file starts Postgres first, waits for its health check to pass, then starts the API container.

To run the frontend against the Dockerized backend, start it locally in a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

The Vite proxy at `localhost:3000` forwards `/api` requests to the Docker container on `localhost:8000`.

## Running Tests

Tests use an in-memory SQLite database via aiosqlite. No Postgres required. No API key required.

```bash
uv sync --dev
uv run pytest
```

```bash
# Verbose output
uv run pytest -v

# Single test file
uv run pytest tests/test_ast_compiler.py

# Single test
uv run pytest tests/test_rules.py::test_approve_rule
```

78 tests across 10 files (~0.7s):

| File | Tests | Covers |
|------|-------|--------|
| `test_ast_compiler.py` | 23 | All AST operators, logic types, edge cases |
| `test_v3_rules.py` | 11 | V3 rule CRUD, filters, approve/reject |
| `test_rules.py` | 10 | V1 rule CRUD, filters, approve/reject |
| `test_v3_scanner.py` | 7 | V3 scanner, bad SQL, dedup, endpoint |
| `test_violations.py` | 7 | V1 violation CRUD, filters |
| `test_v3_violations.py` | 6 | V3 violation CRUD, filters |
| `test_policies.py` | 5 | V1 upload, missing file, health |
| `test_v3_policies.py` | 4 | V3 upload PDF/MD, 422, 400 |
| `test_scanner.py` | 4 | V1 scanner, bad SQL, explanation limit |
| `conftest.py` | — | DB fixtures, app overrides |

## Linting

No config file. Run ad hoc:

```bash
uv run ruff check app/ tests/
uv run ruff format --check app/ tests/

# Auto-fix
uv run ruff check --fix app/ tests/
uv run ruff format app/ tests/
```

## Project Structure

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

frontend/                # React 19 + Vite + Tailwind v4
├── src/
│   ├── App.tsx              # Root component: all state, polling, handlers
│   ├── api.ts               # Typed fetch wrappers for /api/v3 endpoints
│   ├── types.ts             # TypeScript interfaces matching backend schemas
│   ├── index.css            # Tailwind import + custom fonts
│   └── components/
│       ├── ErrorBoundary.tsx     # Render error boundary with retry
│       ├── Header.tsx           # Top nav, scan trigger, status
│       ├── UploadPanel.tsx      # PDF drag-and-drop upload
│       ├── PipelineStrip.tsx    # 3-phase pipeline visualization
│       ├── StatsBar.tsx         # Rule/violation counters
│       ├── RequestTimeline.tsx  # Live API request log
│       ├── ReviewPanel.tsx      # Tabbed rule review
│       ├── RuleCard.tsx         # Single rule with approve/reject
│       ├── ViolationsPanel.tsx  # Violation list
│       ├── ViolationCard.tsx    # Single violation with verdict reasoning/confidence
│       ├── SeverityBadge.tsx    # CRITICAL/HIGH/MEDIUM/LOW badge
│       └── SqlBlock.tsx         # SQL code display
└── vite.config.ts           # Dev proxy: /api → localhost:8000

tests/                   # 78 tests, pytest + pytest-asyncio, in-memory SQLite via aiosqlite
docs/                    # Architecture docs, demo runbooks, agent collaboration diagrams
scripts/                 # Demo data extraction, loading, DB reset
```

## API Reference

### V1 endpoints (`/api/v1/`)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Returns `{"status": "ok"}` |
| `POST` | `/api/v1/policies/upload` | Upload a policy file (`.pdf` or `.md`, multipart form field: `file`). Returns `{id, filename, status: "processing"}`. Compilation runs in background. |
| `GET` | `/api/v1/rules` | List rules. Filters: `?status=pending_review`, `?policy_id=1` |
| `GET` | `/api/v1/rules/{id}` | Get a single rule |
| `PATCH` | `/api/v1/rules/{id}/approve` | Approve a rule for scanning |
| `PATCH` | `/api/v1/rules/{id}/reject` | Reject a rule |
| `PATCH` | `/api/v1/rules/{id}/status` | Generic status update. Body: `{"status": "approved"}` or `{"status": "rejected"}` |
| `GET` | `/api/v1/violations` | List violations. Filters: `?rule_id=1`, `?status=open` |
| `GET` | `/api/v1/violations/{id}` | Get a single violation |
| `POST` | `/api/v1/scan` | Trigger manual scan. Returns `{violations_found: n}` |

### V3 endpoints (`/api/v3/`)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v3/policies/upload` | Upload a policy file. Returns `{id, filename, status: "processing"}`. V3 ingestion (ontology + AST extraction + EXPLAIN validation) runs in background. |
| `GET` | `/api/v3/rules` | List V3 rules. Filters: `?status=pending_review`, `?policy_id=1` |
| `GET` | `/api/v3/rules/{id}` | Get a single V3 rule (includes `logic_tree_json`, `compiled_sql`, `requires_semantic_scan`) |
| `PATCH` | `/api/v3/rules/{id}/approve` | Approve a V3 rule |
| `PATCH` | `/api/v3/rules/{id}/reject` | Reject a V3 rule |
| `GET` | `/api/v3/violations` | List V3 violations (paginated). Filters: `?v3_rule_id=1`, `?status=open`, `?limit=50`, `?offset=0`. Returns `{items, total_count, limit, offset}` |
| `GET` | `/api/v3/violations/{id}` | Get a single V3 violation (includes `confidence_score`, `verdict_reasoning`) |
| `POST` | `/api/v3/scan` | Trigger V3 scan. Returns `{deterministic_violations, semantic_violations, total}` |

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | No | `postgresql+asyncpg://postgres:postgres@localhost:5432/tracerule` | PostgreSQL connection string (must use `asyncpg` driver) |
| `ANTHROPIC_API_KEY` | Yes | — | Anthropic API key for Claude. Required for policy compilation and violation explanations. Not needed for tests. |
| `SCAN_INTERVAL_MINUTES` | No | `5` | How often APScheduler runs the compliance scan |
| `EXPLANATION_MODEL_LIMIT_PER_SCAN` | No | `25` | Max number of V1 violations per scan that use model-generated explanations. Overflow violations get deterministic fallback text. |
| `SEMANTIC_CANDIDATE_LIMIT_PER_RULE` | No | `200` | Max records entering the courtroom per V3 rule per scan. Caps model usage for semantic evaluation. |
| `LOGFIRE_TOKEN` | No | `""` | Pydantic Logfire observability token (optional) |

## Stack

| Layer | Choice | Why |
|---|---|---|
| API | FastAPI | Async, auto-generated OpenAPI docs, dependency injection |
| LLM framework | PydanticAI | Structured output via `output_type=`, built-in retries, no hidden abstractions |
| LLM | Claude Sonnet 4.6 | Configurable thinking budgets per agent (4K to 16K tokens) |
| ORM | SQLAlchemy 2.x async | `Mapped[]` typed columns, async sessions via asyncpg |
| Database | PostgreSQL | Compiled SQL targets Postgres. JSONB for violation data. GIN index for BM25 search. |
| Scheduler | APScheduler 3.x | In-process async scheduler, no external broker needed |
| AST compiler | Pure Python | Recursive LogicNode→SQL. Supports AND, OR, UNLESS (defeasible), CONTAINS, IS_NULL, IS_NOT_NULL, IS_VAGUE (→ `1=1` for courtroom superset) |
| Text search | Postgres BM25 | `ts_rank` + `websearch_to_tsquery` on `company_records`. No embeddings, no pgvector. |
| Adversarial evaluation | PydanticAI courtroom | Prosecutor + Defender (parallel) → Chief Justice. Confidence-scored verdicts. |
| PDF parsing | pymupdf4llm | CPU-only, < 200ms per document, no GPU or PyTorch |
| Frontend | React 19 + Vite + Tailwind v4 | TypeScript, dark theme, zero extra dependencies |
| Testing | pytest + pytest-asyncio + aiosqlite | In-memory SQLite, no external services, 78 tests in ~0.7s |
| Packaging | uv | Fast dependency resolution and lockfile |
| Container | Docker multi-stage | uv build stage, python:3.13-slim runtime, non-root user |

## Troubleshooting

### `connection refused` on startup

Postgres isn't running or the connection string is wrong:

```bash
pg_isready -h localhost -p 5432
```

If using a non-default setup, update `DATABASE_URL` in `.env`.

### `ANTHROPIC_API_KEY` errors

The compiler agent validates the API key at construction time. If the key is missing or invalid, the first policy upload will fail. The API server itself starts fine without a key; it's only needed when uploading a policy file.

### Upload succeeds but no rules appear

Check the API server terminal for errors. Common causes:

- **No business tables in the database.** The compiler queries `information_schema.columns` and skips internal tables (`policies`, `rules`, `violations`, `v3_rules`, `v3_violations`, `company_records`). If no other tables exist, Claude gets no schema context.
- **API key quota exceeded.** Compilation uses adaptive thinking at `high` effort which consumes more tokens than a standard call. V3 ingestion with the Extractor's 10K thinking budget uses even more.
- **Scanned-image PDF.** pymupdf4llm extracts text layers. PDFs that are just scanned images (no embedded text) will produce empty markdown.

### Tests fail with `ModuleNotFoundError`

Run from the project root, not from `app/` or `tests/`:

```bash
# Correct
uv run pytest

# Wrong
cd tests && uv run pytest
```

The `pythonpath = "."` setting in `pyproject.toml` handles module resolution.

### Frontend shows "Failed to fetch"

The Vite dev server proxies `/api` to `localhost:8000`. Both servers must be running:

```bash
# Terminal 1: Backend
uv run uvicorn app.main:app --reload

# Terminal 2: Frontend
cd frontend && npm run dev
```

### Docker: API key is empty

The compose file reads from both the shell and `.env`. Verify:

```bash
echo $ANTHROPIC_API_KEY
grep ANTHROPIC_API_KEY .env
```

### V1 scanner finds 0 violations

The scanner only executes rules where `status='approved'` AND `is_deterministic=true`. Check:

1. At least one rule is approved and deterministic
2. The rule's `compiled_sql` references tables and columns that exist
3. The data actually contains records that match the violation condition

Test a rule's SQL manually:

```bash
psql tracerule -c "SELECT id, age FROM employees WHERE age < 18;"
```

### V3 scanner finds 0 violations

The V3 scanner requires rules with `status='approved'`. For rules with `requires_semantic_scan=True`, the courtroom evaluates candidates. If no `company_records` rows exist (BM25 path) or if the compiled SQL references missing tables, the scanner skips silently. Check:

1. At least one V3 rule is approved
2. The rule's `target_table` exists in your database
3. For semantic rules: `company_records` has rows with matching `table_name` and populated `search_text` / `ts_vector`

### Very large scan result sets create too many explanation calls

By default, TraceRule limits model-based explanations to 25 violations per V1 scan run.

- First N rows (`EXPLANATION_MODEL_LIMIT_PER_SCAN`) get model-generated explanations
- Remaining rows get deterministic fallback text

For V3, the `SEMANTIC_CANDIDATE_LIMIT_PER_RULE` setting (default 200) caps how many records enter the courtroom per rule.
