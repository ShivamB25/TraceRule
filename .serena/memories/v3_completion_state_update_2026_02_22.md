Post-completion hardening update:

1) Violations pagination contract
- Backend endpoint `/api/v3/violations` returns:
  - items
  - total_count
  - limit
  - offset
- Added `PaginatedViolationsResponse` schema.
- Route switched from raw list response to wrapper model.
- Tests updated for shape + pagination.

2) Frontend RAM guardrails
- Violations fetch is paginated (no full list load).
- Frontend page size set to 25 for lower memory pressure.
- Stale request protection added in refresh pipeline.
- Timeline event cap constantized and enforced.
- Violation rendering optimized:
  - rule id -> title map precomputed once
  - heavy stagger animation avoided for larger pages
  - cards use content-visibility hints
  - full pretty JSON is generated only when user expands a card

3) Validation status
- Backend tests: 78 passed.
- Frontend lint/build/tests: all passed.
- LSP diagnostics clean on modified frontend files.
