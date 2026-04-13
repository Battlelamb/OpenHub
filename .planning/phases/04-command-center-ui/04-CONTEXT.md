# Phase 4: Command Center UI - Context

**Gathered:** 2026-04-13
**Status:** Ready for planning

<domain>
## Phase Boundary

OpenHub'ı self-host eden bir developer browser üzerinden tam yönetebilsin: JWT login, live agent status board, task CRUD (create/cancel), workflow viewer, DLQ retry, cost/trace/memory/lock paneleri, mobile-responsive layout. **Tek React+Vite SPA dashboard**, 16 UI requirement (UI-01 … UI-16).

**Out of scope:** Native mobile app (deferred to v2 — `MOB-01`), backend API changes (Phase 1-3 ship'lendi), new endpoints (mevcut REST + `/v1/ws/ui` üzerine inşa edilir).

</domain>

<decisions>
## Implementation Decisions

### Component Library + Design System
- **D-01:** Tailwind CSS + shadcn/ui (Radix UI primitives, copy-paste components). `npx shadcn@latest add <component>` ile kod kendi repo'muzda yaşar, runtime lock-in yok. shadcn'in built-in primitives'i (Table, Dialog, Toast, Form, Tabs, Sheet, Badge, Skeleton) tüm 16 req için yeterli.
- **D-02:** Dark mode default + manual light toggle. Tailwind `dark:` variant + `class` strategy (root `<html>` üzerine `class="dark"` toggle). Toggle preference localStorage'da değil React state + cookie/header'da (UI-01 in-memory pattern paralel).
- **D-03:** Brand palette: zinc/slate base + tek accent color (downstream agent — researcher veya planner — modern dashboard standardına uygun seçer; emerald veya violet öneri).

### State + Data Layer
- **D-04:** TanStack Query (REST cache, background refetch, mutations, optimistic updates) + Zustand (UI-only client state: open modals, selected tab, sidebar collapsed). İkisi de tiny, AI-friendly, modern React standard.
- **D-05:** WebSocket → REST cache sync **hibrit pattern**: critical events (`agent_status_changed`, `task_status_changed`, `task_progress`) `queryClient.setQueryData` ile optimistic merge yapar (UI anında güncellenir). Non-critical events (`heartbeat`, metadata changes) `queryClient.invalidateQueries` ile background refetch tetikler. Stale data riskini critical/non-critical ayrımıyla minimize ediyoruz.
- **D-06:** WebSocket hook (UI-16) hem optimistic merge hem invalidate path'lerini içerir, exponential backoff reconnection (start 1s, max 30s), reconnect sırasında "Reconnecting..." top banner, reconnect başarılı olduğunda **tüm** queryClient cache invalidate edilir (Phase 2 D-04 "fresh state via REST" pattern'i).

### Project Structure + Dev/Deploy
- **D-07:** Frontend `web/` dizini altında, FastAPI `app/` ile aynı root'ta. Monorepo refactor yok (boundaries az dosya hareketiyle çizilir).
- **D-08:** Production: `npm run build` → `web/dist/` → FastAPI `StaticFiles(directory="web/dist", html=True)` mount eder, route: `/dashboard`. Tek deploy artifact, tek systemd unit, tek port (7788). Brunhilde'de zero new infra.
- **D-09:** Dev: Vite dev server `:5173`, `vite.config.ts` `server.proxy` ile `/v1/*` → `http://localhost:7788`, `/v1/ws/ui` → `ws://localhost:7788` (WS proxy desteği). `npm run dev` + `uvicorn app.main:app --reload` paralel çalışır.
- **D-10:** Mevcut `app/static/admin.html` **silinmiyor** — `/admin` route'unda kalmaya devam ediyor. Phase 4 React UI yeni `/dashboard` route'unda yaşıyor. Soft transition: bookmark'lar bozulmaz, brunhilde mevcut admin'i kaybetmez. Phase 5 release readiness'te kullanım gözlemine göre admin.html silme kararı verilir.

### Routing + Auth + i18n
- **D-11:** **TanStack Router** (React Router v6 değil). Type-safe routing, file-based, `loader` API ile route-level data fetching (TanStack Query ile birinci sınıf integration), auto-generated route tree. Modern, AI-friendly, learning curve minimal.
- **D-12:** **Sidebar layout** (sol kolon, collapsible). 16 feature top-nav'a sığmaz; sidebar dashboard standardı (Linear, GitHub, Vercel). Sidebar groups: Operations (Agents, Tasks, Workflows), Visibility (DLQ, Costs, Traces, Memory, Locks), Admin (Health, Settings).
- **D-13:** **Ayrı `/login` route** (full page). 401 handler global query/fetch interceptor → `router.navigate({ to: '/login' })`. Login form `react-hook-form` + `zod` validation. Login success → redirect to original target route (`?redirect=/dashboard/agents`).
- **D-14:** JWT in-memory only (UI-01 explicit). Token Zustand store'unda, page refresh = re-login. localStorage ve URL params **kesin yasak**. Refresh token (eğer backend destekliyorsa) httpOnly cookie üzerinden — Phase 2'de WS handshake için kullanılan auth pattern'iyle uyumlu.
- **D-15:** **Hibrit token refresh:** `token_expiring` WS event'i geldiğinde önce silent refresh (`POST /v1/auth/refresh`) dene. Başarılı → kullanıcı hiç görmez. Başarısız (network error, 401) → toast warning ("Oturum bitiyor, devam etmek için tıkla") + manual continue button. En kullanıcı dostu + en güvenli kombinasyon.
- **D-16:** **Bilingual i18n** (Turkish + English) via **i18next** + `react-i18next`. JSON locale files: `web/src/locales/{tr,en}/common.json`. Dil toggle settings menüsünde. Default language: browser `navigator.language` → fallback English. OSS release-ready (Phase 5'i unblock eder), Türkçe kullanım da first-class.

### Claude's Discretion (downstream agent decides)
- Form library specifics (`react-hook-form` + `zod` strongly recommended, ama planner override edebilir)
- Toast library (sonner vs react-hot-toast vs shadcn'in built-in toast'u)
- DataTable rendering: shadcn Table + TanStack Table mı, custom mı
- Distributed trace viewer (UI-12) için library (custom timeline render önerilir, ek dep yok)
- Mobile breakpoint thresholds (Tailwind default `sm/md/lg/xl/2xl` yeterli, UI-15 detayları planner'ın)
- Dark mode brand accent renk seçimi
- Sidebar group ordering ve icon set (lucide-react önerilir, shadcn ile birlikte gelir)
- Skeleton loading state pattern (shadcn Skeleton component'i mevcut)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Backend contracts (consumed by this phase)
- `.planning/REQUIREMENTS.md` § Command Center UI — UI-01 ile UI-16 acceptance criteria
- `.planning/phases/02-websocket-test-suite/02-CONTEXT.md` — WebSocket protocol decisions (D-01..D-17). Özellikle D-01 event format, D-03 JWT-in-first-frame auth, D-04 reconnect strategy, D-05/D-06 critical/non-critical event tiers, D-11 token_expiring warning, D-12 connection limits, D-14 close codes
- `.planning/phases/01-backend-hardening/01-CONTEXT.md` — Error response format (D-01 RFC 7807 Problem Details), structured logging (D-05). UI-09 toast component bu format'ı parse edip render edecek.
- `app/api/routes_websocket.py` — `/v1/ws/ui` endpoint, message protocol, JWT handshake
- `app/api/routes_auth.py` — `/v1/auth/login`, `/v1/auth/refresh` endpoint shapes
- `app/models/errors.py` — Pydantic `ProblemDetail` shape

### Existing reference UI
- `app/static/admin.html` — Current Turkish vanilla JS admin SPA (258 lines). Reference for: tab navigation pattern, login overlay flow, refresh button behavior, status indicators. Phase 4 UI **bunu replace etmiyor**, paralel yaşıyor.

### Stack & conventions
- `.planning/PROJECT.md` — React + Vite stack lock, "no native mobile yet" constraint
- `.planning/codebase/STACK.md` — backend stack reference
- `.planning/codebase/CONVENTIONS.md` — Python conventions (frontend yeni, kendi conventions'unu plan-phase'de tanımlayacak)

### External docs (research-phase için)
- shadcn/ui docs — https://ui.shadcn.com (component catalog + installation pattern)
- TanStack Router docs — https://tanstack.com/router/latest (file-based routing, type-safe loaders)
- TanStack Query docs — https://tanstack.com/query/latest (REST cache, mutations, WS integration patterns)
- Zustand docs — https://zustand-demo.pmnd.rs (minimal client state)
- i18next + react-i18next — https://react.i18next.com

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`/v1/auth/login` + `/v1/auth/refresh` REST endpoints** — backend already exposes JWT auth (Phase 1 hardening). UI consumes directly, no new backend code needed.
- **`/v1/ws/ui` WebSocket endpoint** — Phase 2 ship'lendi. UI hook bu endpoint'e bağlanır, JWT-in-first-frame auth uygular, exponential backoff ile reconnect eder.
- **`ProblemDetail` schema (RFC 7807)** — Phase 1'den gelen tüm 4xx/5xx response shape. UI'nın Toast component'i bu shape'i parse edip `title` + `detail`'i renderler.
- **`app/static/admin.html`** — Mevcut Turkish admin SPA. **Reference** olarak kullan: tab pattern, login overlay UX, refresh icon, status dot indicator. Replace etmiyoruz, yan yana koşuyor.
- **Vector search `POST /v1/search`** — Phase 3'te ship'lendi. UI'da yeni feature scope'unda değil ama gelecek phase'lerde search bar olarak kullanılabilir (Phase 4'te değil).

### Established Patterns
- **REST endpoint naming:** `/v1/{resource}` (snake_case path, JSON body, kebab-case query)
- **WebSocket message format:** `{event, agent_id, timestamp, data}` — UI client'ı bu shape'i parser
- **Error responses:** RFC 7807 `{type, title, status, detail, instance, errors[]}` — UI Toast bunu parser
- **Auth header:** `Authorization: Bearer <jwt>` — UI tüm fetch/WS calls'da bunu set eder

### Integration Points
- **FastAPI static mount** — Backend `app/main.py` lifespan'a `app.mount("/dashboard", StaticFiles(directory="web/dist", html=True))` eklenecek (D-08). Production'da Vite build output buradan serve edilir.
- **Vite proxy config** — `web/vite.config.ts` development sırasında `/v1/*` → `localhost:7788` proxy yapar. WS proxy: `/v1/ws/ui` → `ws://localhost:7788`.
- **CORS** — Phase 1 hardening'de `cors_origins` whitelist'i var. Brunhilde'de `https://hub.brunhilde.cloud` eklenmesi gerekecek (zaten ekli olabilir, deploy time check).
- **Systemd service** — Phase 4 ship'lendiğinde mevcut systemd unit (`openhub.service`) hiç değişmiyor. `git pull && systemctl --user restart openhub.service` ile her şey güncelleniyor (frontend dahil, çünkü FastAPI static serve ediyor).

</code_context>

<specifics>
## Specific Ideas

- **Sidebar groups:** Operations (Agents, Tasks, Workflows), Visibility (DLQ, Costs, Traces, Memory, Locks), Admin (Health, Settings). Plan-phase bu grupları validate edebilir veya yeniden organize edebilir.
- **Login form:** `react-hook-form` + `zod` validation. Username + password inputs. Error toast'ı RFC 7807 format'tan render eder.
- **Top bar:** Health indicator dot (UI-08 `/v1/health` polling), reconnecting banner (UI-16 WS state), user menu (logout, language toggle, dark/light toggle).
- **Task create form (UI-04):** Modal dialog (shadcn Dialog), `react-hook-form` + `zod`, agent selector dropdown (TanStack Query'den `/v1/agents` listesi).
- **DLQ retry (UI-10):** Table row action button → POST `/v1/dlq/{id}/retry` → optimistic UI update + invalidate query.
- **Mobile breakpoint pattern (UI-15):** `md:` ve üstünde Table, altında Card grid. shadcn DataTable + Tailwind responsive variants.
- **Trace viewer (UI-12):** Vertical timeline (custom render, no library), her node tool call/sub-step gösterir, render time/duration badges.
- **Memory viewer (UI-13):** Key-value table with size + age columns, expandable JSON inspector for value preview.

</specifics>

<deferred>
## Deferred Ideas

- **Native mobile app** — `MOB-01` requirement, v2'ye ertelendi. Phase 4 sadece responsive web.
- **Full search bar in topbar (vector search across all entities)** — Phase 3 backend ready, ama UI scope'unda değil. Phase 5 veya backlog.
- **Multi-tenant / org switching** — OpenHub şu an single-tenant, gelecek roadmap.
- **Notification panel** (persistent notification feed) — UI-09 sadece toast, persistent panel ileride.
- **Custom dashboards / drag-drop layouts** — out of scope, fancy feature.
- **Real-time collaborative cursors** — out of scope.
- **Onboarding tour / first-run wizard** — Phase 5 release readiness olabilir.

</deferred>

---

*Phase: 04-command-center-ui*
*Context gathered: 2026-04-13*
