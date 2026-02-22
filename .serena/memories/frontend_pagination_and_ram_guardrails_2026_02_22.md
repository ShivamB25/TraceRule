Date: 2026-02-22

Implemented end-to-end frontend stability improvements for large violation volumes.

Backend/API contract changes:
- `GET /api/v3/violations` now returns paginated payload:
  - `items: list[V3ViolationResponse]`
  - `total_count: int`
  - `limit: int`
  - `offset: int`
- Added `PaginatedViolationsResponse` in `app/schemas.py`.
- Updated violations route in `app/api/router.py` to return the wrapper model.
- Updated tests in `tests/test_v3_violations.py` for response shape and pagination assertions.

Frontend pagination integration:
- Added `PaginatedViolations` type + zod schema in `frontend/src/types.ts`.
- Updated `getViolations(...)` in `frontend/src/api.ts` to accept `limit/offset` and parse paginated response.
- Updated `frontend/src/App.tsx`:
  - tracks `violationPage` + `violationTotalCount`
  - uses paginated fetches
  - resets page to 1 on filter changes
  - stats now show total from backend count

RAM/memory guardrails added in UI:
- Lowered frontend page size to 25 (`VIOLATIONS_PAGE_SIZE = 25`) to reduce per-render memory pressure.
- Added stale-request guard in `refreshData` via `refreshRequestIdRef` to avoid out-of-order state churn.
- Capped timeline state with `MAX_TIMELINE_EVENTS` constant.
- Optimized violations rendering in `frontend/src/components/ViolationsPanel.tsx`:
  - precomputed `ruleTitleById` map (avoid repeated linear lookups)
  - disabled stagger animation when many cards
  - added CSS content-visibility + contain-intrinsic-size on card wrappers
- Optimized `frontend/src/components/ViolationCard.tsx`:
  - removed per-card full JSON pretty-print by default
  - preview shows first entries only
  - full formatted JSON generated only when user expands a card
  - component wrapped with `memo`

Verification evidence:
- Backend: `uv run pytest` -> 78 passed.
- Frontend: `bun run lint && bun run build && bun run test` -> all pass.
- LSP diagnostics clean for modified frontend files.