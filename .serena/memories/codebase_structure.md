# TraceRule — Codebase Structure

## Directory Layout

```
app/
├── main.py              # FastAPI app + lifespan (DB init + scheduler), CORS, health, router registration
├── config.py            # pydantic-settings BaseSettings (.env)
├── database.py          # async engine, session factory, get_db()
├── models.py            # ORM: Policy, Rule, Violation, CompanyRecord, V3Rule, V3Violation + TypeDecorators
├── schemas.py           # Pydantic: V1 CompiledRule + V3 GlobalOntology, Condition, LogicNode, SymbolicRule, responses
├── ast_compiler.py      # Pure-Python recursive AST→SQL compiler (no LLM)
├── agents/
│   ├── compiler.py      # V1: policy text → list[CompiledRule] via Claude
│   ├── explainer.py     # V1: violation → 2-sentence explanation via Claude
│   ├── extractor.py     # V3: policy text → list[SymbolicRule] (deontic AST) with @output_validator reflexion
│   └── courtroom.py     # V3: Prosecutor + Defender + Chief Justice adversarial debate
├── services/
│   ├── ingestion.py     # V1 ingest_policy() + V3 ingest_policy_v3() with global ontology + chunking
│   └── scanner.py       # V1 run_deterministic_scan() + V3 run_v3_scan() with SQL pre-filter + courtroom
├── routes/              # V1 endpoints (/api/v1/)
│   ├── policies.py      # POST /policies/upload
│   ├── rules.py         # GET/PATCH rules
│   └── violations.py    # GET violations, POST /scan
└── api/                 # V3 endpoints (/api/v3/)
    ├── __init__.py
    └── router.py        # POST upload, GET/PATCH rules, GET violations, POST scan

tests/
├── conftest.py          # In-memory SQLite setup, fixture overrides
├── test_ast_compiler.py # 23 tests: all operators, logic types, edge cases
├── test_policies.py     # 5 tests: V1 upload, missing file, health
├── test_rules.py        # 10 tests: V1 rule CRUD, filters, approve/reject
├── test_scanner.py      # 4 tests: V1 scanner, bad SQL, explanation limit
├── test_violations.py   # 7 tests: V1 violation CRUD, filters
├── test_v3_policies.py  # 4 tests: V3 upload PDF/MD, 422, 400
├── test_v3_rules.py     # 11 tests: V3 rule CRUD, filters, approve/reject
├── test_v3_scanner.py   # 7 tests: V3 scanner, bad SQL, dedup, endpoint
└── test_v3_violations.py # 6 tests: V3 violation CRUD, filters (total: 78)
```

## V1 API Endpoints (prefix: /api/v1/)

| Method | Path | Handler |
|--------|------|---------|
| POST | /policies/upload | upload_policy |
| GET | /rules | list_rules |
| GET | /rules/{id} | get_rule |
| PATCH | /rules/{id}/approve | approve_rule |
| PATCH | /rules/{id}/reject | reject_rule |
| PATCH | /rules/{id}/status | update_rule_status |
| GET | /violations | list_violations |
| GET | /violations/{id} | get_violation |
| POST | /scan | trigger_scan |

## V3 API Endpoints (prefix: /api/v3/)

| Method | Path | Handler |
|--------|------|---------|
| POST | /policies/upload | upload_policy_v3 |
| GET | /rules | list_v3_rules |
| GET | /rules/{id} | get_v3_rule |
| PATCH | /rules/{id}/approve | approve_v3_rule |
| PATCH | /rules/{id}/reject | reject_v3_rule |
| GET | /violations | list_v3_violations |
| GET | /violations/{id} | get_v3_violation |
| POST | /scan | trigger_v3_scan |

## SQLite/Postgres Compatibility (TypeDecorators)

- `JSONVariant` — JSONB on Postgres, JSON on SQLite
- `TSVectorVariant` — TSVECTOR on Postgres, Text on SQLite

GIN index `ix_records_search_vector` uses `postgresql_using="gin"` — SQLAlchemy silently ignores on SQLite.

## Test Setup (conftest.py)

- In-memory SQLite via `aiosqlite` + `StaticPool`
- `app.dependency_overrides[get_db]` swaps the DB session
- `autouse=True` fixture runs `create_all`/`drop_all` per test
- `httpx.AsyncClient` with `ASGITransport` for API testing
- Config in `pyproject.toml` only: `asyncio_mode = "auto"`, `pythonpath = "."`
