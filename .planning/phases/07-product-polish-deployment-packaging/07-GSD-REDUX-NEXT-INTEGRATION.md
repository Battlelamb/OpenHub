# GSD Redux `next` Integration

**Status:** Complete  
**Completed:** 2026-05-25T06:48:49Z  
**Slice type:** GSD runtime/tooling integration  
**Source:** `https://github.com/open-gsd/get-shit-done-redux/tree/next`  
**Source commit:** `dc4b90ae4b202007524e0576ff92b010b7460567`  
**Package:** `@opengsd/get-shit-done-redux@1.0.0`

## Objective

Refresh OpenHub's repository-local GSD runtime surfaces from the upstream `open-gsd/get-shit-done-redux` `next` branch so the codebase carries current Claude Code and Hermes Agent GSD workflows, agents, manifests, hooks, and runtime helper files.

## Integration command

```bash
node /tmp/get-shit-done-redux-next/bin/install.js \
  --claude \
  --hermes \
  --local \
  --profile=full \
  --portable-hooks
```

## Changes

- Installed repository-local Claude Code GSD surface under `.claude/`.
- Installed repository-local Hermes Agent GSD surface under `.hermes/`.
- Set both runtime profiles to `full` for a complete local agent/workflow surface.
- Installed:
  - 67 Claude Code GSD commands.
  - 67 Hermes Agent GSD skills.
  - 33 Claude Code GSD agents.
  - 33 Hermes Agent GSD agents.
- Updated local GSD runtime helper code and manifests under:
  - `.claude/get-shit-done/`
  - `.hermes/get-shit-done/`
  - `.claude/gsd-file-manifest.json`
  - `.hermes/gsd-file-manifest.json`
- Added `workflow.ai_integration_phase = true` to `.planning/config.json` so the new health validator no longer has to rely on the implicit default.
- Corrected the generated Hermes Agent `surface` skill text so it points at the repository-local Hermes config root (`/home/brunhilde/OpenHub/.hermes`) instead of stale Claude config path wording.

## Verification evidence

```bash
# Upstream source snapshot
branch=next
commit=dc4b90ae4b202007524e0576ff92b010b7460567
package=@opengsd/get-shit-done-redux@1.0.0

# Artifact inventory
claude_profile=full
hermes_profile=full
claude_version=1.0.0
hermes_version=1.0.0
claude_commands=67
hermes_skills=67
claude_agents=33
hermes_agents=33

# Config syntax
OK .gsdrc.toml
OK .planning/config.json
OK .gsd/provider-config.json
OK .claude/settings.json
OK .hermes/settings.json
OK .claude/gsd-file-manifest.json
OK .hermes/gsd-file-manifest.json
OK .claude/package.json
OK .hermes/package.json

# GSD probes
gsd-sdk v1.42.3
model_profile=balanced
workflow.ai_integration_phase=true
validate_health=healthy warnings=0 errors=0
validate_consistency=passed
progress_percent=89

# Hermes generated-path sanity
hermes_claude_path_refs=none

# Git whitespace check
diff_check=ok

# Secret scan across changed files
scanned_files=453
secret_scan_hits=none
```

## Notes

- The installer warned that `sdk/dist/cli.js` was missing from the temporary git clone, so it skipped local SDK deployment. Existing global `gsd-sdk v1.42.3` remains available and was used for verification.
- The installer also skipped graphify auto-hook installation because the target hook script was not present. Core GSD health and consistency checks still pass.
- No app runtime code was changed in this slice; the change is limited to local agent/workflow/tooling surfaces and planning config.

## Result

OpenHub now carries the `get-shit-done-redux` `next` branch GSD surface locally for both Claude Code and Hermes Agent, with full workflow and agent coverage and clean validation evidence.
