# Technology Stack - OpenHub v1.0 Milestone

**Scope:** Additions only - React+Vite command center, WebSocket hardening, vector DB upgrade, test suite, production hardening.
**Backend stack is fixed:** Python 3.11+ / FastAPI / SQLite. Not re-researched here.
**Researched:** 2026-04-07

---

## What Already Exists (Do Not Re-Decide)

| Layer | Technology | Version | Status |
|-------|-----------|---------|--------|
| API framework | FastAPI | 0.104.1 | Stable, in production |
| ASGI server | Uvicorn | 0.24.0 | Stable |
| Auth | PyJWT + Casbin + passlib | 2.8.0 / 1.25.0 / 1.7.4 | Stable |
| WebSocket route | `routes_websocket.py` | - | EXISTS, partially implemented |
| WebSocket auth | API key via `?token=` query param | - | EXISTS, working pattern |
| Broadcast | `broadcast_event()` in-memory dict | - | EXISTS, single-process only |
| Vector DB | zvec 0.1.0 | 0.1.0 | EXISTS but severely outdated |
| Cache | Redis 5.0.1 (optional) | 5.0.1 | EXISTS, graceful degradation |
| Logging | structlog 23.2.0 | 23.2.0 | EXISTS |
| Monitoring | prometheus-client 0.19.0 | 0.19.0 | EXISTS, not wired |

---

## New Stack: Frontend (Command Center UI)

### Core Build

| Technology | Version | Purpose | Rationale |
|------------|---------|---------|-----------|
| React | 18.3+ | UI runtime | Established choice per PROJECT.md |
| Vite | 5.x | Build tool | Chosen per PROJECT.md - faster than CRA, lighter than Next.js |
| TypeScript | 5.x | Type safety | Required for maintainability, shadcn/ui requires it |

**Why Vite over Next.js:** OpenHub dashboard is a pure SPA with no SEO requirement and no SSR need. Vite produces a static dist/ that can be served by any file server or embedded in the FastAPI static files mount. Next.js adds SSR complexity and deployment coupling that is not justified here.

### Routing

| Technology | Version | Rationale |
|------------|---------|-----------|
| TanStack Router | 1.x | Type-safe file-based routing, native Vite SPA support, tight TanStack Query integration |

**Why TanStack Router over React Router v7:** React Router v7's type safety only works in framework mode (Remix-style). For a pure Vite SPA, TanStack Router gives full type-safe navigation, search parameter types, and loader-level data preloading. The dashboard has interconnected routes (agents -> tasks -> workflows) that benefit from type-safe params.

**Why not React Router v6 (classic SPA mode):** Still works but type safety is manual. TanStack Router makes navigation errors compiler errors, which matters for a dashboard with many cross-links.

### Data Fetching and Server State

| Technology | Version | Purpose | Rationale |
|------------|---------|---------|-----------|
| TanStack Query | 5.x | Server state, caching, polling | Industry standard for React data fetching; handles stale-while-revalidate, background refetch, WebSocket + polling hybrid |

TanStack Query handles the 90% case: fetch agents, tasks, workflows on mount, keep them fresh. WebSocket events then call `queryClient.invalidateQueries()` to trigger targeted refetches. This avoids building a full event-sourcing system in the frontend.

**Anti-pattern to avoid:** Don't use WebSocket as the sole data source. Combine polling (TanStack Query) + WebSocket invalidation. Polling covers reconnect gaps; WebSocket provides low-latency updates.

### UI Components

| Technology | Version | Purpose | Rationale |
|------------|---------|---------|-----------|
| shadcn/ui | latest (no version - copy-paste model) | Component library | Tailwind-based, accessible, full control over source, no dependency lock-in |
| Tailwind CSS | 3.x | Styling | Required by shadcn/ui; utility-first fits dashboard layout well |
| Radix UI | bundled with shadcn | Accessible primitives | Headless components underneath shadcn |
| Lucide React | latest | Icons | Default icon set for shadcn/ui ecosystem |

**Why shadcn/ui over Tremor:** Tremor is built on Recharts and opinionated toward a specific visual style. shadcn/ui gives full control. For an open source project, not being locked into a closed-style library matters - contributors can style freely. Tremor's color palette limitations become friction as the product grows.

**Why not MUI or Ant Design:** Both are large packages with tight design opinions that clash with Tailwind. shadcn/ui + Tailwind is the current community consensus for 2025 dashboards.

### Charts

| Technology | Version | Purpose | Rationale |
|------------|---------|---------|-----------|
| Recharts | 2.x | Charts and graphs | shadcn/ui ships chart components built on Recharts; no additional dependency needed |

shadcn/ui's chart primitives (AreaChart, BarChart, etc.) are built on Recharts. Use them directly. Do not add Tremor. This covers: agent activity timelines, task throughput bars, cost tracking lines.

### Client State Management

| Technology | Version | Rationale |
|------------|---------|-----------|
| Zustand | 4.x | Lightweight global state for UI-only state (selected agent, sidebar open/closed, active filters) |

TanStack Query owns server state. Zustand owns UI state. Do NOT put server data in Zustand - that's double-sourcing. Zustand's store is simple to debug and works well for the team-collaboration use case (explicit updates are traceable).

**Why not Jotai:** Jotai's atomic model is optimal for fine-grained independent state (forms, real-time data per-atom). For a dashboard where UI state is coarse-grained (current view, selected item, theme), Zustand's single store is easier to reason about.

**Why not Redux:** Overkill. No time-travel debugging or extensive middleware needed here.

### WebSocket Client

| Technology | Version | Purpose | Rationale |
|------------|---------|---------|-----------|
| Native browser WebSocket API | - | WS connection to backend | No library needed - browsers handle reconnect logic via a small custom hook |

Write a `useWebSocket` React hook wrapping the native API with: exponential backoff reconnection, token injection via query param (`?token=<api-key>`), message dispatch to `queryClient.invalidateQueries()`. Do not use socket.io or similar - the backend uses native WebSocket (FastAPI's `websockets` library), not socket.io protocol.

### Testing

| Technology | Version | Purpose | Rationale |
|------------|---------|---------|-----------|
| Vitest | 1.x | Unit and component tests | Native Vite integration, Jest-compatible API, no config overhead |
| React Testing Library | 14.x | Component testing | Standard for React component tests |
| Playwright | 1.4x | E2E tests | Full browser automation for dashboard flows |

---

## New Stack: Backend Additions

### WebSocket Hardening

The existing `routes_websocket.py` has the right structure but two gaps:

1. **No browser/dashboard client support.** Current auth assumes agent API keys (`acn-agent-*` prefix). Dashboard UI uses JWT tokens. Add a parallel auth path: if token is a JWT (starts with `ey`), validate with PyJWT. If it looks like an API key (`oh_`), use the existing `APIKeyManager` path.

2. **Single-process broadcast only.** The `_connections` dict is in-memory. With multiple Uvicorn workers, a broadcast from worker 1 misses connections on workers 2-3. For v1.0 (single-instance VPS deployment), this is acceptable. Document the limitation and add a Redis pub/sub broadcast path as an upgrade option. Do not implement Redis pub/sub for v1.0 - the complexity is not justified for a single-instance open source tool.

No new Python packages needed for WebSocket hardening. The existing `websockets==12.0` and FastAPI's built-in WebSocket support are sufficient.

### Vector Database - Upgrade zvec

**Current:** `zvec==0.1.0` (Dec 2025 release)
**Available:** `zvec==0.2.1b0` (Feb 2026, latest)

zvec 0.1.0 is Alibaba's in-process vector DB built on Proxima. It is the right choice for OpenHub because:
- In-process: no separate service to run (critical for open source self-host)
- Runs alongside SQLite with the same "zero infra" story
- 0.2.x adds RabitQ quantization and CPU SIMD dispatch for better performance

**Action:** Upgrade from `zvec==0.1.0` to `zvec==0.2.1b0` (or latest stable 0.2.x when available). The 0.2.x release is currently beta but the changes are performance-only (quantization, SIMD), not API-breaking based on the changelog.

**Why not Qdrant or Chroma:**
- Qdrant requires a separate Docker container - breaks the "pip install and run" open source UX
- Chroma is developer-friendly but also runs as a separate process by default
- zvec is already in the requirements, already configured in `Settings.zvec_path`, already has startup directory creation in `app/main.py`
- Switching to Qdrant/Chroma would require infrastructure changes incompatible with the "pip install" deployment target

**Embedding model:** The existing `Settings.embedding_model` config drives what model zvec uses for encoding. No change needed to the config shape - just wire up the vector service to actually use it (it's configured but not actively called in most routes).

### Test Suite (Zero Tests Currently)

| Technology | Version | Purpose | Rationale |
|------------|---------|---------|-----------|
| pytest | 7.4.3 (already in requirements) | Unit and integration tests | Already declared, just unused |
| pytest-asyncio | 0.21.1 (already in requirements) | Async test support | Required for FastAPI async routes |
| pytest-cov | 4.1.0 (already in requirements) | Coverage reporting | Already declared |
| httpx | 0.25.2 (already in requirements) | TestClient for FastAPI | FastAPI docs recommend `httpx.AsyncClient` with `ASGITransport` for testing |

No new test dependencies needed. All required packages are already declared.

**Testing pattern for FastAPI:** Use `httpx.AsyncClient` with `ASGITransport(app=app)` - not `TestClient` which is synchronous. This is the current FastAPI 0.104+ recommended approach.

### Production Hardening

| Technology | Version | Purpose | Rationale |
|------------|---------|---------|-----------|
| slowapi | 0.1.9 (already declared) | Rate limiting | Already in requirements but "not yet wired into middleware" per STACK.md - just needs wiring |
| prometheus-client | 0.19.0 (already declared) | Metrics | Already in requirements but "not yet actively instrumented" - add route-level metrics |

---

## What NOT to Use

| Technology | Why Not |
|-----------|---------|
| socket.io / python-socketio | Backend uses native WebSocket. Adding socket.io protocol creates client-server protocol mismatch. The existing implementation is simpler and correct. |
| Next.js | SSR adds complexity and deployment coupling with no benefit for this SPA dashboard. Vite was already decided in PROJECT.md. |
| Redux / Redux Toolkit | Overkill for this UI surface. TanStack Query handles server state; Zustand handles UI state. Redux adds boilerplate with no return. |
| Qdrant / Chroma / Milvus | All require separate services. Breaks the "pip install" open source deployment story. zvec is in-process and already integrated. |
| Tremor | Built on Recharts; shadcn/ui's chart primitives already use Recharts. Two charting abstractions is redundant. Tremor's opinionated styling limits open source contributor flexibility. |
| Jotai | Correct for fine-grained atomic state; overkill for coarse-grained dashboard UI state. Zustand is simpler. |
| Axios | httpx is already used backend-side. Frontend should use native `fetch` wrapped by TanStack Query, or a minimal abstraction. Axios adds 50kb+ bundle for no meaningful gain over `fetch` in 2025. |
| D3.js | Too low-level for this use case. Recharts (via shadcn charts) provides everything needed with far less code. |

---

## Installation

### Frontend (new)

```bash
# From OpenHub repo root
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install

# Routing + data
npm install @tanstack/react-router @tanstack/react-query

# State
npm install zustand

# UI
npm install tailwindcss @tailwindcss/vite
npx shadcn@latest init
npx shadcn@latest add button card table badge dialog sheet

# Charts (via shadcn - uses Recharts underneath)
npx shadcn@latest add chart

# Icons
npm install lucide-react

# Testing
npm install -D vitest @testing-library/react @testing-library/user-event @vitejs/plugin-react
npm install -D playwright @playwright/test
```

### Backend (upgrades only)

```bash
# Upgrade zvec
pip install "zvec==0.2.1b0"
# Update requirements.txt: zvec==0.2.1b0

# No new packages needed for WebSocket hardening, tests, or monitoring
# All required packages already declared in requirements.txt
```

---

## Confidence Assessment

| Area | Confidence | Basis |
|------|-----------|-------|
| React + Vite + shadcn/ui + TanStack stack | HIGH | Multiple official docs, wide community adoption confirmed by npm trends and GitHub discussions |
| TanStack Router for Vite SPA | MEDIUM-HIGH | Official TanStack docs confirm Vite SPA support; community consistently recommends for dashboard use case |
| WebSocket auth via query param | HIGH | FastAPI official docs, multiple verified sources; browser limitation (no custom WS headers) is a documented browser spec constraint |
| zvec upgrade from 0.1.0 to 0.2.x | MEDIUM | PyPI confirmed 0.2.1b0 exists (Feb 2026); "beta" tag introduces some risk; API surface needs verification against existing integration points before upgrade |
| Keep zvec over Qdrant/Chroma | HIGH | In-process requirement is non-negotiable for the "pip install" deployment target; Qdrant/Chroma require separate processes |
| Zustand for UI state | HIGH | 2025 community consensus: TanStack Query for server state, Zustand for client UI state |
| Single-process WebSocket acceptable for v1.0 | HIGH | Deployment is single-instance VPS; Redis pub/sub broadcast is a documented v2+ concern |

---

## Sources

- [shadcn/ui Vite installation](https://ui.shadcn.com/docs/installation/vite) - Official docs
- [TanStack Router vs React Router comparison](https://tanstack.com/router/latest/docs/framework/react/comparison) - Official TanStack docs
- [FastAPI WebSocket official docs](https://fastapi.tiangolo.com/advanced/websockets/) - Official FastAPI docs
- [WebSocket auth with JWT query parameter](https://hexshift.medium.com/adding-authentication-to-websocket-endpoints-in-fastapi-a7efe417188f) - MEDIUM confidence, verified against FastAPI official pattern
- [10 FastAPI WebSocket Patterns for Live Dashboards](https://medium.com/@connect.hashblock/10-fastapi-websocket-patterns-for-live-dashboards-3e36f3080510) - MEDIUM confidence
- [zvec GitHub](https://github.com/alibaba/zvec) - Official repository
- [zvec PyPI](https://pypi.org/project/zvec/) - Package registry, version history verified
- [Zustand vs Jotai 2025 comparison](https://www.reactlibraries.com/blog/zustand-vs-jotai-vs-valtio-performance-guide-2025) - MEDIUM confidence, matches multiple sources
- [Vector DB comparison 2025](https://liquidmetal.ai/casesAndBlogs/vector-comparison/) - MEDIUM confidence, used to validate keeping zvec
- [shadcn/ui chart components on Recharts](https://github.com/shadcn-ui/ui/discussions/4133) - Community confirmation
