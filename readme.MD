# TraceRule

Deterministic AI compliance compiler. Upload a policy PDF, get PostgreSQL queries that find violations automatically.

The LLM runs once during upload. Every scan after that is pure SQL — deterministic, auditable, zero tokens.

## How It Works

```
PDF Policy ──→ Claude compiles to SQL ──→ Human reviews ──→ Scheduler scans DB
                  (one-time AI)            (approve/reject)    (zero AI, ~2ms/rule)
```

1. **Upload** a compliance PDF → Claude Sonnet 4.6 reads the policy text and your database schema, then compiles each enforceable clause into a PostgreSQL SELECT query that returns violating records
2. **Review** each generated SQL rule in the dashboard → approve or reject. Nothing runs without human sign-off
3. **Scan** runs every 5 minutes via APScheduler → executes approved queries against your database, flags violations, generates plain-English explanations

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
2. Drop a compliance policy PDF onto the upload area
3. Wait for compilation (Claude processes the PDF in the background, usually 10-30 seconds)
4. Review the generated SQL rules — approve or reject each one
5. Click **Trigger Scan** or wait for the scheduler (every 5 minutes)
6. View detected violations with AI-generated explanations

**Important:** The compiler introspects your database schema and passes it to Claude so the generated SQL references real tables and columns. If you upload a PDF against an empty database (no tables besides the internal ones), the compiler will have no schema context. Load your business data first, then upload the policy.

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
uv run pytest tests/test_rules.py

# Single test
uv run pytest tests/test_rules.py::test_approve_rule
```

23 tests across 4 files:

| File | Covers |
|---|---|
| `tests/test_rules.py` | Rule CRUD, filtering by status/policy_id, approve, reject, invalid status |
| `tests/test_violations.py` | Violation CRUD, filtering by rule_id and status |
| `tests/test_scanner.py` | Scanner with no rules, bad SQL resilience, empty result sets |
| `tests/test_policies.py` | Upload endpoint, missing file (422), health check |

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
├── main.py                  # FastAPI app, lifespan (DB init + scheduler), CORS, health
├── config.py                # Settings from .env (DATABASE_URL, API key, scan interval)
├── database.py              # Async engine + session factory + get_db dependency
├── models.py                # ORM: Policy, Rule, Violation + JSONVariant TypeDecorator
├── schemas.py               # Pydantic: CompiledRule (agent output), API request/response
├── agents/
│   ├── compiler.py          # PDF text → list[CompiledRule] via Claude (adaptive thinking, high effort)
│   └── explainer.py         # Violation → 2-sentence explanation via Claude (medium effort)
├── services/
│   ├── ingestion.py         # PDF upload → markdown → schema introspection → compile → save
│   └── scanner.py           # Execute approved SQL, dedup by rule_id+record_pk, save violations
└── routes/
    ├── policies.py          # POST /policies/upload (BackgroundTasks for async compilation)
    ├── rules.py             # GET/PATCH rules (list, get, approve, reject, status update)
    └── violations.py        # GET violations, POST /scan

frontend/                    # React 19 + Vite + Tailwind v4
├── src/
│   ├── App.tsx              # Main layout, state management, polling logic
│   ├── api.ts               # Typed fetch wrappers for all endpoints
│   ├── types.ts             # TypeScript interfaces matching backend schemas
│   └── components/
│       ├── Header.tsx       # Logo, status pill, scan trigger button
│       ├── UploadPanel.tsx  # Drag-and-drop PDF upload with progress states
│       ├── ReviewPanel.tsx  # Tabbed rule list (pending / approved / rejected)
│       ├── RuleCard.tsx     # Single rule card with source quote, SQL, approve/reject
│       ├── ViolationsPanel.tsx  # Violation list with count badge
│       ├── ViolationCard.tsx    # Single violation with JSON data and AI explanation
│       ├── SeverityBadge.tsx    # CRITICAL / HIGH / MEDIUM / LOW color pill
│       └── SqlBlock.tsx     # Monospace SQL code display
└── vite.config.ts           # Dev proxy: /api → localhost:8000

tests/                       # pytest + pytest-asyncio, in-memory SQLite via aiosqlite
docs/                        # Architecture research, judges document
```

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Returns `{"status": "ok"}` |
| `POST` | `/api/v1/policies/upload` | Upload a PDF (multipart form, field: `file`). Returns `{id, filename, status: "processing"}`. Compilation runs in background. |
| `GET` | `/api/v1/rules` | List rules. Filters: `?status=pending_review`, `?policy_id=1` |
| `GET` | `/api/v1/rules/{id}` | Get a single rule |
| `PATCH` | `/api/v1/rules/{id}/approve` | Approve a rule for scanning |
| `PATCH` | `/api/v1/rules/{id}/reject` | Reject a rule |
| `PATCH` | `/api/v1/rules/{id}/status` | Generic status update. Body: `{"status": "approved"}` or `{"status": "rejected"}` |
| `GET` | `/api/v1/violations` | List violations. Filters: `?rule_id=1`, `?status=open` |
| `GET` | `/api/v1/violations/{id}` | Get a single violation |
| `POST` | `/api/v1/scan` | Trigger manual scan. Returns `{violations_found: n}` |

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | No | `postgresql+asyncpg://postgres:postgres@localhost:5432/tracerule` | PostgreSQL connection string (must use `asyncpg` driver) |
| `ANTHROPIC_API_KEY` | Yes | — | Anthropic API key for Claude. Required for PDF compilation and violation explanations. Not needed for tests. |
| `SCAN_INTERVAL_MINUTES` | No | `5` | How often APScheduler runs the compliance scan |

## Stack

| Layer | Choice | Why |
|---|---|---|
| API | FastAPI | Async, auto-generated OpenAPI docs, dependency injection |
| LLM framework | PydanticAI | Structured output via `output_type=`, built-in retries, no hidden abstractions |
| LLM | Claude Sonnet 4.6 | Adaptive thinking with configurable effort (`high` for compilation, `medium` for explanations) |
| ORM | SQLAlchemy 2.x async | `Mapped[]` typed columns, async sessions via asyncpg |
| Database | PostgreSQL | Compiled SQL targets Postgres. JSONB for violation data |
| Scheduler | APScheduler 3.x | In-process async scheduler, no external broker needed |
| PDF parsing | pymupdf4llm | CPU-only, < 200ms per document, no GPU or PyTorch |
| Frontend | React 19 + Vite + Tailwind v4 | TypeScript, dark theme, zero extra dependencies |
| Testing | pytest + pytest-asyncio + aiosqlite | In-memory SQLite, no external services |
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

The compiler agent validates the API key at construction time. If the key is missing or invalid, the first PDF upload will fail. The API server itself starts fine without a key — it's only needed when uploading a PDF.

### Upload succeeds but no rules appear

Check the API server terminal for errors. Common causes:

- **No business tables in the database.** The compiler queries `information_schema.columns` and skips internal tables (`policies`, `rules`, `violations`). If no other tables exist, Claude gets no schema context.
- **API key quota exceeded.** Compilation uses adaptive thinking at `high` effort which consumes more tokens than a standard call.
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
# Terminal 1 — Backend
uv run uvicorn app.main:app --reload

# Terminal 2 — Frontend
cd frontend && npm run dev
```

### Docker: API key is empty

The compose file reads from both the shell and `.env`. Verify:

```bash
echo $ANTHROPIC_API_KEY
grep ANTHROPIC_API_KEY .env
```

### Scanner finds 0 violations

The scanner only executes rules where `status='approved'` AND `is_deterministic=true`. Check:

1. At least one rule is approved and deterministic
2. The rule's `compiled_sql` references tables and columns that exist
3. The data actually contains records that match the violation condition

Test a rule's SQL manually:

```bash
psql tracerule -c "SELECT id, age FROM employees WHERE age < 18;"
```
