# Run demo with IBM AML data

This runbook assumes:

- `data/aml_demo` already exists (capped extraction)
- Postgres is running

## 1) Ensure AML demo rows are loaded

```bash
uv run python scripts/load_aml_demo_to_db.py --max-trans-rows 50000 --max-account-rows 50000
```

## 2) Start backend

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 3) Start frontend (new terminal)

```bash
cd frontend
npm run dev
```

Open `http://localhost:3000`.

## 4) Create the policy PDF to upload

Use content from `docs/AML_POLICY_DEMO_CONTENT.md`.

Fast path:

1. Paste the content into Google Docs / Notion / Word
2. Export as PDF
3. Name it `AML_Policy_Demo_v1.pdf`

## 5) Upload and review (V1 — deterministic only)

1. Upload `AML_Policy_Demo_v1.pdf`
2. Wait for rules to appear (compile polling runs automatically)
3. Approve deterministic rules
4. Keep the subjective rule rejected/pending as proof of HITL control

## 6) Run V1 scan

Click **Trigger Scan** in the header.

Then review:

- Violations list
- AI explanations
- Timeline panel for request lifecycle

## 7) Upload and review (V3 — neuro-symbolic + courtroom)

Use the V3 endpoints for the full pipeline:

```bash
# Upload via V3 endpoint (neuro-symbolic compilation)
curl -X POST http://localhost:8000/api/v3/policies/upload \
  -F "file=@AML_Policy_Demo_v1.pdf"

# Poll for V3 rules
curl http://localhost:8000/api/v3/rules | python -m json.tool

# Approve a V3 rule
curl -X PATCH http://localhost:8000/api/v3/rules/1/approve

# Trigger V3 scan (deterministic + courtroom for vague clauses)
curl -X POST http://localhost:8000/api/v3/scan | python -m json.tool

# View V3 violations with confidence scores
curl http://localhost:8000/api/v3/violations | python -m json.tool
```

V3 differences to highlight for judges:

- Rules now have `logic_tree_json` — the deontic logic AST
- Subjective clauses (e.g., "unusual narrative context") are handled via adversarial courtroom instead of being skipped
- Violations include `confidence_score` (0.0–1.0) and `verdict_reasoning` from the courtroom
- SQL was auto-healed via EXPLAIN — guaranteed executable

## 8) Optional quick sanity queries

```bash
uv run python - <<'PY'
import asyncio
from sqlalchemy import text
from app.database import engine

async def main():
    async with engine.connect() as conn:
        checks = {
            'tx_total': 'SELECT COUNT(*) FROM transactions',
            'gt_10000': 'SELECT COUNT(*) FROM transactions WHERE amount_paid > 10000',
            'cash_gt_5000': "SELECT COUNT(*) FROM transactions WHERE payment_format = 'Cash' AND amount_paid > 5000",
            'cross_currency_gt_8000': 'SELECT COUNT(*) FROM transactions WHERE payment_currency <> receiving_currency AND amount_paid > 8000',
            'laundering_tagged': 'SELECT COUNT(*) FROM transactions WHERE is_laundering = TRUE',
        }
        for name, query in checks.items():
            r = await conn.execute(text(query))
            print(f"{name}: {r.scalar_one()}")
    await engine.dispose()

asyncio.run(main())
PY
```

## 9) V3-specific checks

```bash
uv run python - <<'PY'
import asyncio
from sqlalchemy import text
from app.database import engine

async def main():
    async with engine.connect() as conn:
        checks = {
            'v3_rules_total': 'SELECT COUNT(*) FROM v3_rules',
            'v3_rules_approved': "SELECT COUNT(*) FROM v3_rules WHERE status = 'approved'",
            'v3_rules_with_vague': 'SELECT COUNT(*) FROM v3_rules WHERE requires_semantic_scan = TRUE',
            'v3_violations_total': 'SELECT COUNT(*) FROM v3_violations',
            'v3_high_confidence': 'SELECT COUNT(*) FROM v3_violations WHERE confidence_score >= 0.8',
            'company_records': 'SELECT COUNT(*) FROM company_records',
        }
        for name, query in checks.items():
            try:
                r = await conn.execute(text(query))
                print(f"{name}: {r.scalar_one()}")
            except Exception as e:
                print(f"{name}: ERROR - {e}")
    await engine.dispose()

asyncio.run(main())
PY
```

## 10) Reset for rerun

```bash
uv run python scripts/reset_db.py --yes
```

If you also want to clear business/demo tables:

```bash
uv run python scripts/reset_db.py --all-public --yes
```
