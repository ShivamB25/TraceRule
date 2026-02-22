# TraceRule V3 — Completion State

**Date:** 2026-02-22
**Status:** Implementation complete, all tests passing

## What V3 Added

### New Files
- `app/ast_compiler.py` — Pure Python recursive AST→SQL compiler (AND/OR/UNLESS/IS_VAGUE/CONTAINS/IS_NULL)
- `app/agents/extractor.py` — PydanticAI Agent with `@output_validator` reflexion, validates SQL via EXPLAIN
- `app/agents/courtroom.py` — Three-agent adversarial debate (Prosecutor, Defender, Chief Justice)
- `app/api/__init__.py` — Package marker
- `app/api/router.py` — V3 FastAPI endpoints under `/api/v3/`

### Modified Files
- `app/schemas.py` — Added GlobalOntology, Condition, LogicNode (recursive), SymbolicRule, V3 response models
- `app/models.py` — Added CompanyRecord, V3Rule, V3Violation + VectorVariant, TSVectorVariant TypeDecorators
- `app/services/ingestion.py` — Added ingest_policy_v3(), _extract_global_ontology(), _chunk_policy_text()
- `app/services/scanner.py` — Added run_v3_scan(), RRF query, courtroom routing, Mapping type hints
- `app/main.py` — Registered V3 router, CREATE EXTENSION vector, version 3.0.0
- `pyproject.toml` — Added pgvector, numpy dependencies

## TypeDecorator Pattern (SQLite compat)
All Postgres-specific types use TypeDecorator pattern for SQLite test compatibility:
- `JSONVariant` — JSONB on Postgres, JSON on SQLite (pre-existing)
- `VectorVariant(dim)` — pgvector Vector on Postgres, Text on SQLite (new)
- `TSVectorVariant` — TSVECTOR on Postgres, Text on SQLite (new)

V3 models use these variants instead of raw Postgres types.

## GIN Index
`ix_records_search_vector` uses `postgresql_using="gin"` — SQLAlchemy silently ignores this kwarg on SQLite, so no conditional logic needed.

## Test State
- 26 tests, all passing (0.25s)
- Tests use in-memory SQLite via aiosqlite + StaticPool
- No V3-specific tests yet (only V1 tests exist)

## Lint State
- Ruff check clean (except 2 intentional E402 in main.py for router registration pattern)
- Ruff format clean
- LSP diagnostics clean on all changed files

## V3 API Endpoints
All under `/api/v3/`:
- POST `/policies/upload` — Upload policy, triggers V3 ingestion
- GET/GET{id} `/rules` — List/get V3 rules
- PATCH `/rules/{id}/approve` and `/reject`
- GET/GET{id} `/violations` — List/get V3 violations
- POST `/scan` — Trigger V3 scan (deterministic + semantic)
