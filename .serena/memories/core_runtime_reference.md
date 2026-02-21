# Core runtime reference

## What this service does
TraceRule turns policy PDFs into SQL checks.

1. Upload PDF
2. AI compiles policy clauses into SQL rules
3. Human approves/rejects rules
4. Scanner runs approved deterministic rules

## Runtime facts that matter
- Upload endpoint returns quickly with `status=processing`.
- Background ingestion now writes rules to the same `policy_id` returned by upload (fixed on 2026-02-21).
- Scheduler runs scans on interval; manual scan is `POST /api/v1/scan`.

## Common gotchas
- In local dev, React `StrictMode` causes duplicate initial GETs. This is expected.
- If your DB has no business tables (only `policies/rules/violations`), compiled SQL will be weak.
- PDF parser may return `str` or `list[dict]`; ingestion already handles both.

## Verification baseline
- Backend tests pass: `uv run pytest` (23 tests).
- Frontend build passes: `npm run build`.
