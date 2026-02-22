# TraceRule — Core Runtime Reference

## V1 Runtime Flow

```
POST /api/v1/policies/upload
  → BackgroundTasks.add_task(ingest_policy)
  → pymupdf4llm.to_markdown() or UTF-8 decode
  → _introspect_db_schema() queries information_schema.columns
  → get_compiler_agent().run(markdown_text, deps=CompilerDeps)
  → Claude claude-sonnet-4-6 (adaptive thinking, high effort)
  → list[CompiledRule] → Rule ORM objects (status=pending_review)

PATCH /api/v1/rules/{id}/approve → status=approved

POST /api/v1/scan (or APScheduler every N minutes)
  → run_deterministic_scan(db)
  → SELECT approved + deterministic rules
  → Execute compiled_sql for each → save Violation rows (dedup by rule_id+record_pk)
  → _explain_new_violations() → Claude explainer agent for first 25, fallback text for rest
```

## V3 Runtime Flow

```
POST /api/v3/policies/upload
  → BackgroundTasks.add_task(_background_ingest_v3)
  → Background uses async_session_factory() directly (NOT Depends)
  → ingest_policy_v3():
    1. Extract text (PDF or MD)
    2. _extract_global_ontology() → lexicon agent → GlobalOntology{definitions}
    3. _introspect_db_schema() → schema context string
    4. _chunk_policy_text() → overlapping chunks (4000 chars, 500 overlap)
    5. For each chunk:
       → get_extractor_agent().run(chunk, deps=ExtractorDeps{db, schema, ontology})
       → Claude claude-sonnet-4-6 (enabled thinking, 10000 budget, max 20000 tokens)
       → @output_validator: compile_ast_to_sql() → EXPLAIN test SQL in sandboxed transaction
       → On failure: ModelRetry with Postgres stack trace → Claude self-heals
       → list[SymbolicRule] → V3Rule ORM objects (logic_tree_json, compiled_sql, status=pending_review)

PATCH /api/v3/rules/{id}/approve → status=approved

POST /api/v3/scan
  → run_v3_scan(db, session_factory):
    For each approved V3 rule:
      IF NOT requires_semantic_scan:
        → _scan_deterministic_v3(): Execute compiled_sql, save V3Violation (confidence=1.0)
      ELSE (mixed or pure-vague):
        → _scan_semantic_v3():
          1. Parse logic_tree_json → collect IS_VAGUE semantic_rubrics
          2. IF compiled_sql exists (mixed rule):
               Execute SQL (IS_VAGUE→1=1 gives superset) → candidate rows
               On SQL failure: fallback to BM25
             ELSE (pure-vague):
               _find_bm25_candidates() → ts_rank + websearch_to_tsquery on company_records
          3. Dedup against existing v3_violations
          4. For each candidate:
               → run_semantic_debate(record_data, rubric)
                 → Prosecutor + Defender run in parallel (asyncio.gather)
                 → Chief Justice renders Verdict{is_violation, confidence_score, reasoning}
               → If is_violation: save V3Violation with confidence + reasoning
```

## Key Differences V1 vs V3

| Aspect | V1 | V3 |
|--------|----|----|
| Compiler output | Raw SQL string | Deontic Logic AST (LogicNode tree) |
| SQL generation | Claude writes SQL directly | AST compiler (pure Python, deterministic) |
| SQL validation | None | @output_validator runs EXPLAIN, ModelRetry on failure |
| Subjective clauses | Marked non-deterministic, skipped | IS_VAGUE → 1=1 in SQL, courtroom evaluates candidates |
| Ontology | None | Global lexicon extracted from full PDF before chunking |
| Violations | Binary (found/not found) | Confidence score 0.0-1.0 from courtroom verdict |

## Common Gotchas

- PydanticAI reads `ANTHROPIC_API_KEY` from `os.environ`, not from pydantic-settings. Config.py bridges this.
- PostgreSQL `NUMERIC` → `Decimal`. Scanner's `_make_json_safe()` coerces to float.
- `pymupdf4llm.to_markdown()` returns `str | list[dict]` — ingestion handles both.
- Background tasks use `async_session_factory()` directly, NOT `Depends(get_db)`.
- React `StrictMode` causes duplicate initial GETs in local dev — expected.
