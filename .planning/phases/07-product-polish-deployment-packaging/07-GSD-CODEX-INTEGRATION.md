# GSD Redux Codex Runtime Integration

**Status:** Complete  
**Completed:** 2026-05-25T07:00:37Z  
**Slice type:** GSD runtime/tooling integration  
**Source:** `https://github.com/open-gsd/get-shit-done-redux/tree/next`  
**Source commit:** `dc4b90ae4b202007524e0576ff92b010b7460567`  
**Package:** `@opengsd/get-shit-done-redux@1.0.0`

## Objective

Add Codex as a third repository-local GSD runtime for OpenHub so Claude Code, Hermes Agent, and Codex can share the same GSD phase/workflow discipline while Codex is available for focused implementation, refactor, and review slices.

## Preconditions

```bash
codex_path=/home/brunhilde/.npm-global/bin/codex
codex_version=codex-cli 0.132.0
codex_auth=present
source_branch=next
source_commit=dc4b90ae4b202007524e0576ff92b010b7460567
source_package=@opengsd/get-shit-done-redux@1.0.0
```

## Integration command

```bash
node /tmp/get-shit-done-redux-next/bin/install.js \
  --codex \
  --local \
  --profile=full \
  --portable-hooks
```

## Changes

- Installed repository-local Codex GSD surface under `.codex/`.
- Set Codex runtime profile to `full`.
- Installed:
  - 67 Codex GSD skills.
  - 33 Codex GSD agent markdown files.
  - 33 Codex GSD agent TOML config files.
- Generated `.codex/config.toml` with GSD-managed agent roles.
- Installed Codex runtime helper code and manifest under:
  - `.codex/get-shit-done/`
  - `.codex/gsd-file-manifest.json`
- Corrected the generated Codex `gsd-surface` skill text so it points at the repository-local Codex config root (`/home/brunhilde/OpenHub/.codex`) instead of stale Claude config path wording.

## Verification evidence

```bash
# Artifact inventory
codex_profile=full
codex_version=1.0.0
codex_skills=67
codex_agents_md=33
codex_agents_toml=33
codex_config=present
codex_manifest=present

# Syntax
OK .codex/config.toml
OK .codex/gsd-file-manifest.json

# GSD probes through Codex surface
validate_health=healthy warnings=0 errors=0
validate_consistency=passed
progress_percent=89

# Generated-path sanity
codex_claude_path_refs=none

# Codex CLI
codex-cli 0.132.0
codex_exec_help_checked=ok

# Git whitespace
diff_check=ok

# Secret scan
scanned_files=453
secret_scan_hits=none
```

## Operational use

- Claude/Hermes remain the orchestration and continuity surfaces.
- Codex is now available as a GSD-aligned coding worker for narrow implementation/refactor/review work.
- Recommended invocation for focused slices:

```bash
codex exec --full-auto 'Use the local GSD plan context. Implement the single requested OpenHub slice, update tests, and stop after verification evidence.'
```

Codex should be launched from `/home/brunhilde/OpenHub` so it sees the repository-local `.codex/` GSD surface and the git worktree.

## Notes

- The installer warned that `sdk/dist/cli.js` was missing from the temporary git clone, so local SDK deployment was skipped. Existing GSD tooling remains available and Codex-surface health/consistency passed.
- The installer skipped Codex SessionStart hook registration because `gsd-check-update.js` was not present at the target. This does not block the local GSD surface or agent config from being used.
- No application runtime code was changed in this slice; the change is limited to local agent/workflow/tooling surfaces and documentation.

## Result

OpenHub now carries the `get-shit-done-redux` `next` branch Codex surface locally, alongside the existing Claude Code and Hermes Agent GSD surfaces.
