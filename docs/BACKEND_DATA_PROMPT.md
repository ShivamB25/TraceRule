# Backend Data Setup Prompt — TraceRule V3 (Neuro-Symbolic)

## Step 0: Load context first

```text
serena_activate_project("policysense")
serena_read_memory("project_overview")
serena_read_memory("codebase_structure")
serena_read_memory("core_runtime_reference")
serena_read_memory("code_style_and_conventions")
serena_read_memory("task_completion_checklist")
```

Then read these files:

```text
app/models.py
app/schemas.py
app/services/ingestion.py
app/services/scanner.py
app/agents/extractor.py
app/agents/courtroom.py
app/ast_compiler.py
app/api/router.py
scripts/extract_aml_demo.py
scripts/load_aml_demo_to_db.py
scripts/reset_db.py
docs/ARCHITECTURE_AND_CODE_FLOW.md
docs/system-design.md
```

---

## Goal

Prepare realistic business data for **V3 scanning** so the system can demonstrate all three paths:

1. Pure deterministic SQL violations
2. Mixed deterministic + semantic (courtroom) violations
3. Pure vague semantic violations via BM25 + courtroom

You must support these runtime models:

- `transactions` and `accounts` business tables (already loaded by script)
- `company_records` semantic index table (for BM25 + courtroom path)

---

## Current architecture assumptions (must match code)

### V3 endpoints

- `POST /api/v3/policies/upload`
- `GET /api/v3/rules`
- `PATCH /api/v3/rules/{id}/approve`
- `PATCH /api/v3/rules/{id}/reject`
- `POST /api/v3/scan`
- `GET /api/v3/violations`

### V3 rule fields

- `logic_tree_json`
- `requires_semantic_scan`
- `compiled_sql`
- `target_table`

### V3 violation fields

- `v3_rule_id`
- `record_id`
- `violation_data`
- `verdict_reasoning`
- `confidence_score`

Do not use old V1-only fields in new V3 docs or scripts (`is_deterministic`, `rule_id`, `record_pk`, `ai_explanation`, `violations_found`).

---

## Data setup workflow

## 1) Extract AML subset from Kaggle zip

Place the original AML zip(s) under `data/`, then run:

```bash
uv run python scripts/extract_aml_demo.py --profile small --budget-gb 1.5
```

Output goes to:

- `data/aml_demo/`

## 2) Load business tables (transactions/accounts)

```bash
uv run python scripts/load_aml_demo_to_db.py --max-trans-rows 250000 --max-account-rows 50000
```

This creates and fills:

- `transactions`
- `accounts`

## 3) Build `company_records` semantic index (required for pure-vague V3 rules)

Create a script at `scripts/build_company_records_index.py` that:

1. Creates `company_records` if needed (same schema as ORM model)
2. Truncates existing rows (unless `--no-truncate`)
3. Copies records from business tables into `company_records`
4. Fills `search_text` with concise natural text for BM25
5. Populates `ts_vector` using `to_tsvector('english', search_text)`

Use this mapping for initial index build:

- Source table `transactions` -> `company_records.table_name='transactions'`
- Source table `accounts` -> `company_records.table_name='accounts'`

`data_payload` should preserve the raw source row as JSON.

### Example SQL inside the script

```sql
INSERT INTO company_records (table_name, data_payload, search_text, ts_vector)
SELECT
  'transactions',
  jsonb_build_object(
    'id', t.id,
    'from_account', t.from_account,
    'to_account', t.to_account,
    'amount_paid', t.amount_paid,
    'payment_currency', t.payment_currency,
    'receiving_currency', t.receiving_currency,
    'payment_format', t.payment_format,
    'is_laundering', t.is_laundering,
    'event_ts', t.event_ts
  ),
  concat_ws(' ',
    'transaction',
    t.from_account,
    t.to_account,
    t.payment_format,
    t.payment_currency,
    t.receiving_currency,
    t.amount_paid::text,
    CASE WHEN t.is_laundering THEN 'laundering flagged suspicious' ELSE 'normal' END
  ),
  to_tsvector('english', concat_ws(' ',
    'transaction',
    t.from_account,
    t.to_account,
    t.payment_format,
    t.payment_currency,
    t.receiving_currency,
    t.amount_paid::text,
    CASE WHEN t.is_laundering THEN 'laundering flagged suspicious' ELSE 'normal' END
  ))
FROM transactions t;
```

## 4) Verify minimum data health

Run these checks:

```bash
psql tracerule -c "SELECT COUNT(*) FROM transactions;"
psql tracerule -c "SELECT COUNT(*) FROM accounts;"
psql tracerule -c "SELECT COUNT(*) FROM company_records;"
psql tracerule -c "SELECT COUNT(*) FROM company_records WHERE table_name='transactions';"
psql tracerule -c "SELECT COUNT(*) FROM company_records WHERE ts_vector IS NOT NULL;"
```

All counts should be > 0 for a useful demo.

## 5) Exercise V3 API end-to-end

```bash
# Upload a policy
curl -X POST http://localhost:8000/api/v3/policies/upload -F "file=@AML_Policy_Demo_v1.pdf"

# List rules
curl http://localhost:8000/api/v3/rules | python -m json.tool

# Approve one or more rules
curl -X PATCH http://localhost:8000/api/v3/rules/1/approve

# Trigger V3 scan
curl -X POST http://localhost:8000/api/v3/scan | python -m json.tool

# Inspect V3 violations
curl http://localhost:8000/api/v3/violations | python -m json.tool
```

You should see scan output shaped like:

```json
{
  "deterministic_violations": 0,
  "semantic_violations": 0,
  "total": 0
}
```

And violation rows shaped like:

```json
{
  "id": 1,
  "v3_rule_id": 2,
  "record_id": 123,
  "violation_data": {"...": "..."},
  "verdict_reasoning": "...",
  "confidence_score": 0.84,
  "status": "open"
}
```

---

## Guardrails

- Do not reintroduce pgvector, numpy, embeddings, or RRF
- Do not change V1 models/routes while setting up V3 data
- Do not use `Any`, `@ts-ignore`, or `as any`
- Do not bypass SQLAlchemy async patterns in app runtime code

---

## Deliverables checklist

- `scripts/build_company_records_index.py` exists and works
- `transactions`, `accounts`, and `company_records` all populated
- V3 upload, approve, scan, and violations endpoints return valid payloads
- Demo-ready counts and sanity queries documented
