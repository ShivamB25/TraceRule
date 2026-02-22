# Frontend — Project Knowledge Base

**Generated:** 2026-02-22  
**Commit:** d045dec  
**Branch:** main

## OVERVIEW

Single-page compliance dashboard for TraceRule. React 19 + TypeScript 5.9 + Vite 7 + Tailwind CSS 4. No router — tab-based navigation via state. All business logic centralized in App.tsx; components are purely presentational.

## STRUCTURE

```
frontend/
├── src/
│   ├── main.tsx           # Entry point (StrictMode + createRoot)
│   ├── App.tsx            # Root component — ALL state, polling, handlers (360 lines)
│   ├── api.ts             # Fetch-based API client (6 functions, base=/api/v3)
│   ├── types.ts           # TypeScript interfaces (Rule, Violation, PolicyUploadResponse, ScanResult)
│   ├── index.css          # Tailwind import + custom fonts + scrollbar
│   └── components/        # 12 presentational components (props in, callbacks out)
│       ├── ErrorBoundary.tsx  # Class component error boundary for render crashes
│       ├── Header.tsx         # Top nav, scan/refresh buttons, status
│       ├── UploadPanel.tsx    # PDF drag-and-drop upload
│       ├── PipelineStrip.tsx  # 3-phase pipeline visualization
│       ├── StatsBar.tsx       # Rule/violation KPI counters
│       ├── RequestTimeline.tsx # Live API request/response log (technical mode toggle)
│       ├── ReviewPanel.tsx    # Tabbed rule review (pending/approved/rejected)
│       ├── RuleCard.tsx       # Individual rule with approve/reject actions
│       ├── ViolationsPanel.tsx # Violations list with status/rule filters
│       ├── ViolationCard.tsx  # Individual violation with courtroom verdict
│       ├── SeverityBadge.tsx  # CRITICAL/HIGH/MEDIUM/LOW badge
│       └── SqlBlock.tsx       # SQL code display
├── vite.config.ts         # React plugin, Tailwind plugin, port 3000, /api proxy → :8000
├── eslint.config.js       # Flat config: ts-eslint recommended + react-hooks + react-refresh
├── tsconfig.app.json      # strict, noUnusedLocals, noUnusedParameters, erasableSyntaxOnly
└── package.json           # bun.lock present — use bun for install
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add new component | `src/components/` | Functional, typed props interface, no hooks except local UI state |
| Add API endpoint call | `src/api.ts` | Follow existing fetch pattern: `const res = await fetch(...)` |
| Add TypeScript type | `src/types.ts` | Mirror backend schema field names exactly |
| Change app state/logic | `src/App.tsx` | All useState/useEffect/useCallback lives here |
| Change styles | Inline Tailwind classes | No CSS modules; global overrides in `src/index.css` |
| Change dev server port | `vite.config.ts` | `server.port` |
| Change API proxy target | `vite.config.ts` | `server.proxy['/api'].target` |

## CODE MAP

| Symbol | Type | File | Role |
|--------|------|------|------|
| `App` | Component | `App.tsx` | Root: state, polling, handlers, layout |
| `refreshData` | useCallback | `App.tsx` | `Promise.all([getRules, getViolations])` |
| `handleUpload` | async function | `App.tsx` | POST upload → sets lastUpload → triggers polling |
| `handleApprove/Reject` | async function | `App.tsx` | PATCH rule status → updates local state |
| `handleScan` | async function | `App.tsx` | POST scan → refreshes violations |
| `pushTimeline` | useCallback | `App.tsx` | Appends to timeline event log (max 30) |
| `uploadPolicy` | async fn | `api.ts` | `POST /api/v3/policies/upload` (FormData) |
| `getRules` | async fn | `api.ts` | `GET /api/v3/rules` with optional status/policy_id |
| `approveRule` | async fn | `api.ts` | `PATCH /api/v3/rules/{id}/approve` |
| `rejectRule` | async fn | `api.ts` | `PATCH /api/v3/rules/{id}/reject` |
| `getViolations` | async fn | `api.ts` | `GET /api/v3/violations` with optional v3_rule_id/status |
| `triggerScan` | async fn | `api.ts` | `POST /api/v3/scan` |
| `TimelineEvent` | interface | `RequestTimeline.tsx` | Exported; used by App.tsx for event tracking |

## CONVENTIONS

 **Component pattern**: Functional + explicit props interface. One class component (ErrorBoundary). No HOCs, no render props.
- **State management**: All in App.tsx via useState. No Context, Redux, or Zustand. Props drill down.
- **Data fetching**: Vanilla `fetch()` in `api.ts`. No React Query, SWR, or axios.
- **Polling**: Manual `setInterval` in useEffect. Compilation polls at 3s (40 attempts max).
 **Memoization**: `refreshData` and `pushTimeline` wrapped in `useCallback`. `PipelineStrip`, `SeverityBadge`, and `SqlBlock` use `React.memo`. Other handlers are plain async functions.
- **Icons**: `lucide-react` only. Import individual icons.
- **Styling**: Tailwind utility classes inline. Dark theme: `slate-950` bg, blue/cyan/emerald accents.
- **Fonts**: Space Grotesk (headings, 500-700), IBM Plex Sans (body, 400-600). Loaded via Google Fonts in `index.css`.
- **TypeScript**: Strict mode. Zero `any` types. Zero suppressions.
- **Refs**: `useRef` for StrictMode dedup (`initialLoadLoggedRef`) and DOM refs.
- **Error display**: Single `error` state string → red alert banner at top of main content.

## ANTI-PATTERNS

| Don't | Do Instead |
|-------|------------|
| Add state management library | Keep state in App.tsx (app is small enough) |
| Use `any` type | Explicit types; update `types.ts` |
| Add `ts-ignore` / `eslint-disable` | Fix the actual error |
| Create custom hooks (unless extracting from App.tsx) | Keep logic co-located in App.tsx |
| Use CSS modules or styled-components | Tailwind utility classes |
| Add React Router | Tab-based nav via `activeTab` state |
| Use axios or install HTTP client library | Vanilla `fetch()` in `api.ts` |
| Put business logic in components | Components are presentational; logic stays in App.tsx |

## COMMANDS

```bash
bun install                          # Install deps (bun.lock present)
bun run dev                          # Dev server on :3000, proxies /api → :8000
bun run build                        # tsc type-check + vite build → dist/
bun run lint                         # ESLint (flat config)
bun run preview                      # Preview production build
```

## NOTES

- **Frontend tests exist**: Vitest tests for API and key components (`src/api.test.ts`, `src/components/*.test.tsx`).
 **Error boundary exists**: `ErrorBoundary.tsx` wraps `ReviewPanel` and `ViolationsPanel` in App.tsx. Render errors in those sections show a retry prompt instead of crashing the full page.
- **No router** — entire UI is a single dashboard view. Tabs are state-driven, not URL-driven.
- **StrictMode** in dev causes double-mount; `initialLoadLoggedRef` prevents duplicate timeline entries.
- **API base**: Hardcoded `'/api/v3'` in `api.ts`. Vite proxy handles routing to backend in dev. In production, configure reverse proxy.
- **RequestTimeline** serves dual purpose: user-facing transparency + developer debugging. Toggle "technical mode" to see raw HTTP details.
- **Polling stops** automatically: compilation polling after rules appear (or 40 attempts).
