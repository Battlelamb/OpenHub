# OpenHub Command Center (web/)

React + Vite + TanStack Router + Tailwind v4 + shadcn/ui SPA that ships as part of the OpenHub FastAPI process. Served at `/dashboard` in production.

## Requirements

- Node.js 20.19+ (Vite requirement)
- npm 10+

## Development

```bash
cd web
npm install          # one-time
npm run dev          # Vite dev server on http://localhost:5173
```

In a second terminal, start the FastAPI backend on port 7788:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 7788 --reload
```

The Vite dev server proxies `/v1/*` HTTP and `/v1/ws/ui` WebSocket to `localhost:7788`, so cross-origin setup is not required.

## Testing

```bash
cd web
npm run test -- --run    # Vitest unit + integration tests
npm run typecheck        # TypeScript strict type check
npm run build            # Production build to web/dist/
```

The full gate is:

```bash
npm run test -- --run && npm run typecheck && npm run build
```

## Production Build

```bash
cd web
npm run build
```

This produces `web/dist/` with `index.html` + `assets/*`. FastAPI mounts this directory at `/dashboard` via `StaticFiles(html=True)` in `app/main.py` when the directory exists. SPA deep-link routes fall back to `index.html`.

Deploy flow on the VPS:

```bash
git pull
cd web && npm ci && npm run build
systemctl --user restart openhub.service
```

## Architecture Locked Decisions

See `.planning/phases/04-command-center-ui/04-CONTEXT.md` for the full D-01..D-16 decision set. Key points:

- **Stack (D-01, D-04, D-11, D-16):** React 19 + Vite + TS + Tailwind v4 + shadcn/ui + TanStack Router + TanStack Query + Zustand + react-hook-form + zod + i18next.
- **Theme (D-02):** Dark default with manual light toggle. Root `.dark` class.
- **Palette (D-03):** zinc base + emerald accent. See `.planning/phases/04-command-center-ui/04-UI-SPEC.md` for the full color map.
- **Auth (D-14):** JWT in-memory only (Zustand). Page refresh = re-login. No localStorage, no cookies written from JS.
- **Deployment (D-08):** Single port 7788. Frontend served as static assets by FastAPI. No separate node process in production.
- **Admin legacy (D-10):** `app/static/admin.html` stays at `/admin`. The React dashboard is at `/dashboard` side by side.

## Directory Layout

```
web/
  src/
    routes/              # TanStack Router file-based routes (auto-generated tree)
      __root.tsx
      login.tsx          # Public login page
      _authed.tsx        # Auth guard + AppShell wrapper
      _authed/
        agents/          # UI-02, UI-07
        tasks/           # UI-03, UI-04, UI-05, UI-12
        workflows/       # UI-06
        dlq.tsx          # UI-10
        costs.tsx        # UI-11
        memory.tsx       # UI-13
        locks.tsx        # UI-14
        health.tsx       # UI-08 detail page
        settings.tsx     # theme + language
    components/
      ui/                # shadcn primitives (button, input, dialog, ...)
      layout/            # AppShell, Sidebar, Topbar, ThemeProvider
      common/            # StatusBadge, ResponsiveList, JsonViewer, TraceTimeline
      forms/              # LoginForm, TaskCreateForm
    hooks/
      queries/            # TanStack Query wrappers per resource
      useWebSocketSync.ts # Hybrid WS merge + invalidate sync
    lib/
      api-client.ts       # fetch wrapper with RFC 7807 parsing
      query-keys.ts
      utils.ts            # shadcn cn() helper
    stores/
      auth-store.ts       # JWT in-memory only
      ui-store.ts         # theme / language / sidebar / wsStatus
    i18n/index.ts         # i18next init (TR + EN)
    locales/{en,tr}/*.json
    mocks/                # msw handlers for Vitest
    test/setup.ts
```
