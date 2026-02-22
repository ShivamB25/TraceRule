# Frontend flow reference

## Request flow (V3 endpoints)
1. Page load
   - `Promise.all([GET /api/v3/rules, GET /api/v3/violations])`

2. Upload
   - `POST /api/v3/policies/upload`
   - receive `{id, status=processing}`

3. Compile polling
   - poll `GET /api/v3/rules?policy_id={id}` every 3s
   - stop when rules appear (max 40 attempts)

4. Human review
   - `PATCH /api/v3/rules/{id}/approve`
   - `PATCH /api/v3/rules/{id}/reject`

5. Scan
   - `POST /api/v3/scan`
   - refresh `GET /api/v3/violations` (paginated, 25 per page)

6. Violation polling
   - if any violation has null `verdict_reasoning`, poll violations every 5s

## Current UI features
- Manual refresh button in header
- Last-updated time in header
- Violations filters backed by API query params (`rule_id`, `status`)
- Live Request Timeline panel
- Technical mode in timeline (shows request/response lines)

## Main files
- `frontend/src/App.tsx`
- `frontend/src/api.ts`
- `frontend/src/components/RequestTimeline.tsx`
- `frontend/src/components/ViolationsPanel.tsx`
- `frontend/src/components/Header.tsx`
