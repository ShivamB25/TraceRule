# TraceRule Frontend

Single-page compliance dashboard. React 19 + TypeScript + Vite + Tailwind CSS v4.

## Setup

```bash
cd frontend
npm install
npm run dev
```

Runs on [http://localhost:3000](http://localhost:3000). The Vite dev server proxies `/api` requests to the backend at `localhost:8000`.

The backend must be running first:

```bash
# From project root
uv run uvicorn app.main:app --reload
```

## What it does

Three panels, top to bottom:

1. **Upload** — drag a compliance policy PDF onto the drop zone. The backend compiles it into V3 rules with logic trees and compiled SQL (usually 10-30 seconds).
2. **Review** — tabbed list of compiled rules (pending / approved / rejected). Each card shows source quote, logic tree, target table, semantic/deterministic mode, and approve/reject controls.
3. **Violations** — scan results after running approved rules. Deterministic violations show record data, and semantic violations include courtroom verdict reasoning with confidence.

## Stack

- React 19, no router (single page, tab-based navigation via state)
- Tailwind CSS v4, dark theme, no CSS modules
- Vanilla `fetch()` in `api.ts`, no axios or React Query
- All state in `App.tsx` via `useState`, no external state management
- Icons from `lucide-react`
- Fonts: Space Grotesk (headings), IBM Plex Sans (body)

## Project structure

```
src/
├── App.tsx              # Root component: all state, polling, handlers
├── api.ts               # Typed fetch wrappers for /api/v3 endpoints
├── types.ts             # TypeScript interfaces matching backend schemas
├── index.css            # Tailwind import + custom fonts
└── components/
    ├── ErrorBoundary.tsx     # Render error boundary with retry
    ├── Header.tsx           # Top nav, scan trigger, status
    ├── UploadPanel.tsx      # PDF drag-and-drop upload
    ├── PipelineStrip.tsx    # 3-phase pipeline visualization
    ├── StatsBar.tsx         # Rule/violation counters
    ├── RequestTimeline.tsx  # Live API request log
    ├── ReviewPanel.tsx      # Tabbed rule review
    ├── RuleCard.tsx         # Single rule with approve/reject
    ├── ViolationsPanel.tsx  # Violation list
    ├── ViolationCard.tsx    # Single violation with verdict reasoning/confidence
    ├── SeverityBadge.tsx    # CRITICAL/HIGH/MEDIUM/LOW badge
    └── SqlBlock.tsx         # SQL code display
```

## Commands

```bash
npm run dev       # Dev server on :3000
npm run build     # Type-check + production build
npm run lint      # ESLint
npm run preview   # Preview production build
```
