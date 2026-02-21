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
