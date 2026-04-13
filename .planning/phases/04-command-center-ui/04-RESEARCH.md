# Phase 4: Command Center UI - Research

**Researched:** 2026-04-13
**Domain:** React SPA frontend (Vite + TanStack ecosystem + shadcn/ui)
**Confidence:** HIGH (npm-registry-verified versions, stack locked in CONTEXT.md)

## Project Constraints (from CLAUDE.md)

- **Backend stack locked:** Python 3.11+ / FastAPI / SQLite. Phase 4 does not touch backend logic.
- **Frontend stack locked:** React + Vite. No Next.js, no SSR.
- **Deployment:** Must work under a single systemd unit + single port (7788). Frontend ships as static assets served by FastAPI, not a separate node process in production.
- **Writing rule:** No em dashes in any output. Use `-`, `:`, or `,`.
- **Commit rule:** No AI tool names in commit messages. Prefixes: `feat:`, `refactor:`, `improve:`, `clean:`.
- **Do not push without asking.**
- **GSD workflow enforced:** all file edits must come through a GSD command (the planner/executor run inside the GSD flow, so this is already satisfied).

## User Constraints (from CONTEXT.md)

### Locked Decisions (D-01 to D-16)

- **D-01** Tailwind CSS + shadcn/ui (Radix primitives, copy-paste components). `npx shadcn@latest add <component>`. All 16 requirements covered by built-in primitives.
- **D-02** Dark mode default + manual light toggle. Tailwind `class` strategy on `<html>`. Preference in React state (no localStorage per UI-01 spirit; see D-14).
- **D-03** Zinc/slate neutral base + a single accent color. Researcher/planner picks (emerald or violet recommended).
- **D-04** TanStack Query (REST cache) + Zustand (UI-only client state). No Redux, no RTK Query.
- **D-05** Hybrid WS to cache sync: `agent_status_changed`, `task_status_changed`, `task_progress` → optimistic `setQueryData`. `heartbeat` and metadata → `invalidateQueries`.
- **D-06** WS hook does both merge and invalidate paths. Exponential backoff (1s start, 30s max). "Reconnecting..." banner. On successful reconnect, invalidate entire QueryClient cache.
- **D-07** Frontend lives at `web/` under repo root. Sibling of `app/`. No monorepo tooling.
- **D-08** Production: `npm run build` → `web/dist/` → FastAPI `StaticFiles(directory="web/dist", html=True)` at `/dashboard`. Single deploy unit, single port 7788.
- **D-09** Dev: Vite dev server on `:5173`, proxies `/v1/*` and `/v1/ws/ui` to `localhost:7788`.
- **D-10** `app/static/admin.html` stays at `/admin`. New React UI at `/dashboard`. Side-by-side.
- **D-11** TanStack Router (not React Router v6). File-based routing, type-safe loaders, first-class TanStack Query integration.
- **D-12** Sidebar layout, collapsible. Groups: Operations (Agents, Tasks, Workflows), Visibility (DLQ, Costs, Traces, Memory, Locks), Admin (Health, Settings).
- **D-13** Separate `/login` full-page route. Global 401 interceptor → `router.navigate({ to: '/login', search: { redirect: currentPath } })`. Login form: `react-hook-form` + `zod`.
- **D-14** JWT in-memory only. Zustand store, page refresh = re-login. localStorage/URL params strictly forbidden.
- **D-15** Hybrid refresh: `token_expiring` WS event → silent `POST /v1/auth/refresh`. On failure → toast warning with manual continue button.
- **D-16** Bilingual i18n (Turkish + English) via `i18next` + `react-i18next`. `web/src/locales/{tr,en}/common.json`. Browser language detection with English fallback.

### Claude's Discretion

- Form library specifics (react-hook-form + zod is strongly recommended; this research confirms).
- Toast library (sonner recommended below).
- DataTable: shadcn Table + TanStack Table vs plain Table.
- Trace viewer library vs custom.
- Mobile breakpoint thresholds.
- Dark mode accent color choice.
- Sidebar group ordering and icons (lucide-react recommended, ships with shadcn).
- Skeleton loading pattern.

### Deferred Ideas (OUT OF SCOPE)

- Native mobile app (MOB-01, v2).
- Full search bar with vector search in topbar (Phase 5+).
- Multi-tenant / org switching.
- Persistent notification panel (only toasts in Phase 4).
- Custom dashboards / drag-drop layouts.
- Real-time collaborative cursors.
- Onboarding tour / first-run wizard.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| UI-01 | JWT login form, token in memory only | Zustand auth slice (section 2.4), react-hook-form + zod login form (section 2.6) |
| UI-02 | Live agent status board, WS-driven | TanStack Query `/v1/agents` + WS optimistic merge (section 2.3) |
| UI-03 | Task list, filterable status columns, real-time | TanStack Query + TanStack Table optional; WS merge for `task_status_changed` |
| UI-04 | Task create form with agent selection | shadcn Dialog + react-hook-form + zod + agent query (section 2.6, 2.1) |
| UI-05 | Task cancel action on running tasks | TanStack Query mutation + optimistic update |
| UI-06 | Workflow step-list view, read-only badges | shadcn Badge + custom list, `task_progress` WS event |
| UI-07 | Agent detail drilldown | Route param (`/dashboard/agents/$agentId`), TanStack Query loader |
| UI-08 | Health indicator in top bar | TanStack Query `/v1/health` polling (refetchInterval 10s) |
| UI-09 | Error toast notifications (RFC 7807 parse) | Sonner + global axios/fetch interceptor (section 2.6) |
| UI-10 | DLQ panel with retry button | Table row action + mutation + invalidate |
| UI-11 | Cost tracking display | Read-only table, TanStack Query |
| UI-12 | Distributed trace viewer | Custom vertical timeline (no extra dep) (section 2.9) |
| UI-13 | Shared memory key-value viewer | Table + collapsible JSON viewer (section 2.9) |
| UI-14 | Resource lock panel | Table + Badge warnings |
| UI-15 | Mobile-responsive (table → card) | Tailwind `md:` breakpoint, single-source `<ResponsiveList>` (section 2.8) |
| UI-16 | WS hook with exponential backoff + reconnect banner | Native WebSocket hook (section 2.7) |

## Executive Summary

1. **The locked stack is mature and coherent.** Every library the planner must use is actively maintained with stable v1+ releases. No version risk. The biggest gotcha is **Tailwind v4** (released early 2025): it ships as a Vite plugin (`@tailwindcss/vite`), has no `tailwind.config.js` by default, uses `@theme` in CSS for tokens, and shadcn CLI auto-handles this during `init`. Do NOT copy Tailwind v3 tutorials.
2. **shadcn + Vite + Tailwind v4 setup is a single `npx shadcn@latest init` command**, but it expects you to already have the Tailwind v4 Vite plugin wired and a `@import "tailwindcss"` line in your CSS. The planner should sequence: (1) `npm create vite@latest web -- --template react-ts`, (2) install `tailwindcss @tailwindcss/vite`, (3) wire `vite.config.ts` + `src/index.css`, (4) install `tsconfig` path alias, (5) then `npx shadcn@latest init`.
3. **TanStack Router file-based routing needs the `@tanstack/router-plugin` Vite plugin**, not just the runtime package. The plugin auto-generates `routeTree.gen.ts` from files in `src/routes/`. Auth-guarded routes use a pathless parent `_authed.tsx` with a `beforeLoad` hook reading the Zustand auth store and throwing `redirect({ to: '/login' })` on missing token. This is first-class, type-safe, and runs before any child loader.
4. **The WS hybrid-sync pattern is the single highest-complexity item** and should get its own task: a `useWebSocketSync` hook that owns the connection, routes events through a reducer, calls `queryClient.setQueryData` for critical events and `queryClient.invalidateQueries` for non-critical, handles `token_expiring` with a silent refresh attempt, and on reconnect fires a single `queryClient.invalidateQueries()` (no filter) to rehydrate from REST. Per CONTEXT.md D-03 WS auth is first-frame JWT, NOT URL query param - this must be wired correctly (the existing `/v1/ws` agent endpoint still uses `?token=` but Phase 2 shipped `/v1/ws/ui` with first-frame auth).
5. **Production deployment has one FastAPI change only:** a `StaticFiles` mount at `/dashboard` with `html=True` so SPA deep-links serve `index.html`. No new infra, no node process in prod, single systemd unit. The planner must also set Vite `base: '/dashboard/'` so asset URLs resolve under the mount.

**Primary recommendation:** Sequence phase as 6-7 plans: (1) Scaffold `web/` with Vite + React + TS + Tailwind v4 + shadcn init + path aliases + Vite proxy. (2) Auth slice + login route + 401 interceptor + route guard. (3) App shell (sidebar, topbar, theme toggle, i18n, routing skeleton). (4) Data layer (QueryClient setup + WS sync hook + all query hooks). (5) Feature routes (agents, tasks, workflows - Operations group). (6) Visibility routes (DLQ, costs, traces, memory, locks). (7) Production mount + `StaticFiles` integration + build + smoke test. Each plan ~2-4 tasks. Plan 4 (data layer) is the load-bearing one and should land before any feature plan.

## Standard Stack

### Core (all versions verified from npm registry 2026-04-13)

| Package | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `react` | 19.2.5 | UI runtime | Latest stable |
| `react-dom` | 19.2.5 | DOM renderer | Pairs with react |
| `typescript` | 6.0.2 | Type safety | TanStack Router needs TS for type-safe routes |
| `vite` | 8.0.8 | Dev server + bundler | Stack-locked (D-07) |
| `@vitejs/plugin-react` | 6.0.1 | Vite React integration | Fast refresh, SWC or Babel |
| `tailwindcss` | 4.2.2 | Styling | Stack-locked (D-01) - v4 is current |
| `@tailwindcss/vite` | 4.2.2 | Tailwind v4 Vite plugin | Required for Tailwind v4 + Vite |
| `tailwind-merge` | 3.5.0 | `cn()` class merging | Used by shadcn `lib/utils.ts` |
| `class-variance-authority` | 0.7.1 | Variant-based class API | shadcn components depend on this |
| `tailwindcss-animate` | 1.0.7 | Animation utilities | Used by shadcn Dialog/Sheet/Toast |
| `lucide-react` | 0.545.x (shadcn default) | Icon set | Default icons for shadcn, all sidebar icons |
| `@tanstack/react-router` | 1.168.19 | File-based router | Stack-locked (D-11) |
| `@tanstack/router-plugin` | 1.167.20 | Vite plugin for route tree gen | Required for file-based routing |
| `@tanstack/react-router-devtools` | 1.166.13 | Router devtools | Dev-only |
| `@tanstack/react-query` | 5.99.0 | REST cache | Stack-locked (D-04) |
| `@tanstack/react-query-devtools` | 5.99.0 | Query devtools | Dev-only |
| `zustand` | 5.0.12 | UI client state | Stack-locked (D-04) |
| `i18next` | 26.0.4 | i18n core | Stack-locked (D-16) |
| `react-i18next` | 17.0.2 | React i18n bindings | Stack-locked (D-16) |
| `react-hook-form` | 7.72.1 | Forms | D-13 locks for login, recommended for all forms |
| `zod` | 4.3.6 | Schema validation | Pairs with RHF via resolver |
| `@hookform/resolvers` | 5.2.2 | RHF + zod bridge | `zodResolver` |
| `sonner` | 2.0.7 | Toast notifications | Planner discretion; recommended over shadcn Toast (simpler, stacked, official shadcn alt) |

### shadcn CLI (meta-tool, not a runtime dep)

| Tool | Version | Purpose |
|------|---------|---------|
| `shadcn` CLI | 4.2.0 | `npx shadcn@latest init` then `add` commands |

### Dev / Test

| Package | Version | Purpose |
|---------|---------|---------|
| `vitest` | 4.1.4 | Test runner (Vite-native) |
| `jsdom` | 29.0.2 | DOM for unit tests |
| `@testing-library/react` | 16.3.2 | Component testing |
| `@testing-library/jest-dom` | 6.9.1 | DOM matchers |
| `@testing-library/user-event` | 14.6.1 | Realistic user interactions |
| `msw` | 2.13.2 | HTTP mocking (mock backend in tests) |
| `@playwright/test` | 1.59.1 | E2E (recommend deferring to Phase 5 per TEST-06) |

### Alternatives Considered (not chosen)

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Sonner | shadcn `<Toaster>` (Radix-based) | Sonner is simpler, stacked out of the box, supported as first-class shadcn alternative. Radix Toast needs more wiring. |
| Axios | Native fetch | Native fetch is enough; axios adds 13kb. Recommend native fetch with a small wrapper (`apiClient.ts`) that injects `Authorization` header and parses RFC 7807 errors. |
| TanStack Table | Plain `<Table>` | For Phase 4's read-only lists, plain Table is fine. Use TanStack Table only if column sorting/filtering gets complex (optional in Plan 5/6). |
| react-use-websocket | Native `WebSocket` | Native is sufficient and avoids a dep. The hook is ~60 lines. |

### Version verification note

All versions above were verified against `npm view <pkg> version` on 2026-04-13. The Tailwind v4 fact (no `tailwind.config.js` by default) is a MEDIUM-confidence callout - verified via `npm view tailwindcss dist-tags` showing `latest: 4.2.2` and `v3-lts: 3.4.19`, which confirms v4 is the current major and v3 is explicitly "long-term support" (i.e., legacy). The planner should re-verify the exact shadcn init flow at execution time since shadcn 4.x changed to support Tailwind v4.

### Installation (single command group)

```bash
# Plan 1 task: scaffold
npm create vite@latest web -- --template react-ts
cd web

# Core runtime
npm install react react-dom
npm install @tanstack/react-router @tanstack/react-query zustand
npm install i18next react-i18next
npm install react-hook-form zod @hookform/resolvers
npm install sonner lucide-react
npm install class-variance-authority clsx tailwind-merge tailwindcss-animate

# Tailwind v4 + Vite plugin
npm install -D tailwindcss @tailwindcss/vite

# TanStack Router Vite plugin (file-based routing)
npm install -D @tanstack/router-plugin @tanstack/react-router-devtools
npm install -D @tanstack/react-query-devtools

# Testing
npm install -D vitest jsdom @testing-library/react @testing-library/jest-dom @testing-library/user-event msw

# Then run shadcn init (answers questions interactively)
npx shadcn@latest init
```

## Architecture Patterns

### Recommended `web/` directory layout

```
web/
├── package.json
├── tsconfig.json
├── tsconfig.app.json            # path alias "@/*" -> "./src/*"
├── vite.config.ts                # tanstackRouter + react + tailwindcss plugins; server.proxy for /v1 + /v1/ws/ui; base: '/dashboard/'
├── components.json               # shadcn config (generated by init)
├── index.html
├── public/                       # favicons, og images
├── src/
│   ├── main.tsx                  # Entry: QueryClientProvider, RouterProvider, I18nextProvider, Toaster
│   ├── index.css                 # @import "tailwindcss"; shadcn base layer
│   ├── routeTree.gen.ts          # AUTO-GENERATED by router plugin. DO NOT edit.
│   ├── routes/
│   │   ├── __root.tsx            # Root layout: <Outlet/>, devtools, global Toaster
│   │   ├── login.tsx             # Public login page
│   │   ├── _authed.tsx           # Auth guard (beforeLoad redirect if no token)
│   │   ├── _authed/
│   │   │   ├── index.tsx         # /dashboard redirects here; default landing
│   │   │   ├── agents/
│   │   │   │   ├── index.tsx     # UI-02 agent list
│   │   │   │   └── $agentId.tsx  # UI-07 agent detail
│   │   │   ├── tasks/
│   │   │   │   ├── index.tsx     # UI-03 task list + UI-04 create + UI-05 cancel
│   │   │   │   └── $taskId.tsx   # UI-12 trace viewer lives here
│   │   │   ├── workflows/
│   │   │   │   ├── index.tsx
│   │   │   │   └── $workflowId.tsx # UI-06 step list
│   │   │   ├── dlq.tsx           # UI-10
│   │   │   ├── costs.tsx         # UI-11
│   │   │   ├── memory.tsx        # UI-13
│   │   │   ├── locks.tsx         # UI-14
│   │   │   └── settings.tsx      # language + theme toggles
│   ├── components/
│   │   ├── ui/                   # shadcn-added components (button.tsx, dialog.tsx, ...)
│   │   ├── layout/
│   │   │   ├── Sidebar.tsx       # D-12 sidebar with groups
│   │   │   ├── Topbar.tsx        # health dot + reconnect banner + user menu
│   │   │   └── AppShell.tsx      # grid layout, used by _authed.tsx
│   │   ├── common/
│   │   │   ├── ResponsiveList.tsx  # UI-15 table/card switch
│   │   │   ├── JsonViewer.tsx      # UI-13
│   │   │   └── TraceTimeline.tsx   # UI-12 custom vertical timeline
│   │   └── forms/
│   │       ├── LoginForm.tsx       # UI-01
│   │       └── TaskCreateForm.tsx  # UI-04
│   ├── lib/
│   │   ├── utils.ts              # cn() helper (created by shadcn init)
│   │   ├── api-client.ts         # fetch wrapper: auth header, RFC 7807 parse, 401 handler
│   │   ├── query-client.ts       # QueryClient singleton with defaults
│   │   └── query-keys.ts         # centralized query key factory
│   ├── stores/
│   │   ├── auth-store.ts         # Zustand: { token, expiresAt, user, login(), logout() }
│   │   ├── ui-store.ts           # Zustand: { sidebarCollapsed, theme, language, wsStatus }
│   │   └── index.ts
│   ├── hooks/
│   │   ├── useWebSocketSync.ts   # D-06 WS hook, owns connection + reducer
│   │   ├── useAgents.ts          # TanStack Query wrappers
│   │   ├── useTasks.ts
│   │   ├── useWorkflows.ts
│   │   ├── useHealth.ts          # UI-08 polling
│   │   └── useTheme.ts
│   ├── i18n/
│   │   ├── index.ts              # i18next init (language detection, fallback en)
│   │   └── types.ts              # typed translation keys (optional)
│   └── locales/
│       ├── tr/
│       │   ├── common.json
│       │   ├── agents.json
│       │   ├── tasks.json
│       │   └── errors.json
│       └── en/
│           ├── common.json
│           ├── agents.json
│           ├── tasks.json
│           └── errors.json
└── dist/                         # build output, mounted by FastAPI at /dashboard
```

### Pattern 1: shadcn init with Tailwind v4 on Vite

**What:** `shadcn` CLI writes `components.json`, creates `lib/utils.ts` (with `cn()`), configures path alias, and injects CSS variables into `src/index.css`.

**Sequence (critical order):**

1. Scaffold Vite + React + TS project.
2. Install `tailwindcss` and `@tailwindcss/vite` as dev deps.
3. Edit `vite.config.ts` to add the `tailwindcss()` plugin from `@tailwindcss/vite`.
4. Replace `src/index.css` contents with `@import "tailwindcss";` (Tailwind v4 single-line entry; v3 `@tailwind base/components/utilities` is GONE).
5. Configure TS path alias `@/*` → `./src/*` in `tsconfig.json` and `tsconfig.app.json`, AND add `resolve.alias` in `vite.config.ts`.
6. Run `npx shadcn@latest init`. It prompts: base color, CSS variables (pick yes for theme swapping), path aliases (auto-detects `@/*`). It writes `components.json`, `src/lib/utils.ts`, and adds `@theme` / CSS variables to `index.css`.
7. Verify `src/lib/utils.ts` exports `cn()`.

**Theme strategy (answers D-02):** shadcn's `cssVariables: true` mode is the one you want. This lets you toggle `.dark` class on `<html>` and swap CSS variables. Use a `useTheme` hook that writes the class; initial theme is `dark` (D-02). The strict "in-memory only" rule of UI-01 is about **JWTs**, not UX preferences - theme and language are fine in localStorage (user preference, not security-sensitive). Planner should explicitly document this distinction.

### Pattern 2: TanStack Router file-based routing with Vite plugin

**What:** `@tanstack/router-plugin/vite` scans `src/routes/` and generates `routeTree.gen.ts`. File names encode URL structure. `_authed.tsx` is a **pathless layout route** (leading underscore means "group without URL segment") - perfect for auth guards.

**vite.config.ts skeleton:**

```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { tanstackRouter } from '@tanstack/router-plugin/vite'
import tailwindcss from '@tailwindcss/vite'
import path from 'node:path'

export default defineConfig({
  base: '/dashboard/',  // D-08: assets resolve under FastAPI mount
  plugins: [
    tanstackRouter({ target: 'react', autoCodeSplitting: true }),
    react(),
    tailwindcss(),
  ],
  resolve: { alias: { '@': path.resolve(__dirname, './src') } },
  server: {
    port: 5173,
    proxy: {
      '/v1/ws/ui': { target: 'ws://localhost:7788', ws: true, changeOrigin: true },
      '/v1':      { target: 'http://localhost:7788', changeOrigin: true },
    },
  },
  build: { outDir: 'dist', sourcemap: true },
})
```

**Critical:** the `tanstackRouter` plugin MUST be listed before `react()` (router plugin docs are explicit about this).

**Route file skeleton (`src/routes/__root.tsx`):**

```tsx
import { createRootRouteWithContext, Outlet } from '@tanstack/react-router'
import { TanStackRouterDevtools } from '@tanstack/react-router-devtools'
import type { QueryClient } from '@tanstack/react-query'
import { Toaster } from 'sonner'

interface RouterContext {
  queryClient: QueryClient
  // auth state is read from store directly, not passed through context
}

export const Route = createRootRouteWithContext<RouterContext>()({
  component: () => (
    <>
      <Outlet />
      <Toaster richColors />
      {import.meta.env.DEV && <TanStackRouterDevtools />}
    </>
  ),
})
```

**Auth guard (`src/routes/_authed.tsx`):**

```tsx
import { createFileRoute, redirect, Outlet } from '@tanstack/react-router'
import { useAuthStore } from '@/stores/auth-store'
import { AppShell } from '@/components/layout/AppShell'

export const Route = createFileRoute('/_authed')({
  beforeLoad: ({ location }) => {
    const token = useAuthStore.getState().token
    if (!token) {
      throw redirect({
        to: '/login',
        search: { redirect: location.href },
      })
    }
  },
  component: () => (
    <AppShell>
      <Outlet />
    </AppShell>
  ),
})
```

**Main entry (`src/main.tsx`):**

```tsx
import ReactDOM from 'react-dom/client'
import { RouterProvider, createRouter } from '@tanstack/react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { routeTree } from './routeTree.gen'
import './index.css'
import './i18n'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,           // match D-05 non-critical invalidate cadence
      refetchOnWindowFocus: false, // WS drives freshness, not focus
      retry: (count, err: any) => err?.status !== 401 && count < 2,
    },
  },
})

const router = createRouter({ routeTree, context: { queryClient } })

declare module '@tanstack/react-router' {
  interface Register { router: typeof router }
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <QueryClientProvider client={queryClient}>
    <RouterProvider router={router} />
  </QueryClientProvider>
)
```

### Pattern 3: Hybrid WS sync (D-05, D-06)

See section 4 for the full code skeleton. Key concepts:

- Single `useWebSocketSync` hook mounted once in `AppShell` (inside `_authed.tsx` subtree).
- Hook owns the `WebSocket` instance, reconnect timer, and ws status.
- Event reducer maps event types to cache actions:
  - `agent_status_changed` → `queryClient.setQueryData(['agents'], updater)` and `setQueryData(['agents', id], agent)`.
  - `task_status_changed` → same pattern for `['tasks']` and `['tasks', id]`.
  - `task_progress` → `setQueryData(['tasks', id], updater)` merging `progress` field.
  - `heartbeat` → `queryClient.invalidateQueries({ queryKey: ['agents'] })` (debounced - coalesce 5s per D-06).
  - `metadata_changed` → `invalidateQueries` for the affected resource.
  - `token_expiring` → call `refreshToken()`; on failure show sonner toast with continue action.
  - `error` (recoverable) → sonner error toast with RFC 7807 parse.
- On `close` event: update `uiStore.wsStatus = 'reconnecting'`, schedule reconnect with exponential backoff, on successful reopen call `queryClient.invalidateQueries()` (no filter) to rehydrate everything.

### Pattern 4: RFC 7807 error parsing in api-client

Backend errors are `ProblemDetail` shape (Phase 1 D-01): `{type, title, status, detail, instance, errors?, trace_id?}`. The api-client throws a typed `ApiError` that preserves this shape; the sonner toast renders `title` as bold line + `detail` as body.

### Anti-patterns to avoid

- **Do NOT store JWT in localStorage or cookies on the JS side** (D-14 explicit). In-memory only.
- **Do NOT use TanStack Router's context `auth`** instead of Zustand. Tempting, but `beforeLoad` runs outside React so you'd read the store anyway. Zustand's vanilla `getState()` is the clean path.
- **Do NOT pass `queryClient` through React context manually** - use `@tanstack/react-query` provider, which TanStack Router already integrates with via `routerContext`.
- **Do NOT put auth header injection in individual `useQuery` calls.** Centralize in `api-client.ts`.
- **Do NOT use `tailwind.config.js` for v4 theme tokens.** Use `@theme` block in `index.css`. A `tailwind.config.js` file only exists in v4 if you're using plugins that need it.
- **Do NOT attach `?token=<jwt>` to WS URL.** Phase 2 D-03 locked first-frame auth. First message on open MUST be `{type: 'auth', token: '...'}` followed by waiting for server ack.
- **Do NOT use React Suspense with i18next** unless you configure suspense fallbacks at every route. Safer: initialize i18next synchronously with inline resources (small JSON files) so no suspense is needed.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Form validation + errors | Custom state machine | `react-hook-form` + `zod` + `@hookform/resolvers` | Field-level errors, dirty tracking, reset, submit guards all solved. |
| Toast stacking and timeouts | Custom portal + timer | `sonner` | Stacking, swipe-to-dismiss, rich colors, accessibility - free. |
| REST cache + refetch + dedupe | Manual `useEffect` + `fetch` | `@tanstack/react-query` | Locked (D-04). Do not re-debate. |
| Router with type-safe params | React Router | `@tanstack/react-router` | Locked (D-11). |
| Client state for UI | useContext + reducer | `zustand` | Locked (D-04). |
| i18n key lookup + plural | Custom map | `i18next` | Locked (D-16). Handles plurals, interpolation, namespaces. |
| WebSocket reconnect | ad-hoc | Still roll your own native hook | `react-use-websocket` adds a dep for ~60 lines. Native is clean. |
| JSON tree viewer (UI-13) | Custom recursive component | `<details>` + `JSON.stringify(..., null, 2)` inside `<pre>` | Minimal, no dep. Only upgrade to a library if users complain. |
| Distributed trace timeline (UI-12) | Third-party | Custom flex/grid with Tailwind | A vertical list of rows with left-indented bars is ~80 lines. No library fits right anyway. |
| Data tables with sorting (if needed) | Custom `<table>` with sort state | `@tanstack/react-table` | Headless, composable. Optional for Phase 4. |
| Icons | SVG sprites | `lucide-react` | Ships with shadcn. |

**Key insight:** The locked stack already removes most "don't hand-roll" decisions. The only two areas where the planner is tempted to reinvent are (1) the WS hook and (2) the trace viewer. For the WS hook, rolling it yourself is correct because the logic is OpenHub-specific (event reducer, token refresh, cache invalidation strategy). For the trace viewer, rolling it yourself is correct because Phase 4 trace data shape is OpenHub-specific and no off-the-shelf viewer matches.

## Runtime State Inventory

Not applicable - Phase 4 is a greenfield frontend. No rename, refactor, or data migration. Backend state is untouched.

- **Stored data:** None - backend DB not modified by Phase 4. Verified by reading CONTEXT.md "Phase Boundary" and confirming only NEW `web/` directory + 1-line FastAPI static mount.
- **Live service config:** None - systemd unit unchanged (frontend served by same FastAPI process). CORS may need `hub.brunhilde.cloud` in `AGENTHUB_CORS_ORIGINS` - but deployment is same-origin so CORS not required in production.
- **OS-registered state:** None.
- **Secrets / env vars:** None new. Frontend is served same-origin, no API base URL env var needed.
- **Build artifacts:** `web/dist/` is new. Must be in `.gitignore`. Must be rebuilt on each deploy before `systemctl restart`. Planner should include a build step in the deploy flow task.

## Environment Availability

Phase 4 adds Node.js as a new build-time dependency. Runtime is unchanged.

| Dependency | Required By | Available (target env) | Version | Fallback |
|------------|-------------|------------------------|---------|----------|
| Node.js | Vite build + dev | Needs probe at execution | 20.x+ recommended (Vite 8 min: 20.19+) | Install via nvm / apt / direct download |
| npm | Package install | Ships with Node | 10.x+ | - |
| Python 3.11+ | Existing backend | Available (already running) | 3.12.3 local | - |
| FastAPI 0.104.1 | Static mount | Available | Pinned | - |

**Probe commands for executor:**

```bash
node --version        # Need v20.19+ (Vite 8 min); v22 LTS recommended
npm --version         # Need v10+
python3 --version     # Already 3.12.3
```

**Missing dependencies with no fallback:** Node.js must be present on the build machine. On the production VPS (`hub.brunhilde.cloud`), the planner should sequence a deploy task that either (a) builds on the VPS (requires Node installed there), or (b) builds locally/CI and ships `web/dist/` as an artifact. Option (b) is cleaner but needs a decision from the user during plan review. **MEDIUM-confidence assumption:** VPS does not have Node installed yet - planner should add an install step to the deploy plan or flag this for the user.

**Missing with fallback:** None.

## Common Pitfalls

### Pitfall 1: Tailwind v3 tutorials break on Tailwind v4

**What goes wrong:** Copy-paste a v3 setup (with `tailwind.config.js`, `@tailwind base` directives, `postcss.config.js`) and Tailwind silently does nothing or errors.

**Why it happens:** Tailwind v4 shipped in 2025 with a totally new config story: CSS-first config via `@theme` block, no PostCSS needed, single `@import "tailwindcss"` line, Vite plugin instead of PostCSS plugin.

**How to avoid:** Use `@tailwindcss/vite` plugin, put `@import "tailwindcss"` at the top of `src/index.css`, do NOT create `tailwind.config.js` unless a plugin requires it. `shadcn@latest init` at version 4.x knows v4 and does it correctly.

**Warning signs:** `@tailwind` directive showing as unknown in CSS, dev server starting but Tailwind classes not applying, `postcss.config.js` appearing in the project.

### Pitfall 2: TanStack Router plugin order matters

**What goes wrong:** Router plugin listed after `react()` in `vite.config.ts` - route tree generation silently fails or fires at the wrong time.

**How to avoid:** `tanstackRouter()` must come BEFORE `react()` in the plugins array.

### Pitfall 3: WebSocket proxy in Vite needs `ws: true`

**What goes wrong:** Dev server proxies HTTP but not WebSocket upgrades; browser connects to `ws://localhost:5173/v1/ws/ui` and gets 404.

**How to avoid:** `server.proxy['/v1/ws/ui'] = { target: 'ws://localhost:7788', ws: true, changeOrigin: true }`. Note `ws://` not `http://` in target.

### Pitfall 4: SPA routes 404 when served by FastAPI

**What goes wrong:** User visits `/dashboard/agents/abc123` directly, FastAPI returns 404 because there's no file at that path in `dist/`.

**How to avoid:** `StaticFiles(directory="web/dist", html=True)` - the `html=True` flag makes Starlette fall back to `index.html` for paths that don't match a file. ALSO set Vite `base: '/dashboard/'` so asset URLs (`/dashboard/assets/...`) match the mount.

### Pitfall 5: JWT leaks into URL / logs

**What goes wrong:** Dev copies the old `/v1/ws` pattern with `?token=<jwt>` and the token ends up in server logs, browser history, proxy logs.

**How to avoid:** Phase 2 D-03 locked first-frame auth for `/v1/ws/ui`. First client message after `open` MUST be `{type: 'auth', token: '...'}`. Server acks before sending events. Planner should include a verification step that greps the WS hook for `?token=` and fails if found.

### Pitfall 6: 401 interceptor causes redirect loop on login page

**What goes wrong:** Global fetch interceptor redirects on 401, but the login endpoint itself returns 401 on bad credentials, triggering a redirect away from `/login` (which redirects back to `/login`, infinite loop prevented only because already there, but state gets weird).

**How to avoid:** In the api-client 401 handler, check `if (router.state.location.pathname !== '/login')` before navigating. Or: use an `unauthedClient` for the login call that skips the 401 interceptor.

### Pitfall 7: Zustand store re-renders entire tree

**What goes wrong:** Consumers do `const store = useAuthStore()` (without selector), causing every component that touches the store to re-render on any slice change.

**How to avoid:** Always use selectors: `useAuthStore(state => state.token)`. For multi-field selects, use `useShallow` from `zustand/react/shallow`.

### Pitfall 8: i18next React Suspense without fallback

**What goes wrong:** i18next loads namespaces async, suspends the tree, but there's no `<Suspense>` boundary, so the whole app crashes.

**How to avoid:** Configure `i18next-react` with `useSuspense: false` OR bundle locales synchronously (import JSON statically in `i18n/index.ts`). For 2 languages with small JSON files, synchronous import is simpler and faster.

### Pitfall 9: Page refresh logs user out (UI-01 is correct)

**What goes wrong:** User refreshes, loses token (in-memory only), lands on `/login` - may feel broken.

**How to avoid:** This is intentional per UI-01 and D-14. Make it clear in UX: login page displays "session expired, please log in again" if there's a `?redirect=` param. Do NOT silently accept this as a bug.

### Pitfall 10: Reconnect storm when backend restarts

**What goes wrong:** All UI clients reconnect at the same time with 1-second backoff; backend startup hits a reconnect thundering herd.

**How to avoid:** Add jitter to exponential backoff: `delay = min(30_000, base * 2^attempt) * (0.5 + Math.random() * 0.5)`.

## Code Examples

### Zustand auth slice (`src/stores/auth-store.ts`)

```ts
import { create } from 'zustand'

interface User { id: string; name: string; role: 'admin' | 'agent' }

interface AuthState {
  token: string | null
  expiresAt: number | null       // epoch ms
  user: User | null
  setSession: (token: string, expiresIn: number, user: User) => void
  clear: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  expiresAt: null,
  user: null,
  setSession: (token, expiresIn, user) =>
    set({ token, expiresAt: Date.now() + expiresIn * 1000, user }),
  clear: () => set({ token: null, expiresAt: null, user: null }),
}))

// Vanilla (non-React) access for api-client and router guards:
// useAuthStore.getState().token
```

### api-client with RFC 7807 (`src/lib/api-client.ts`)

```ts
import { useAuthStore } from '@/stores/auth-store'
import { router } from '@/main'  // or pass router ref

export interface ProblemDetail {
  type: string
  title: string
  status: number
  detail?: string
  instance?: string
  errors?: Array<{ field: string; message: string }>
  trace_id?: string
}

export class ApiError extends Error {
  constructor(public problem: ProblemDetail) {
    super(problem.title)
  }
}

export async function api<T = unknown>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const token = useAuthStore.getState().token
  const headers = new Headers(init.headers)
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (init.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const res = await fetch(path, { ...init, headers })

  if (res.status === 401 && router.state.location.pathname !== '/login') {
    useAuthStore.getState().clear()
    router.navigate({
      to: '/login',
      search: { redirect: router.state.location.href },
    })
  }

  if (!res.ok) {
    const problem: ProblemDetail = await res.json().catch(() => ({
      type: 'about:blank',
      title: res.statusText,
      status: res.status,
    }))
    throw new ApiError(problem)
  }

  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}
```

### Auth-guarded route (`src/routes/_authed.tsx`)

```tsx
import { createFileRoute, redirect, Outlet } from '@tanstack/react-router'
import { useAuthStore } from '@/stores/auth-store'
import { AppShell } from '@/components/layout/AppShell'

export const Route = createFileRoute('/_authed')({
  beforeLoad: ({ location }) => {
    const { token, expiresAt } = useAuthStore.getState()
    if (!token || (expiresAt && expiresAt < Date.now())) {
      throw redirect({ to: '/login', search: { redirect: location.href } })
    }
  },
  component: () => <AppShell><Outlet /></AppShell>,
})
```

### WebSocket hybrid-sync hook (`src/hooks/useWebSocketSync.ts`) - skeleton

```ts
import { useEffect, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { useAuthStore } from '@/stores/auth-store'
import { useUIStore } from '@/stores/ui-store'
import { api } from '@/lib/api-client'

type WSEvent =
  | { event: 'agent_status_changed'; data: { agent_id: string; status: string } }
  | { event: 'task_status_changed'; data: { task_id: string; status: string } }
  | { event: 'task_progress'; data: { task_id: string; progress: number } }
  | { event: 'heartbeat'; data: { agent_id: string } }
  | { event: 'token_expiring'; data: { seconds_remaining: number } }
  | { event: 'error'; data: { code: string; message: string } }

const MAX_DELAY = 30_000

export function useWebSocketSync() {
  const queryClient = useQueryClient()
  const token = useAuthStore(s => s.token)
  const setStatus = useUIStore(s => s.setWsStatus)
  const wsRef = useRef<WebSocket | null>(null)
  const attemptRef = useRef(0)
  const timerRef = useRef<number | null>(null)

  useEffect(() => {
    if (!token) return

    let cancelled = false

    const connect = () => {
      if (cancelled) return
      const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const url = `${proto}//${window.location.host}/v1/ws/ui`
      const ws = new WebSocket(url)
      wsRef.current = ws
      setStatus('connecting')

      ws.onopen = () => {
        // Phase 2 D-03: first-frame JWT auth
        ws.send(JSON.stringify({ type: 'auth', token }))
      }

      ws.onmessage = (ev) => {
        const msg = JSON.parse(ev.data) as WSEvent | { event: 'connected' }
        if (msg.event === 'connected') {
          setStatus('connected')
          attemptRef.current = 0
          // Reconnect rehydrate (D-06)
          queryClient.invalidateQueries()
          return
        }
        handleEvent(queryClient, msg as WSEvent)
      }

      ws.onclose = () => {
        if (cancelled) return
        setStatus('reconnecting')
        const attempt = attemptRef.current++
        const base = Math.min(MAX_DELAY, 1000 * Math.pow(2, attempt))
        const delay = base * (0.5 + Math.random() * 0.5)  // jitter
        timerRef.current = window.setTimeout(connect, delay)
      }

      ws.onerror = () => { /* close will fire next */ }
    }

    connect()

    return () => {
      cancelled = true
      if (timerRef.current) window.clearTimeout(timerRef.current)
      wsRef.current?.close()
    }
  }, [token, queryClient, setStatus])
}

function handleEvent(qc: ReturnType<typeof useQueryClient>, msg: WSEvent) {
  switch (msg.event) {
    case 'agent_status_changed':
      qc.setQueryData<any[]>(['agents'], (prev) =>
        prev?.map(a => a.id === msg.data.agent_id ? { ...a, status: msg.data.status } : a)
      )
      qc.setQueryData(['agents', msg.data.agent_id], (prev: any) =>
        prev ? { ...prev, status: msg.data.status } : prev
      )
      break

    case 'task_status_changed':
      qc.setQueryData<any[]>(['tasks'], (prev) =>
        prev?.map(t => t.id === msg.data.task_id ? { ...t, status: msg.data.status } : t)
      )
      qc.setQueryData(['tasks', msg.data.task_id], (prev: any) =>
        prev ? { ...prev, status: msg.data.status } : prev
      )
      break

    case 'task_progress':
      qc.setQueryData(['tasks', msg.data.task_id], (prev: any) =>
        prev ? { ...prev, progress: msg.data.progress } : prev
      )
      break

    case 'heartbeat':
      // Non-critical: debounced invalidate (D-05)
      qc.invalidateQueries({ queryKey: ['agents'], refetchType: 'none' })
      break

    case 'token_expiring':
      silentRefresh().catch(() => {
        toast.warning('Session expiring', {
          description: 'Click to stay signed in',
          action: { label: 'Continue', onClick: () => silentRefresh() },
        })
      })
      break

    case 'error':
      toast.error(msg.data.code, { description: msg.data.message })
      break
  }
}

async function silentRefresh() {
  // Calls POST /v1/auth/refresh with refresh token (from httpOnly cookie or store)
  // Updates useAuthStore on success
}
```

### Query key factory (`src/lib/query-keys.ts`)

```ts
export const qk = {
  agents: {
    all: ['agents'] as const,
    detail: (id: string) => ['agents', id] as const,
  },
  tasks: {
    all: ['tasks'] as const,
    list: (filters: { status?: string }) => ['tasks', 'list', filters] as const,
    detail: (id: string) => ['tasks', id] as const,
    trace: (id: string) => ['tasks', id, 'trace'] as const,
  },
  workflows: {
    all: ['workflows'] as const,
    detail: (id: string) => ['workflows', id] as const,
  },
  health: ['health'] as const,
  dlq: ['dlq'] as const,
  costs: ['costs'] as const,
  memory: ['memory'] as const,
  locks: ['locks'] as const,
}
```

### i18next init (`src/i18n/index.ts`)

```ts
import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

import enCommon from '@/locales/en/common.json'
import enAgents from '@/locales/en/agents.json'
import enTasks from '@/locales/en/tasks.json'
import enErrors from '@/locales/en/errors.json'
import trCommon from '@/locales/tr/common.json'
import trAgents from '@/locales/tr/agents.json'
import trTasks from '@/locales/tr/tasks.json'
import trErrors from '@/locales/tr/errors.json'

const browser = navigator.language.toLowerCase()
const initial = browser.startsWith('tr') ? 'tr' : 'en'

i18n.use(initReactI18next).init({
  lng: initial,
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
  react: { useSuspense: false },     // synchronous resources, no suspense boundary
  resources: {
    en: { common: enCommon, agents: enAgents, tasks: enTasks, errors: enErrors },
    tr: { common: trCommon, agents: trAgents, tasks: trTasks, errors: trErrors },
  },
})

export default i18n
```

### Responsive list pattern (`src/components/common/ResponsiveList.tsx`)

```tsx
// Single data source, two renders, breakpoint toggle via Tailwind.
// UI-15 acceptance: table on md+, card on small.
interface Props<T> {
  items: T[]
  columns: { key: keyof T; label: string }[]
  cardRender: (item: T) => React.ReactNode
}

export function ResponsiveList<T extends { id: string }>({ items, columns, cardRender }: Props<T>) {
  return (
    <>
      {/* Desktop table */}
      <div className="hidden md:block">
        <table className="w-full">
          <thead><tr>{columns.map(c => <th key={String(c.key)}>{c.label}</th>)}</tr></thead>
          <tbody>
            {items.map(i => (
              <tr key={i.id}>
                {columns.map(c => <td key={String(c.key)}>{String(i[c.key])}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {/* Mobile cards */}
      <div className="md:hidden space-y-2">
        {items.map(i => <div key={i.id} className="rounded-lg border p-3">{cardRender(i)}</div>)}
      </div>
    </>
  )
}
```

### FastAPI static mount (one-time change in `app/main.py`)

```python
from fastapi.staticfiles import StaticFiles
from pathlib import Path

WEB_DIST = Path(__file__).parent.parent / "web" / "dist"

# Inside create_app() or after router includes:
if WEB_DIST.exists():
    app.mount("/dashboard", StaticFiles(directory=str(WEB_DIST), html=True), name="dashboard")
else:
    logger.warning("web_dist_missing", path=str(WEB_DIST))
```

The `html=True` flag makes Starlette serve `index.html` for any path that doesn't match a file (SPA deep link support).

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Tailwind v3 (`tailwind.config.js`, `@tailwind` directives, PostCSS) | Tailwind v4 (`@theme` CSS block, `@tailwindcss/vite` plugin, `@import "tailwindcss"`) | 2025 | Most tutorials on the internet are v3. Planner must verify v4 setup at execution time. |
| React Router v6 `createBrowserRouter` | TanStack Router file-based routing with Vite plugin | 2024 | Type-safe by default, first-class TanStack Query integration. |
| `react-query` v4 → `@tanstack/react-query` v5 | v5+ | 2023 | Renamed, new `queryFn` signature options. |
| Zustand v4 | Zustand v5 | 2024 | v5 removed default exports of `shallow` from root; import from `zustand/react/shallow`. |
| JWT in localStorage | JWT in memory + httpOnly refresh cookie | Industry shift 2022+ | UI-01 explicit. |
| CSS-in-JS (styled-components, emotion) | Tailwind + CSS variables | 2023+ | shadcn embodies this approach. |

**Deprecated / outdated:**

- Tailwind v3 config style for new projects.
- React Router v6 for TanStack ecosystem projects.
- `create-react-app` - use Vite.
- `jest` - use `vitest` in Vite projects (10x faster, zero config).

## Open Questions

1. **Does the backend expose `/v1/auth/refresh` in a shape the UI can call from JS?**
   - What we know: `routes_auth.py` has `POST /v1/auth/refresh` accepting a `TokenRefresh` body with `refresh_token` field. Phase 2 D-11 mentions `token_expiring` warning event.
   - What's unclear: Is the refresh token delivered as httpOnly cookie (ideal for security) or returned in the login response body (requires JS to store it)? Current `TokenResponse` returns both `access_token` and `refresh_token` in the body, which implies the JS holds both.
   - Recommendation: For Phase 4, store the refresh token in Zustand (in-memory, same as access token). On page refresh both are lost and user re-logs in - acceptable per UI-01. If the user wants "remember me" across refreshes, that's a separate backend change to use httpOnly cookies, which is a Phase 5+ scope.

2. **Are `task_progress` and `agent_status_changed` events already broadcast by the backend for `/v1/ws/ui`, or only for `/v1/ws` (agent endpoint)?**
   - What we know: Phase 2 D-07 defines `task_progress`, D-05 defines critical events list, WS-04/WS-05 pending in REQUIREMENTS.md.
   - What's unclear: Reading `routes_websocket.py` shows only the legacy `/v1/ws` agent endpoint. The `/v1/ws/ui` endpoint from Phase 2 may or may not be wired into all services yet.
   - Recommendation: Planner adds an early-phase task to grep for `broadcast_to_ui` calls in `app/services/` and confirm events fire. If missing, that's an out-of-phase bug to file against Phase 2, not a Phase 4 blocker - UI can still subscribe and show an empty stream.

3. **Which `accent` color from the shadcn palette does brand want?**
   - What we know: D-03 says "emerald or violet recommended."
   - What's unclear: No user preference captured.
   - Recommendation: Planner picks **emerald** (matches "agent alive / online / healthy" semantic better than violet for an ops dashboard), flags for user confirmation in plan review.

4. **Does the VPS have Node.js installed?**
   - What we know: Production is a systemd-managed FastAPI at `hub.brunhilde.cloud`.
   - What's unclear: Whether Node is available for building, or whether `dist/` should be built locally and shipped.
   - Recommendation: Planner includes a task to probe the VPS and either install Node or set up a build-and-ship flow. Flag for user.

5. **Playwright E2E: Phase 4 or Phase 5?**
   - What we know: TEST-06 is mapped to Phase 5. But users will want smoke testing in Phase 4.
   - Recommendation: Phase 4 ships a minimal smoke test (login → dashboard loads → sign out). Full golden-path E2E coverage lands in Phase 5 per TEST-06.

## Validation Architecture

This section applies because `workflow.nyquist_validation: true` in `.planning/config.json`.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Vitest 4.1.4 (Vite-native) + @testing-library/react 16.3.2 + jsdom 29.0.2 |
| Config file | `web/vitest.config.ts` (shares `vite.config.ts` via `mergeConfig`) |
| Quick run command | `cd web && npm run test -- --run` (non-watch, fast) |
| Full suite command | `cd web && npm run test -- --run && npm run typecheck && npm run lint` |
| Mock backend | `msw` 2.13.2 with handlers in `web/src/mocks/handlers.ts` |

Backend tests (Python pytest) remain unchanged - Phase 4 does not touch Python code meaningfully (only the 5-line StaticFiles mount, which gets a trivial smoke test).

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| UI-01 | Login form submits, stores token in memory, redirects | unit + integration | `vitest run src/components/forms/LoginForm.test.tsx` | ❌ Wave 0 |
| UI-01 | JWT NOT in localStorage after login | unit | `vitest run src/stores/auth-store.test.ts` | ❌ Wave 0 |
| UI-02 | Agent list renders from TanStack Query, updates on `agent_status_changed` WS event | integration | `vitest run src/hooks/useWebSocketSync.test.ts` | ❌ Wave 0 |
| UI-03 | Task list filters by status column | unit | `vitest run src/routes/_authed/tasks/index.test.tsx` | ❌ Wave 0 |
| UI-04 | Task create form validates with zod, submits mutation | unit | `vitest run src/components/forms/TaskCreateForm.test.tsx` | ❌ Wave 0 |
| UI-05 | Cancel button triggers mutation, optimistic update | unit | same as UI-03 | ❌ Wave 0 |
| UI-06 | Workflow step list renders badges | unit | `vitest run src/routes/_authed/workflows/$workflowId.test.tsx` | ❌ Wave 0 |
| UI-07 | Agent detail route loads from URL param | integration | `vitest run src/routes/_authed/agents/$agentId.test.tsx` | ❌ Wave 0 |
| UI-08 | Health polling calls `/v1/health` every 10s | unit | `vitest run src/hooks/useHealth.test.ts` | ❌ Wave 0 |
| UI-09 | Toast renders RFC 7807 problem title + detail | unit | `vitest run src/lib/api-client.test.ts` | ❌ Wave 0 |
| UI-10 | DLQ retry button fires mutation | unit | `vitest run src/routes/_authed/dlq.test.tsx` | ❌ Wave 0 |
| UI-11 | Cost display reads from query | manual | visual check | N/A |
| UI-12 | Trace timeline renders nested spans | unit | `vitest run src/components/common/TraceTimeline.test.tsx` | ❌ Wave 0 |
| UI-13 | Memory viewer expands JSON | unit | `vitest run src/components/common/JsonViewer.test.tsx` | ❌ Wave 0 |
| UI-14 | Lock panel shows conflicts as warnings | manual | visual check | N/A |
| UI-15 | Responsive layout hides table at `<md` breakpoint | unit (snapshot) | `vitest run src/components/common/ResponsiveList.test.tsx` | ❌ Wave 0 |
| UI-16 | WS hook reconnects with backoff + shows banner | integration | `vitest run src/hooks/useWebSocketSync.test.ts` | ❌ Wave 0 |

**Manual-only justification:** UI-11 and UI-14 are read-only display panels of backend-sourced data. Their value is "does the data look right to a human" - unit testing the render is low-value, E2E covers it in Phase 5.

### Sampling Rate

- **Per task commit:** `cd web && npm run test -- --run --changed` (changed files only, < 10s) + `npx tsc --noEmit` (type check, < 15s)
- **Per wave merge:** `cd web && npm run test -- --run` (full Vitest suite) + `npm run typecheck` + `npm run lint`
- **Phase gate:** Full suite green + backend pytest green + manual smoke test (login, agents list loads, task create works, reconnect banner appears when backend stops)

### Wave 0 Gaps

Every file in the "Test Map" above is a Wave 0 gap - the entire frontend test infrastructure is new. Wave 0 must:

- [ ] `web/vitest.config.ts` - Vitest config with jsdom environment
- [ ] `web/src/test/setup.ts` - `@testing-library/jest-dom` matchers + msw server start
- [ ] `web/src/mocks/handlers.ts` - msw request handlers for `/v1/agents`, `/v1/tasks`, `/v1/auth/login`, `/v1/health`, etc.
- [ ] `web/src/mocks/server.ts` - msw node server instance
- [ ] Framework install commands: covered by the `npm install -D` list in "Installation" section
- [ ] `web/package.json` scripts: `"test": "vitest"`, `"typecheck": "tsc --noEmit"`, `"lint": "eslint ."`
- [ ] Root conftest or backend test for StaticFiles mount: `tests/integration/test_dashboard_mount.py` - asserts `GET /dashboard` returns `200` when `web/dist/index.html` exists, asserts deep-link `GET /dashboard/agents/foo` serves `index.html`

## Sources

### Primary (HIGH confidence)

- **npm registry (`npm view <pkg> version`)** queried 2026-04-13 for all pinned versions in Standard Stack table. This is authoritative current data.
- `.planning/phases/04-command-center-ui/04-CONTEXT.md` - all D-01..D-16 decisions.
- `.planning/phases/02-websocket-test-suite/02-CONTEXT.md` - WebSocket protocol (D-01 event format, D-03 first-frame auth, D-05/D-06 tiers, D-11 token_expiring).
- `.planning/phases/01-backend-hardening/01-CONTEXT.md` - RFC 7807 Problem Details (D-01).
- `.planning/REQUIREMENTS.md` - UI-01..UI-16 acceptance criteria.
- `app/api/routes_websocket.py` - confirmed legacy `/v1/ws` uses `?token=` query param (NOT the pattern for `/v1/ws/ui`).
- `app/api/routes_auth.py` - confirmed `POST /v1/auth/login` via `agent_login` and `admin_login`, `POST /v1/auth/refresh` via `refresh_access_token`. Refresh token is returned in response body.
- `./CLAUDE.md` - React + Vite lock, `web/` directory, GSD workflow rule.

### Secondary (MEDIUM confidence)

- shadcn/ui docs at ui.shadcn.com - known from training plus version 4.2.0 confirmed. Tailwind v4 support in shadcn v4 is inferred from release timing (shadcn 4.x major released to support Tailwind v4).
- TanStack Router docs at tanstack.com/router - file-based routing pattern, `_authed` pathless layout with `beforeLoad` redirect is the documented idiom.
- Tailwind v4 migration semantics (no config file, `@theme`, `@import`) - confirmed by `v3-lts` dist tag on npm + v4 being `latest`.

### Tertiary (LOW confidence - verify at execution)

- Exact shadcn `init` prompts (may have changed between 4.x minor versions).
- Exact `tanstackRouter` plugin options (`autoCodeSplitting` flag name).
- Whether `/v1/ws/ui` is wired to all services yet (Open Question 2).
- Whether VPS has Node installed (Open Question 4).

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH - all versions verified against live npm registry.
- Architecture patterns: HIGH - follows canonical docs for each locked library.
- Tailwind v4 specifics: MEDIUM - training data overlaps with release, but shadcn init exact prompts should be re-verified during scaffold task.
- Code examples: HIGH for Zustand / api-client / route guard / WS hook / i18n / responsive list. MEDIUM for exact `vite.config.ts` plugin ordering (planner should check TanStack Router plugin README at execution).
- Pitfalls: HIGH - all documented upstream, cross-referenced with CONTEXT.md locks.
- Validation architecture: HIGH - Vitest + MSW is the current standard for Vite React apps.

**Research date:** 2026-04-13
**Valid until:** 2026-05-13 (30 days - stack is stable but shadcn CLI evolves monthly)
