# Phase 05 — GSD Operating Loop Context

Created: 2026-05-19 08:58 UTC

## Purpose

Continue OpenHub development using Get Shit Done (GSD) as the operating loop and Claude Code as the implementation runtime.

This phase is not a product rewrite. It is the development discipline for the next OpenHub slices:

1. refresh codebase and runtime state,
2. discuss/choose the next small slice,
3. write an executable plan,
4. execute in fresh context / worktree where useful,
5. verify with tests and smoke checks,
6. document evidence,
7. commit and push.

## Runtime Direction

- GSD installed locally for Claude Code in `.claude/`.
- GSD installed locally for Hermes Agent in `.hermes/`.
- Use core GSD profile to keep context load small.
- Preferred Claude Code invocation:

```bash
claude -p "<task>" --model opus --effort max --max-turns <n>
```

GSD's bundled model catalog resolves Anthropic `opus` to `claude-opus-4-7`.

## Credential State

Claude Code is installed, but live credential validation is currently blocked:

- `claude --version`: available (`2.1.80`).
- `claude auth status`: not logged in.
- `ANTHROPIC_API_KEY`: not present in the terminal environment.
- `CLAUDE_CODE_OAUTH_TOKEN`: not present in the terminal environment.

No secrets were written to repository files.

Before launching Claude Code execution, one of these must be true:

1. `ANTHROPIC_API_KEY` is exported into the shell/session running Claude Code, or
2. `claude auth login` / `claude auth login --console` has completed, or
3. a configured API-key helper is available to Claude Code.

## OpenHub Constraints

- Preserve the FastAPI + React + Turso/SQLite architecture.
- Do not replace OpenHub with GSD; use GSD to operate the work.
- Security-first: preserve known-good OpenHub keys and never print `ak_...`, `oh_...`, provider tokens, or connection strings.
- Verification-first: every implementation slice needs test evidence or an explicit bounded smoke check.
- Keep product direction: OpenHub is the hub-first, API/dashboard-first coordination layer for multi-agent software work.

## Immediate Next Work Candidates

1. **Release-readiness snapshot**
   - Git status, runtime health, backend test status, frontend typecheck/build status, docs freshness.
2. **GSD command surface for OpenHub**
   - Add project-specific GSD/Claude commands for snapshot, plan, execute, verify, and closeout.
3. **Coordinator-first dashboard slice**
   - Command Center UX inspired by Gastown/GSD benchmark notes.
4. **Stuck-work recovery UX**
   - Surface stale claimed tasks, expired leases, and recovery actions.
5. **Durable work-history UX**
   - Make agent/task/evidence history visible after chat/session loss.
