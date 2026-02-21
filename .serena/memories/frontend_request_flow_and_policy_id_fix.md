# TraceRule — Frontend request flow and policy_id consistency fix (2026-02-21)

## Frontend request flow (React)

1. Page load (App mount): frontend calls `GET /api/v1/rules` and `GET /api/v1/violations` in parallel.
2. Upload flow:
   - frontend calls `POST /api/v1/policies/upload`
   - API immediately returns `{id, filename, status="processing"}`
   - frontend polls `GET /api/v1/rules?policy_id={id}` every 3s until rules appear
3. Review flow:
   - `PATCH /api/v1/rules/{id}/approve` or `/reject`
   - frontend updates local rule state with the response payload
4. Scan flow:
   - `POST /api/v1/scan`
   - frontend refreshes `GET /api/v1/violations`
   - if any `ai_explanation` is null, frontend polls violations every 5s until filled

## StrictMode note

In local development, `frontend/src/main.tsx` wraps app in `StrictMode`, so initial mount effects fire twice. Seeing duplicate `GET /rules` and `GET /violations` in local logs is expected and not a backend regression.

## Critical bug fixed

### Problem
Upload route created a placeholder `Policy` row, but background ingestion created a second `Policy` row. Rules were attached to the second row, so `policy_id` from upload response did not always match generated rules.

### Fix
- `app/routes/policies.py`
  - `_background_ingest` now accepts `policy_id`
  - upload route passes `policy.id` into background task
- `app/services/ingestion.py`
  - `ingest_policy(..., policy_id: int | None = None)` now accepts optional target policy id
  - if `policy_id` exists, ingestion updates that same row (`filename`, `markdown_text`, `status`) and writes rules with that `policy_id`
  - only falls back to creating a new policy if provided `policy_id` cannot be found

### Verification
- `lsp_diagnostics` clean for modified files
- full test suite passes: `uv run pytest` -> 23 passed