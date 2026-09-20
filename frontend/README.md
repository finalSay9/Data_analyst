# Frontend — AI Data Analyst Platform

Vite + React + Tailwind CSS v4, talking to the FastAPI backend built in Phase 1.

## Stack

- **Vite** — build tool / dev server
- **React 19** + **React Router** — pages: dataset list, upload, dataset detail/profile
- **Tailwind CSS v4** — via `@tailwindcss/vite` (no separate `tailwind.config.js` needed;
  theme tokens live in `src/index.css` under `@theme`)
- **lucide-react** — icons
- **axios** — API client

## Local setup

```bash
npm install
npm run dev
```

Runs on `http://localhost:5173`. API calls to `/api/*` are proxied to
`http://localhost:8000` (see `vite.config.js`) — **make sure the FastAPI
backend is running first** (`uvicorn app.main:app --reload` from `backend/`).

## Structure

```
src/
├── api/
│   └── datasets.js       # axios client wrapping backend endpoints
├── components/
│   ├── Layout.jsx          # sidebar nav + responsive shell
│   ├── DatasetCard.jsx
│   ├── ColumnProfileCard.jsx  # renders different stats per column type
│   ├── StatusBadge.jsx
│   ├── StatCard.jsx
│   ├── LoadingSpinner.jsx
│   └── ErrorMessage.jsx
├── pages/
│   ├── DatasetsPage.jsx       # list view, "/"
│   ├── UploadPage.jsx         # drag-and-drop upload, "/upload"
│   └── DatasetDetailPage.jsx  # overview + profile grid, "/datasets/:id"
├── hooks/
│   └── useApi.js            # fetch-on-mount + loading/error state
└── App.jsx                  # routes
```

## Design notes

- **Dev proxy over hardcoded URLs.** `vite.config.js` proxies `/api` to
  the backend, so the same relative paths work in dev and (once served
  behind a real reverse proxy) in production, with no env-var juggling
  for the base URL at this stage.
- **`useApi` hook** avoids repeating loading/error boilerplate in every
  page — deliberately small, not a data-fetching library. Worth
  swapping for React Query / TanStack Query later once caching,
  refetching, or optimistic updates actually matter.
- **Column profile rendering is type-driven.** `ColumnProfileCard`
  switches on `inferred_type` from the backend response to decide which
  stats to show (min/max/mean for numeric, top values for strings,
  true/false counts for booleans, earliest/latest for datetimes) —
  mirrors the same type-driven design used in the backend's profiling
  service.
