# TraceRule V3 — Current State (2026-02-22)

**Status:** Implementation complete, all tests passing, pgvector removed

## Architecture: SQL Pre-Filtering + Multi-Agent Semantic Evaluation

No pgvector. No embeddings. No RRF. No numpy.

### Scan paths by rule type:

| Rule Type | Example | Scan Path |
|-----------|---------|-----------|
| Pure deterministic | `age < 18` | Execute compiled SQL → violations (confidence=1.0) |
| Mixed (det + vague) | `amount > 500 AND IS_VAGUE("lavish")` | SQL pre-filter (1=1 superset) → courtroom per candidate |
| Pure vague | `IS_VAGUE("lavish gift")` | BM25 text search → courtroom per candidate |

### Why no pgvector:
1. Embedding structured tabular data is an anti-pattern
2. Anthropic has no embedding API — would need second provider
3. The stub was returning `[0.0] * 1536` — would crash any demo
4. The adversarial courtroom IS the semantic reranker

## V3 Files

### New files created:
- `app/ast_compiler.py` — Pure Python AST→SQL (AND/OR/UNLESS/IS_VAGUE→1=1/CONTAINS→ILIKE/IS_NULL/IS_NOT_NULL, bool before numeric check)
- `app/agents/extractor.py` — PydanticAI Agent with @output_validator reflexion, ModelRetry with Postgres stack trace
- `app/agents/courtroom.py` — Three @lru_cache agent factories (Prosecutor, Defender, Chief Justice), parallel via asyncio.gather
- `app/api/__init__.py` + `app/api/router.py` — V3 endpoints under /api/v3/

### Modified files:
- `app/schemas.py` — GlobalOntology, Condition, LogicNode (recursive + model_rebuild), SymbolicRule, V3 responses
- `app/models.py` — CompanyRecord (BM25 only, no embedding column), V3Rule, V3Violation + TSVectorVariant TypeDecorator
- `app/services/ingestion.py` — ingest_policy_v3(), _extract_global_ontology(), _chunk_policy_text()
- `app/services/scanner.py` — run_v3_scan(), _scan_deterministic_v3(), _scan_semantic_v3(), _find_bm25_candidates()
- `app/main.py` — V3 router registered, version 3.0.0, NO vector extension
- `pyproject.toml` — pgvector and numpy REMOVED

### V3 test files:
- `tests/test_ast_compiler.py` — 23 tests
- `tests/test_v3_rules.py` — 11 tests
- `tests/test_v3_violations.py` — 6 tests (was 7, recount: 6)
- `tests/test_v3_scanner.py` — 7 tests
- `tests/test_v3_policies.py` — 4 tests

## Verification State

- **76/76 tests passing** (26 V1 + 50 V3) in ~0.7s
- `ruff check` — all passed
- `ruff format` — all formatted
- `uv sync` — pgvector and numpy uninstalled from venv

## Key Technical Details

- V3Violation.record_id is plain `Mapped[int]` (no ForeignKey to company_records — allows deterministic scan to reference any table's id)
- AST compiler: bool check before numeric check (Python bool subclasses int)
- Extractor agent: retries=4, thinking budget=16000
- Courtroom: Prosecutor+Defender thinking=8000, Chief Justice thinking=16000
- All agents use claude-sonnet-4-6
- BM25 uses Postgres-native ts_rank + websearch_to_tsquery (no extensions needed)
