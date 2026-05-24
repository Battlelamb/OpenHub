# Phase 07 Context: Product Polish + Deployment Packaging

## Why this phase exists

Phase 05 made OpenHub releasable. Phase 06 made Tasks/Kanban/Workflow Canvas real and verified. Phase 07 is the sober polish pass: remove misleading dashboard states, align docs with the live deployment, and make the next release/tag decision evidence-based.

## Current truths

- Repo: `/home/brunhilde/OpenHub`
- Remote: `https://github.com/Battlelamb/OpenHub.git`
- Branch: `master`
- Current HEAD at phase open: `993622b`
- Live hub: `https://hub.brunhilde.cloud`
- Runtime: `openhub-api.service` active, `openhub-bridge-brunhilde.service` active
- Legacy duplicate bridge: `openhub-bridge.service` disabled/dead
- ACN live status at phase open: 1 node / 1 agent (`brunhilde`) online
- GSD: installed, valid config, secret scan clean

## Operating rules

- Small GSD slices only.
- Do not claim UI/product completion from visuals alone.
- Backend-wired + tested + pushed + live-smoked is the completion bar.
- Preserve secrets; never print `ak_...`, `oh_...`, provider keys, or Cloudflare tunnel tokens.
- Prefer ACN status/health as source of truth for OpenHub agent visibility.
- Keep Claude Code/GSD default at Opus/max effort when using Claude.

## Known issue class to hunt

- Dashboard views that still read legacy endpoints and show zero/empty state while ACN is healthy.
- Planning/docs that claim old service names or pre-Phase-06 state.
- Verification commands that reference missing tools or stale test paths.
- Release docs that say an install path works without current smoke evidence.
- Runtime ops docs that omit the active bridge unit name or the disabled legacy bridge cleanup.

## Phase 07 done means

- Dashboard truth audit/fixes complete.
- Docs and packaging paths match the real live deployment and current repo state.
- Verification commands are accurate and reproducible.
- Runtime service docs are secret-safe and operationally useful.
- Full verification evidence is recorded before any next tag/release.
