# TraceRule Architecture and Code Flow

## What this system does

TraceRule turns policy text into enforceable compliance checks. It has two coexisting pipelines:

**V1 — Deterministic Compilation**: Policy PDF → Claude compiles to raw SQL → human approves → scheduler executes SQL → violations logged.

**V3 — Neuro-Symbolic with Adversarial Courtroom**: Policy PDF → global ontology extraction → Claude compiles to deontic logic ASTs → pure-Python AST→SQL compiler → SQL auto-healed via EXPLAIN → human approves → scanner routes to deterministic SQL, SQL+courtroom, or BM25+courtroom paths → violations logged with confidence scores.

The key property: model usage happens during rule creation (and courtroom evaluation for subjective clauses). Deterministic scanning never touches the LLM.

## V1 Runtime Architecture

### Phase 1: Ingestion and compilation

Input path:

- Endpoint: `POST /api/v1/policies/upload`
- File: `app/routes/policies.py`
- Background handoff: `_background_ingest(...)`

Core ingestion logic:

- File: `app/services/ingestion.py`
- Function: `ingest_policy(...)`
- Supported formats:
  - `.pdf` -> `pymupdf4llm.to_markdown(...)`
  - `.md`/`.markdown` -> UTF-8 decode

Compiler behavior:

- File: `app/agents/compiler.py`
- Model: `claude-sonnet-4-6`
- Output: `list[CompiledRule]` (`app/schemas.py`)
- Rule fields include:
  - `title`
  - `source_quote`
  - `severity`
  - `is_deterministic`
  - `compiled_sql`

State transition:

- `policies.status`: `processing` -> `completed` or `failed`
- New rules created as `status='pending_review'`

Important fix already in place:

- Background ingestion uses the same `policy_id` created by upload route, so frontend polling by `policy_id` is consistent.

### Phase 2: Human approval gate

Endpoints:

- `GET /api/v1/rules`
- `PATCH /api/v1/rules/{id}/approve`
- `PATCH /api/v1/rules/{id}/reject`

Files:

- Backend: `app/routes/rules.py`
- Frontend: `frontend/src/components/ReviewPanel.tsx`, `frontend/src/components/RuleCard.tsx`

Behavior:

- Rules remain inert until explicitly approved.
- Rejected rules are retained for traceability.

### Phase 3: Deterministic scan and violation logging

Trigger paths:

- Scheduled: APScheduler in `app/main.py`
- Manual: `POST /api/v1/scan` in `app/routes/violations.py`

Execution logic:

- File: `app/services/scanner.py`
- Function: `run_deterministic_scan(...)`
- Query source: each approved deterministic rule's `compiled_sql`
- Violation dedup key: `(rule_id, record_pk)` among open violations

Stored violation payload:

- `rule_id`
- `record_pk`
- `violating_data` (JSON-safe transformed)
- `ai_explanation` (nullable until generated)

---

## V3 Runtime Architecture

### Phase 1: Neuro-Symbolic Ingestion

Input path:

- Endpoint: `POST /api/v3/policies/upload`
- File: `app/api/router.py`
- Background handoff: `_background_ingest_v3(...)`
- Background uses `async_session_factory()` directly (NOT `Depends(get_db)`)

Core ingestion logic:

- File: `app/services/ingestion.py`
- Function: `ingest_policy_v3(...)`
- Steps:
  1. Extract text (PDF via pymupdf4llm or MD via UTF-8 decode)
  2. `_extract_global_ontology()` → lexicon agent reads full PDF → `GlobalOntology{definitions}` — domain terms mapped to DB columns
  3. `_introspect_db_schema()` → schema context string from `information_schema.columns`
  4. `_chunk_policy_text()` → overlapping chunks (4000 chars, 500 overlap)
  5. For each chunk → extractor agent → `list[SymbolicRule]`

Extractor agent behavior:

- File: `app/agents/extractor.py`
- Model: `claude-sonnet-4-6` with thinking budget of 16000 tokens
- Output: `list[SymbolicRule]` — each contains a `LogicNode` tree (recursive AND/OR/UNLESS nodes with `Condition` leaves)
- Dependencies: `ExtractorDeps{db, db_schema_context, global_ontology}`
- Retries: 4

SQL auto-healing (`@output_validator`):

1. AST compiler (`app/ast_compiler.py`) converts `LogicNode` tree to SQL deterministically
2. Validator runs `EXPLAIN {sql}` in a sandboxed nested transaction (`begin_nested()`)
3. If Postgres rejects → `ModelRetry` with full stack trace injected into prompt
4. Claude sees the error and self-corrects the logic tree
5. Loop repeats up to 4 times
6. SQL that passes EXPLAIN is guaranteed executable

AST Compiler:

- File: `app/ast_compiler.py`
- Function: `compile_ast_to_sql(rule: SymbolicRule) -> str`
- Pure Python, no LLM, deterministic
- Operator mapping:
  - AND/OR → SQL AND/OR
  - UNLESS → `AND NOT` (defeasible logic)
  - IS_VAGUE → `1=1` (deliberate superset)
  - CONTAINS → `ILIKE '%value%'`
  - IS_NULL / IS_NOT_NULL → SQL IS NULL / IS NOT NULL
  - Bool check placed before numeric check (Python `bool` subclasses `int`)

State transition:

- `policies.status`: `processing` -> `completed` or `failed`
- V3 rules created as `status='pending_review'` with `logic_tree_json` and `compiled_sql`

### Phase 2: Human approval gate

Endpoints:

- `GET /api/v3/rules`
- `PATCH /api/v3/rules/{id}/approve`
- `PATCH /api/v3/rules/{id}/reject`

Files:

- Backend: `app/api/router.py`

Behavior:

- Same as V1 — rules remain inert until explicitly approved.
- V3 rules additionally show the logic tree structure alongside the compiled SQL.

### Phase 3: Three-path scanning

Trigger paths:

- Manual: `POST /api/v3/scan` in `app/api/router.py`

Execution logic:

- File: `app/services/scanner.py`
- Function: `run_v3_scan(db, session_factory)`
- Routes each approved rule to one of three paths based on `has_vague_conditions`:

**Path A — Pure Deterministic** (`has_vague_conditions=False`):

- Function: `_scan_deterministic_v3()`
- Execute `compiled_sql` → save `V3Violation` rows with `confidence_score=1.0`
- Dedup by `(rule_id, record_id)` among existing V3 violations

**Path B — Mixed Rules** (deterministic + IS_VAGUE conditions):

- Function: `_scan_semantic_v3()`
- Steps:
  1. Parse `logic_tree_json` → `_collect_semantic_rubrics()` extracts IS_VAGUE values as rubrics
  2. Execute compiled SQL (IS_VAGUE → `1=1` returns superset of candidates)
  3. If SQL fails → automatic fallback to BM25 (`_find_bm25_candidates()`)
  4. Dedup candidates against existing violations
  5. For each candidate → adversarial courtroom → `Verdict{is_violation, confidence_score, reasoning}`
  6. If `is_violation=True` → save `V3Violation` with confidence + reasoning

**Path C — Pure Vague Rules** (only IS_VAGUE conditions, no compiled SQL):

- Function: `_scan_semantic_v3()`
- Steps:
  1. `_find_bm25_candidates()` → Postgres-native `ts_rank` + `websearch_to_tsquery` on `company_records`
  2. Dedup candidates
  3. For each candidate → adversarial courtroom → Verdict
  4. If violation → save with confidence + reasoning

### Adversarial Courtroom

- File: `app/agents/courtroom.py`
- Three `@lru_cache` agent factories:
  - `_get_prosecutor()` — Claude claude-sonnet-4-6, thinking budget 8000
  - `_get_defender()` — Claude claude-sonnet-4-6, thinking budget 8000
  - `_get_chief_justice()` — Claude claude-sonnet-4-6, thinking budget 16000
- Entry function: `run_semantic_debate(record_data, rubric)`
- Flow:
  1. Prosecutor + Defender run in parallel via `asyncio.gather`
  2. Each gets: record data, semantic rubric, source quote
  3. Chief Justice gets: both arguments + original evidence
  4. Returns: `Verdict{is_violation: bool, confidence_score: float, reasoning: str}`

---

## Determinism and audit trail

### Determinism claim

V1 scan detection uses SQL execution only:

- `await db.execute(text(rule["compiled_sql"]))` in scanner
- No row-by-row model calls in scan path

V3 extends this:

- Pure deterministic V3 rules: same as V1 — SQL only, `confidence=1.0`
- Mixed/vague V3 rules: SQL pre-filter (deterministic) + courtroom (model-based, but structured adversarial debate with explicit reasoning chain)
- The courtroom produces auditable artifacts: Prosecutor argument, Defender argument, Chief Justice reasoning, confidence score

### Audit trail chain

V1 violations trace back through:

1. `violation.rule_id`
2. `rule.source_quote`
3. `rule.compiled_sql`
4. policy text in `policies.markdown_text`

V3 violations trace back through:

1. `v3_violation.rule_id`
2. `v3_rule.source_quote`
3. `v3_rule.logic_tree_json` (the full AST)
4. `v3_rule.compiled_sql` (generated from AST)
5. `v3_violation.verdict_reasoning` (courtroom's rationale, if semantic)
6. `v3_violation.confidence_score` (calibrated confidence)
7. policy text in `policies.markdown_text`

---

## Frontend code flow

Main file: `frontend/src/App.tsx`

1. Initial load:
  - `GET /api/v1/rules`
  - `GET /api/v1/violations`
2. Upload:
  - `POST /api/v1/policies/upload`
  - poll `GET /api/v1/rules?policy_id={id}` every 3s until rules appear
3. Review:
  - approve/reject endpoints update local rule state
4. Scan:
  - `POST /api/v1/scan`
  - refresh violations
5. Explanation polling:
  - if any `ai_explanation` is null, poll violations every 5s

Observability in UI:

- `RequestTimeline` panel shows lifecycle events
- Technical mode displays endpoint-level request/response lines

Note: The frontend currently targets V1 endpoints only. V3 frontend (AST visualization, courtroom verdict display, confidence scores) is planned.

---

## Model section

### What is implemented

- Primary model in code: **Claude Sonnet 4.6** (`claude-sonnet-4-6`)
- V1 Compiler effort: high (adaptive thinking)
- V1 Explainer effort: medium
- V3 Extractor: enabled thinking, 16000 token budget
- V3 Prosecutor/Defender: enabled thinking, 8000 token budget
- V3 Chief Justice: enabled thinking, 16000 token budget

### LLM framework

PydanticAI with:
- `output_type=` for structured output
- `@output_validator` for SQL auto-healing (V3)
- `ModelRetry` for self-correction loops
- `RunContext[DepsType]` for dependency injection
- `@lru_cache(maxsize=1)` factory pattern for all agents

---

## What to present to judges

Use this order:

1. Problem: probabilistic scanning is expensive, inconsistent, and can't handle subjectivity
2. V1 Architecture: compile once, scan deterministically
3. V3 Evolution: deontic logic ASTs, SQL auto-healing, adversarial courtroom for subjective clauses
4. Human gate: no rule executes without approval
5. Demo: upload policy -> approve rule -> trigger scan -> view violations (V1) + view confidence-scored violations from courtroom (V3)
6. Proof: show SQL + source quote + logic tree + courtroom reasoning

Recommended supporting docs:

- `docs/system-design.md` for narrative framing
- `docs/RUN_DEMO_WITH_AML.md` for exact run commands
- `docs/ARCHITECTURE_RESEARCH.md` for design decision rationale
