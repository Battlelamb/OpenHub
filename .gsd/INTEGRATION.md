# GSD-2 Integration Guide for OpenHub

## Quick Start

### 1. Authenticate (Required)
```bash
cd /home/brunhilde/OpenHub
hermes auth list openai-codex
```
OpenHub GSD defaults use the local Hermes/OpenAI Codex OAuth credential. Do not store real credential values in repository files.

### 2. Start Working
```bash
# Auto mode - autonomous execution
gsd auto "Implement Phase 1 task: auth stub removal"

# Interactive mode
gsd "Work on backend hardening - heartbeat monitor"

# Quick tasks
gsd quick "Fix datetime.utcnow() in routes_agents.py"

# Debug issues
gsd debug "Task claim endpoint returns 500 error"
```

## Project Structure

```
OpenHub/
├── .gsd/                      # GSD-2 configuration
│   ├── PREFERENCES.md         # Stack, conventions, workflow
│   └── STATE.json             # Current milestone/slice/task state
├── .gsdrc.toml                # GSD-2 CLI configuration
├── .planning/                 # Legacy GSD v1 docs (preserved)
│   ├── PROJECT.md
│   ├── ROADMAP.md
│   └── phases/
├── app/                       # Main application
├── docs/                      # Specifications
└── tests/                     # Test suite
```

## Current Milestone

**v1.0 - Production Ready**

### Phase 1: Backend Hardening (8 tasks)
1. Test scaffold: pytest infrastructure
2. Auth stub removal, API key dep, capabilities JSON fix
3. Heartbeat monitor wiring
4. CORS lockdown, datetime.utcnow() partial fix
5. Alembic schema migration consolidation
6. RFC 7807 error format, OpenAPI /docs enabled
7. slowapi rate limiting, Prometheus metrics, structlog
8. Codebase-wide datetime.utcnow() sweep

### Upcoming Phases
- **Phase 2**: WebSocket + Test Suite
- **Phase 3**: Vector Database (can run parallel with Phase 2)
- **Phase 4**: Command Center UI (React + Vite)
- **Phase 5**: Release Readiness

## GSD Commands

### Workflow Commands
```bash
# Start autonomous work session
gsd auto "<task description>"

# Interactive chat mode
gsd "<message>"

# Quick fix (no full context)
gsd quick "<small task>"

# Debug/Investigate
gsd debug "<problem>"

# Transition to next phase
gsd transition "Complete Phase 1, move to Phase 2"

# Complete milestone
gsd complete-milestone "v1.0"
```

### Git Workflow
```bash
# Worktree isolation (automatic)
gsd --worktree "feature/auth-fix" "<task>"

# List worktrees
gsd worktree list

# Merge completed work
gsd worktree merge "<branch>"
```

### Session Management
```bash
# List past sessions
gsd sessions

# Resume most recent
gsd --continue

# Resume specific session
gsd sessions resume <session-id>
```

## Verification Commands

GSD-2 runs these after each task:
```bash
pytest                    # Run tests
mypy app/                 # Type check
flake8 app/               # Lint
black --check app/        # Format check
isort --check app/        # Import order check
```

## Model Routing (Optional)

Configure in `.gsdrc.toml`:
```toml
[model]
default = "gpt-5.5"
research = "gpt-5.5"
planning = "gpt-5.5"
implementation = "gpt-5.5"
verification = "gpt-5.5"
effort = "max"
reasoning_effort = "xhigh"
```

## Budget Controls (Optional)

```toml
[workflow]
budget_usd = 10.0           # Max spend per session
token_ceiling = 1000000     # Max tokens per session
```

## Integration with Existing Tools

### Claude Code
Your `CLAUDE.md` already has GSD markers. These work alongside GSD-2:
- `<!-- GSD:project-start -->` - Project context
- `<!-- GSD:stack-start -->` - Stack info
- `<!-- GSD:conventions-start -->` - Code style
- `<!-- GSD:architecture-start -->` - Architecture

### VS Code Extension
Install the GSD VS Code extension for:
- Session sidebar
- One-click worktree management
- Inline chat with GSD context

### MCP Server
GSD-2 can expose tools via MCP for other LLMs:
```bash
gsd mcp serve
```

## Migration Notes

### From GSD v1 → GSD-2
- `.planning/` preserved for reference
- `.gsd/` is the new active planning directory
- `STATE.json` replaces `STATE.md`
- GSD-2 CLI is standalone (not Claude Code-only)
- Worktree management built-in
- Budget tracking, cost monitoring, crash recovery

### What Changed
| GSD v1 | GSD-2 |
|--------|-------|
| Claude Code only | Standalone CLI |
| Prompt injection | Direct session control |
| `.planning/STATE.md` | `.gsd/STATE.json` |
| Manual git workflow | Built-in worktree management |
| No cost tracking | Token ledger, budget ceilings |
| No crash recovery | Automatic recovery, stuck detection |

## Troubleshooting

### "Not authenticated"
```bash
gsd auth login
```

### "Worktree already exists"
```bash
gsd worktree clean    # Remove stale worktrees
gsd worktree list     # See active worktrees
```

### "Session stuck"
```bash
gsd sessions          # List sessions
gsd sessions kill     # Kill stuck session
```

### "Model unavailable"
GSD-2 auto-fallbacks to next available model. Configure alternatives in `.gsdrc.toml`.

## Next Steps

1. **Authenticate**: `gsd auth login`
2. **Start Phase 1**: `gsd auto "Begin Phase 1 Backend Hardening - start with test scaffold"`
3. **Monitor progress**: Check `.gsd/STATE.json` for task status updates

## Resources

- Docs: https://gsd.build/docs
- GitHub: https://github.com/gsd-build/gsd-2
- Migration Guide: https://gsd.build/docs/migration
