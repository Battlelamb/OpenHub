# Phase 4 - Plan 02 Summary: App Shell

**Phase:** 04-command-center-ui  
**Plan:** 02 - App Shell  
**Wave:** 2  
**Date:** 2026-04-13  
**Status:** ✅ Complete

---

## Executive Summary

Built the frontend app shell: sidebar + topbar + theme provider + i18n init + reconnecting banner. All layout tokens match UI-SPEC.md. Tests green, build green.

---

## Layout Tokens (Verbatim from UI-SPEC)

| Token | Value | Usage |
|-------|-------|-------|
| Sidebar expanded width | `w-64` (256px) | Desktop sidebar |
| Sidebar collapsed width | `w-14` (56px) | Collapsed sidebar |
| Topbar height | `h-14` (56px) | Topbar header |
| Base color | `zinc` | Backgrounds, borders, text |
| Accent color | `emerald-500` | Brand, active states, health |
| Border color | `border-zinc-800` | Sidebar/Topbar borders |
| Background | `bg-zinc-900` | Sidebar/Topbar |
| Page background | `bg-zinc-950` | Main content area |

---

## Sidebar Navigation Items

### Operations Group
- `/agents` — Agents (Users icon)
- `/tasks` — Tasks (ListChecks icon)
- `/workflows` — Workflows (GitBranch icon)

### Visibility Group
- `/dlq` — DLQ (AlertCircle icon)
- `/costs` — Costs (DollarSign icon)
- `/traces` — Traces (Activity icon)
- `/memory` — Memory (Database icon)
- `/locks` — Locks (Lock icon)

### Admin Group
- `/health` — Health (Heart icon)
- `/settings` — Settings (Settings icon)

**Total:** 10 nav items across 3 groups

---

## i18n Namespaces Shipped

### `common` namespace (EN + TR)
- `brand`, `signIn`, `signOut`, `loading`
- `signInTitle`, `invalidCredentials`
- `healthOk`, `healthFail`
- `reconnecting`, `tokenExpiring`
- `themeToLight`, `themeToDark`
- `language`, `requestFailed`, `networkError`

### `nav` namespace (EN + TR)
- `groups.operations`, `groups.visibility`, `groups.admin`
- `items.agents`, `items.tasks`, `items.workflows`
- `items.dlq`, `items.costs`, `items.traces`
- `items.memory`, `items.locks`
- `items.health`, `items.settings`

**Languages:** English (default), Turkish (browser detection)  
**Init:** Synchronous, no Suspense (`useSuspense: false`)

---

## shadcn Primitives Installed

| Component | File | Exports |
|-----------|------|---------|
| Button | `src/components/ui/button.tsx` | `Button`, `buttonVariants` |
| Sheet | `src/components/ui/sheet.tsx` | `Sheet`, `SheetContent`, `SheetTrigger`, etc. |
| Tooltip | `src/components/ui/tooltip.tsx` | `Tooltip`, `TooltipContent`, `TooltipTrigger`, `TooltipProvider` |
| Separator | `src/components/ui/separator.tsx` | `Separator` |
| Dropdown Menu | `src/components/ui/dropdown-menu.tsx` | `DropdownMenu`, `DropdownMenuContent`, `DropdownMenuItem`, etc. |

**Additional Radix deps installed:**
- `@radix-ui/react-dialog` (for Sheet)
- `@radix-ui/react-tooltip` (for Tooltip)
- `@radix-ui/react-separator` (for Separator)
- `@radix-ui/react-dropdown-menu` (auto-installed)

---

## Files Created/Modified

### New Files (21)
- `src/stores/ui-store.ts` — Zustand UI state
- `src/stores/ui-store.test.ts` — 5 tests
- `src/hooks/useTheme.ts` — Theme sync hook
- `src/i18n/index.ts` — i18next init
- `src/locales/en/nav.json` — English nav copy
- `src/locales/tr/nav.json` — Turkish nav copy
- `src/components/layout/ThemeProvider.tsx`
- `src/components/layout/ReconnectingBanner.tsx`
- `src/components/layout/Sidebar.tsx`
- `src/components/layout/Topbar.tsx`
- `src/components/layout/AppShell.tsx`
- `src/components/ui/button.tsx` (shadcn)
- `src/components/ui/sheet.tsx` (shadcn)
- `src/components/ui/tooltip.tsx` (shadcn)
- `src/components/ui/separator.tsx` (shadcn)
- `src/components/ui/dropdown-menu.tsx` (shadcn)
- `src/App.tsx` (placeholder)

### Modified Files (3)
- `src/locales/en/common.json` — extended with 11 new keys
- `src/locales/tr/common.json` — extended with 11 new keys
- `src/routes/__root.tsx` — added ThemeProvider + i18n import

---

## Verification Results

### Tests
```
npm run test -- --run
✓ src/lib/cn.test.ts (3 tests)
✓ src/stores/ui-store.test.ts (5 tests)
Total: 8/8 passing
```

### Typecheck
```
npm run typecheck → ✅ exits 0
```

### Build
```
npm run build → ✅ exits 0
dist/index.html, dist/assets/index-*.js, dist/assets/index-*.css produced
```

---

## Known Issues & Resolutions

### Issue 1: Missing Radix Dependencies
**Problem:** shadcn CLI didn't auto-install all `@radix-ui/*` peer deps.  
**Resolution:** Manually installed `@radix-ui/react-dialog`, `@radix-ui/react-tooltip`, `@radix-ui/react-separator` after typecheck failures.  
**Impact:** None — all components now type-check correctly.

---

## Next Steps

**Plan 04-03 (Auth Layer) Ready:**
- `src/stores/auth-store.ts` — in-memory JWT store
- `src/lib/api-client.ts` — fetch wrapper with auth headers
- `src/lib/router-ref.ts` — router indirection for 401 redirects
- `src/routes/login.tsx` — public login page
- `src/routes/_authed.tsx` — auth guard wrapper
- `src/components/forms/LoginForm.tsx` — react-hook-form + zod

**Plan 04-02 Complete.** App shell delivered. Wave 2 ready for parallel Auth Layer execution.
