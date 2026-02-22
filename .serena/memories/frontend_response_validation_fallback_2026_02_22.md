Hotfix for runtime client error: `Response validation failed: (root): Invalid input: expected object, received array`.

What changed:
- File: `frontend/src/api.ts`
  - Added `parseViolationsResponse(data, limit, offset)`.
  - Client now accepts BOTH response shapes for `/api/v3/violations`:
    1) New paginated object `{items,total_count,limit,offset}`
    2) Legacy array `Violation[]`
  - Legacy array is normalized to paginated shape with:
    - `items = legacy array`
    - `total_count = array.length`
    - `limit/offset = requested params`
  - Improved zod error rendering for root-level errors by labeling empty path as `(root)`.

- File: `frontend/src/api.test.ts`
  - Added test verifying legacy array response is accepted and normalized.

Verification:
- `bun run lint` passed
- `bun run build` passed
- `bun run test` passed (4 tests total)
- LSP diagnostics clean for modified files.