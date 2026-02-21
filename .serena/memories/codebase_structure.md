# TraceRule — Codebase structure (supplements AGENTS.md)

Only info NOT already in AGENTS.md lives here.

## SQLite/Postgres compatibility

`JSONVariant` (models.py) is a custom `TypeDecorator` that maps to JSONB on Postgres and plain JSON on SQLite. This is how tests run against in-memory SQLite while production uses Postgres JSONB columns.

## Route handlers by file

| Method | Path | Handler | File |
|--------|------|---------|------|
| POST | /policies/upload | `upload_policy` | routes/policies.py |
| GET | /rules | `list_rules` | routes/rules.py |
| GET | /rules/{rule_id} | `get_rule` | routes/rules.py |
| PATCH | /rules/{rule_id}/status | `update_rule_status` | routes/rules.py |
| PATCH | /rules/{rule_id}/approve | `approve_rule` | routes/rules.py |
| PATCH | /rules/{rule_id}/reject | `reject_rule` | routes/rules.py |
| GET | /violations | `list_violations` | routes/violations.py |
| GET | /violations/{violation_id} | `get_violation` | routes/violations.py |
| POST | /scan | `trigger_scan` | routes/violations.py |

## Test setup (tests/conftest.py)

- In-memory SQLite via `aiosqlite` + `StaticPool`
- `app.dependency_overrides[get_db]` swaps the DB session
- `autouse=True` fixture runs `create_all` / `drop_all` per test
- `httpx.AsyncClient` with `ASGITransport` for API testing
- Config in `pyproject.toml` only (pytest.ini removed)
- 23 tests across 4 files: `test_rules.py` (10), `test_violations.py` (8), `test_scanner.py` (3), `test_policies.py` (3)

## Docker (multi-stage)

- Build stage: `ghcr.io/astral-sh/uv:python3.13-bookworm-slim` with cache mounts
- Runtime stage: `python:3.13-slim-bookworm`, non-root user, no uv in final image
- CMD runs `uvicorn` directly (not via `uv run`)


## Recent additions (2026-02-22)

### Scripts directory
- `scripts/reset_db.py` — repeatable DB reset utility
  - default: truncates `policies`, `rules`, `violations`
  - `--all-public`: truncates all public schema tables
- `scripts/extract_aml_demo.py` — capped extraction from IBM AML zip without full unzip
  - profiles: `tiny`, `small`
  - budget control: `--budget-gb`
  - writes `data/aml_demo/manifest.json`
- `scripts/load_aml_demo_to_db.py` — loader for extracted AML CSVs into Postgres
  - creates `transactions` and `accounts` tables if missing
  - batched inserts + unique `(source_file, source_row_number)`
  - supports `--max-trans-rows`, `--max-account-rows`, `--no-truncate`

### Frontend flow improvements
- `frontend/src/components/RequestTimeline.tsx` — separate live timeline panel for request lifecycle
  - includes optional Technical Mode to show request/response endpoint lines
- `frontend/src/components/ViolationsPanel.tsx` + `frontend/src/api.ts`
  - violations filtering now uses backend query params (`rule_id`, `status`)
- `frontend/src/App.tsx`
  - unified refresh path, manual refresh, last-updated indicator
  - upload polling timeout guard
  - timeline events for upload/compile/review/scan/explanation lifecycle
