# Frontend flow reference

## Request flow
1. Page load
   - `GET /api/v1/rules`
   - `GET /api/v1/violations`

2. Upload
   - `POST /api/v1/policies/upload`
   - receive `{id, status=processing}`

3. Compile polling
   - poll `GET /api/v1/rules?policy_id={id}` every 3s
   - stop when rules appear

4. Human review
   - `PATCH /api/v1/rules/{id}/approve`
   - `PATCH /api/v1/rules/{id}/reject`

5. Scan
   - `POST /api/v1/scan`
   - refresh `GET /api/v1/violations`

6. Explanation polling
   - if any violation has `ai_explanation=null`, poll violations every 5s

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
