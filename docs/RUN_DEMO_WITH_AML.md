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

## 5) Upload and review

1. Upload `AML_Policy_Demo_v1.pdf`
2. Wait for rules to appear (compile polling runs automatically)
3. Approve deterministic rules
4. Keep the subjective rule rejected/pending as proof of HITL control

## 6) Run scan

Click **Trigger Scan** in the header.

Then review:

- Violations list
- AI explanations
- Timeline panel for request lifecycle

## 7) Optional quick sanity queries

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

## 8) Reset for rerun

```bash
uv run python scripts/reset_db.py --yes
```

If you also want to clear business/demo tables:

```bash
uv run python scripts/reset_db.py --all-public --yes
```
