# Phase 4: Command Center UI - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-13
**Phase:** 04-command-center-ui
**Areas discussed:** Component library + design system, State + data layer, Project structure + dev/deploy, Routing + auth flow + i18n

---

## Component Library + Design System

### Q1: Hangi component library?

| Option | Description | Selected |
|--------|-------------|----------|
| Tailwind + shadcn/ui | Radix UI + copy-paste components, no runtime lock-in, modern OSS dashboard standard | ✓ |
| Tailwind + Mantine | Full-featured, more built-in primitives, lib lock-in | |
| Tailwind only (custom) | Maximum control, slow for 16 reqs | |

**Notes:** shadcn/ui dev velocity ve AI-friendliness için seçildi. lucide-react icon set built-in geliyor.

### Q2: Dark mode + renk şeması?

| Option | Description | Selected |
|--------|-------------|----------|
| Dark default + light toggle | Modern developer dashboard standard (Linear, GitHub, Vercel) | ✓ |
| Light default + dark toggle | Traditional, admin.html benzeri | |
| Dark only | En basit, toggle yok | |
| System preference (auto) | OS dark/light follow + manual override | |

---

## State + Data Layer

### Q1: REST data caching ve client state?

| Option | Description | Selected |
|--------|-------------|----------|
| TanStack Query + Zustand | TQ: REST cache + mutations + optimistic. Zustand: minimal UI client state. Modern React standard. | ✓ |
| RTK Query (Redux Toolkit) | Unified state + cache, more boilerplate | |
| SWR + native useState | Minimal, less deps, manual WS sync | |

### Q2: WebSocket events REST cache'i nasıl etkilesin?

| Option | Description | Selected |
|--------|-------------|----------|
| Invalidate-on-event | WS event → invalidateQueries → background refetch | |
| Optimistic merge | WS event → setQueryData → no refetch | |
| Hibrit: critical optimistic, others invalidate | task_status critical → optimistic; heartbeat → invalidate | ✓ |

**Notes:** Hibrit en kompleks ama en doğru. Critical events kullanıcının anında görmesi gereken state changes (task done, agent offline). Diğerleri 5s batch'te toplanır, invalidate yeterli.

---

## Project Structure + Dev/Deploy

### Q1: Frontend nerede yaşasın + production serve?

| Option | Description | Selected |
|--------|-------------|----------|
| web/ + FastAPI static mount | Tek deploy artifact, brunhilde'de zero new infra | ✓ (default lock'landı, soru kısa kesildi) |
| frontend/ + FastAPI static mount | Aynı yaklaşım, farklı dizin adı | |
| web/ + ayrı Caddy reverse proxy | Daha esnek, ek config gerektirir | |
| apps/web/ + apps/api/ true monorepo | Full monorepo refactor, scope creep | |

**Notes:** Kullanıcı "ön taraf React değil mi" diyerek sorunun yönünü sorguladı. Açıklama: React zaten locked, soru klasör adı + serve yöntemi. Sade default'lar lock'landı.

### Q2: admin.html ne olacak?

| Option | Description | Selected |
|--------|-------------|----------|
| Yan yana dur, /admin = old, /dashboard = new | Soft transition, bookmarks bozulmaz | ✓ |
| Phase 4 sonu silinsin | En temiz, transition risk | |
| /admin/legacy.html'e taşı | Compromise | |

---

## Routing + Auth Flow + i18n

### Q1: Router + layout + login UX?

| Option | Description | Selected |
|--------|-------------|----------|
| React Router v6 + Sidebar + /login route | Modern dashboard standard, max adoption | |
| React Router v6 + Top nav + login modal | admin.html visual continuity | |
| TanStack Router + Sidebar + /login | Type-safe + file-based, AI-friendly | ✓ |

**Notes:** TanStack Router seçildi — type-safety ve TanStack Query ile birinci sınıf integration.

### Q2: token_expiring eventi geldiğinde?

| Option | Description | Selected |
|--------|-------------|----------|
| Silent refresh | Backend refresh otomatik, kullanıcı görmez | |
| Toast warning + manual continue | 60s kala uyarı + buton | |
| Hibrit: silent first, fallback toast | Önce dene, başarısızsa uyar | ✓ |

### Q3: Dil stratejisi?

| Option | Description | Selected |
|--------|-------------|----------|
| English only | OSS audience, single language complexity | |
| Türkçe only | admin.html devamı, native dil | |
| Her ikisi (i18next) | Bilingual TR + EN, OSS-ready + first-class TR | ✓ |

---

## Claude's Discretion

User explicitly deferred or did not raise:
- Form library specifics (`react-hook-form` + `zod` strongly recommended in CONTEXT.md)
- Toast library (sonner vs react-hot-toast vs shadcn built-in)
- DataTable rendering library
- Distributed trace viewer rendering approach
- Mobile breakpoint thresholds (Tailwind defaults)
- Dark mode brand accent color
- Sidebar group ordering and icon set
- Skeleton loading state pattern

These will be decided by gsd-phase-researcher and gsd-planner.

## Deferred Ideas

- Native mobile app (MOB-01 — v2)
- Vector search bar in topbar (Phase 5 or backlog)
- Multi-tenant / org switching
- Persistent notification panel
- Custom dashboards / drag-drop layouts
- Real-time collaborative cursors
- Onboarding tour / first-run wizard (Phase 5 candidate)

## Mid-discussion correction

User asked about admin login key during discussion (out of phase scope but immediate need). Discovered admin.html uses `X-Admin-Key` header against `/v1/acn/admin/applications`, NOT JWT user/password. Memory had recorded the same key but mislabeled it. Corrected: `AGENTHUB_ACN_ADMIN_KEY=ak_21c4f9...` is the value to enter. JWT user/password (`omer` / `OpenHub2026!`) are env vars for the future Phase 4 UI's login form, NOT for admin.html. This distinction will matter when Phase 4 ships and both flows coexist.
