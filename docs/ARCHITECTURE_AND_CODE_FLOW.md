# TraceRule Architecture and Code Flow

## What this system does

TraceRule turns policy text into enforceable SQL checks.

1. Ingest a policy file (`.pdf` or `.md`)
2. Compile policy clauses into SQL rules
3. Human approves or rejects each rule
4. Scanner runs approved deterministic rules against the database
5. Violations are stored with explainable context

The key property is simple: model usage happens during rule creation and explanation, not during deterministic scan execution.

## Runtime architecture

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

## Determinism and audit trail

### Determinism claim

Scan detection uses SQL execution only:

- `await db.execute(text(rule["compiled_sql"]))` in scanner
- No row-by-row model calls in scan path

### Audit trail chain

Each violation can be traced back through:

1. `violation.rule_id`
2. `rule.source_quote`
3. `rule.compiled_sql`
4. policy text in `policies.markdown_text`

This is why the system is reviewable by compliance and engineering teams.

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

## Model section (truthful, judge-safe wording)

### What is implemented

- Primary model in code: **Claude Sonnet 4.6**
- Compiler effort: high
- Explainer effort: medium

### Optional cross-model verification

This is not required for core runtime, but you can mention an external verification workflow:

- Primary answer from implemented compiler (Claude Sonnet 4.6)
- Secondary review with another model, such as Gemini 3.1 Pro (Preview), for comparison

Important wording:

- Treat Gemini 3.1 Pro as preview-tier
- Keep it clearly optional
- Do not claim the scan engine depends on it

## What to present to judges

Use this order:

1. Problem: probabilistic scanning is expensive and hard to audit
2. Architecture: compile once, scan deterministically
3. Human gate: no rule executes without approval
4. Demo: upload policy -> approve rule -> trigger scan -> view violations
5. Proof: show SQL + source quote + timeline

Recommended supporting docs:

- `docs/JUDGES.md` for narrative framing
- `docs/RUN_DEMO_WITH_AML.md` for exact run commands
- `scripts/README.md` for data extraction and loading utilities
