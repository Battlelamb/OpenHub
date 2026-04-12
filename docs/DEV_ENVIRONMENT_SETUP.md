# OpenHub - Development Environment Setup Guide

Complete setup guide for replicating the development environment on a new machine.

## 1. Prerequisites

### System Requirements
- **OS:** WSL2 (Ubuntu) on Windows, or native Linux
- **Node.js:** v25.x (via nvm)
- **Python:** 3.12.x
- **Git:** 2.x+

### Install nvm + Node.js
```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
source ~/.bashrc
nvm install 25
nvm use 25
```

### Install Python 3.12
```bash
sudo apt update && sudo apt install -y python3.12 python3.12-venv python3-pip
```

---

## 2. Claude Code CLI

### Install
```bash
# Via npm (requires Node.js)
npm install -g @anthropic-ai/claude-code

# Or via pip
pip install claude-code
```

### Configure
```bash
# Login
claude login

# Set permission mode (we use dontAsk for productivity)
# This is set in ~/.claude/settings.json
```

### Key Settings (~/. claude/settings.json)
```json
{
  "permissions": {
    "defaultMode": "dontAsk",
    "additionalDirectories": ["/home/omer"]
  },
  "skipDangerousModePermissionPrompt": true,
  "effortLevel": "max"
}
```

---

## 3. GSD (Get Shit Done) - Project Management Framework

GSD is the core workflow engine we use for planning, executing, and verifying all work.

### Install
```bash
# Install via Claude Code skill system
claude "/install get-shit-done-cc"

# Or manually from the skill repo:
# The skill lives at ~/.claude/skills/gsd/
# Version: 1.28.0
```

### What GSD Provides
- **Workflows:** discuss-phase, plan-phase, execute-phase, verify-work, debug
- **Agents:** gsd-executor, gsd-planner, gsd-verifier, gsd-plan-checker, gsd-phase-researcher, gsd-debugger, etc.
- **Hooks:** context-monitor, prompt-guard, statusline, check-update, workflow-guard
- **Tools:** gsd-tools.cjs (CLI for state management, roadmap ops, commits)

### GSD Commands We Use
```
/gsd:new-project          -- Initialize project with .planning/ structure
/gsd:discuss-phase N      -- Capture design decisions before planning
/gsd:plan-phase N         -- Research + plan + verify loop
/gsd:execute-phase N      -- Execute plans with parallel agents
/gsd:progress             -- Check project status
/gsd:verify-work N        -- Manual testing / UAT
/gsd:review --phase N     -- Cross-AI peer review
/gsd:debug                -- Systematic debugging
/gsd:quick                -- Small tasks without full planning
/gsd:fast                 -- Trivial inline tasks
/gsd:resume-work          -- Restore context from previous session
/gsd:ship                 -- Create PR after verification
```

### GSD Hooks (auto-installed by GSD skill)
Located at `~/.claude/hooks/`:
- `gsd-check-update.js` -- SessionStart: checks for GSD updates
- `gsd-context-monitor.js` -- PostToolUse: monitors context usage
- `gsd-prompt-guard.js` -- PreToolUse: guards against editing outside GSD workflow
- `gsd-statusline.js` -- Status bar showing current phase/plan
- `gsd-workflow-guard.js` -- Workflow enforcement

---

## 4. External AI CLIs (for cross-AI reviews)

### Gemini CLI
```bash
npm install -g @google/gemini-cli
# Version: 0.33.2

# Configure API key:
# Create ~/.gemini/settings.json with GEMINI_API_KEY
# Or set env: export GEMINI_API_KEY=your-key
```

### OpenAI Codex CLI
```bash
npm install -g @openai/codex
# Version: 0.115.0

# Configure: export OPENAI_API_KEY=your-key
```

### Usage
```bash
# Cross-AI review of plans
/gsd:review --phase N --all
```

---

## 5. Claude Code Plugins (Enabled)

These plugins are enabled in `~/.claude/settings.json` under `enabledPlugins`.
They auto-install on first use.

### Official Plugins (@claude-plugins-official)
| Plugin | Purpose |
|--------|---------|
| `superpowers` | Code review, brainstorming, parallel agents, TDD, plan execution |
| `context7` | Library documentation fetching (React, FastAPI, etc.) |
| `frontend-design` | UI component design and implementation |
| `code-simplifier` | Code cleanup and refactoring |
| `code-review` | PR and code review workflows |
| `feature-dev` | Feature architecture and development |
| `playwright` | Browser automation and E2E testing |
| `typescript-lsp` | TypeScript language server |
| `pyright-lsp` | Python type checking |
| `rust-analyzer-lsp` | Rust language server |
| `claude-md-management` | CLAUDE.md file management |
| `skill-creator` | Create and manage custom skills |
| `serena` | Semantic code navigation |
| `claude-code-setup` | Automation recommendations |
| `ralph-loop` | Recurring task loops |
| `firecrawl` | Web scraping and crawling |

### Knowledge Work Plugins (@knowledge-work-plugins)
```json
"extraKnownMarketplaces": {
  "knowledge-work-plugins": {
    "source": {
      "source": "github",
      "repo": "anthropics/knowledge-work-plugins"
    }
  }
}
```

| Plugin | Purpose |
|--------|---------|
| `enterprise-search` | Cross-source search (Slack, docs, etc.) |
| `data` | SQL queries, data analysis, dashboards |
| `engineering` | Tech debt, debugging, architecture, deployment |

---

## 6. MCP Servers

### Cloud MCP Integrations (via claude.ai account)
These are connected through your Claude account settings at claude.ai/settings/integrations.
They auto-sync when you login.

| Integration | Used For |
|-------------|----------|
| Context7 | Library docs (FastAPI, Pydantic, etc.) |
| Slack | Team communication |
| Linear | Issue tracking |
| Gmail | Email |
| Google Calendar | Scheduling |
| Notion | Documentation |
| Supabase | Database management |
| Cloudflare | CDN and edge functions |
| Hugging Face | AI model hub |
| Airtable | Structured data |
| HubSpot | CRM |
| Canva | Design |
| Microsoft Learn | MS documentation |
| Mermaid Chart | Diagram rendering |
| Base44 | App building |

### Local MCP Servers (in settings.json > mcpServers)
```json
{
  "hostinger-mcp": {
    "command": "npx",
    "args": ["hostinger-api-mcp@latest"],
    "env": {
      "API_TOKEN": "<your-hostinger-api-token>"
    }
  }
}
```

### Plugin-Provided MCP Servers (auto-managed by plugins)
These are automatically started by their respective plugins:
- **playwright** -- Browser automation (mcp__playwright__*)
- **serena** -- Semantic code analysis (mcp__plugin_serena_serena__*)
- **filesystem** -- File operations (mcp__filesystem__*)
- **memory** -- Knowledge graph (mcp__memory__*)
- **git** -- Git operations (mcp__git__*)
- **fetch** -- HTTP requests (mcp__fetch__*)
- **context7** -- Library docs (mcp__context7__*)
- **perplexity** -- Web search (mcp__perplexity__*)
- **firecrawl** -- Web scraping (mcp__firecrawl__*)
- **sequentialthinking** -- Step-by-step reasoning (mcp__sequentialthinking__*)
- **socket** -- Dependency security (mcp__socket__*)
- **time** -- Time utilities (mcp__time__*)
- **puppeteer** -- Browser control (mcp__puppeteer__*)
- **chrome-devtools** -- Chrome debugging (mcp__chrome-devtools__*)
- **browsermcp** -- Browser snapshots (mcp__browsermcp__*)
- **browser-use** -- Browser agent (mcp__browser-use__*)

---

## 7. Custom Skills

Located at `~/.claude/skills/`:

### GSD Skill (`~/.claude/skills/gsd/`)
- Main workflow engine
- Includes all GSD commands, agents, hooks, templates
- Auto-updates on session start

### Agent Reach (`~/.claude/skills/agent-reach/`)
- Multi-platform search (Twitter, Reddit, YouTube, GitHub, etc.)
- SKILL.md defines the interface

---

## 8. Custom Agents

Located at `~/.claude/agents/` - 30 specialized agents:

### General Purpose
| Agent | Purpose |
|-------|---------|
| `ai-research-analyst` | Research papers, competitive analysis |
| `backend-api-engineer` | API design, server logic |
| `browser-automation-expert` | E2E testing, web scraping |
| `business-productivity-coach` | Professional communication |
| `cloud-infrastructure-architect` | AWS, CDK, serverless |
| `code-quality-auditor` | Security, performance, debugging |
| `creative-media-producer` | Image/video/creative content |
| `data-document-processor` | OCR, data extraction |
| `document-automation-specialist` | Word, Excel, PowerPoint |
| `frontend-ui-designer` | React, Tailwind, dashboards |
| `full-stack-developer` | End-to-end feature dev |
| `git-github-workflow-manager` | Git ops, PRs, CI/CD |

### GSD Agents (used by /gsd: commands)
| Agent | Purpose |
|-------|---------|
| `gsd-executor` | Executes plans, atomic commits |
| `gsd-planner` | Creates detailed plans |
| `gsd-verifier` | Verifies phase goal achievement |
| `gsd-plan-checker` | Reviews plan quality |
| `gsd-phase-researcher` | Researches technical approaches |
| `gsd-debugger` | Systematic debugging |
| `gsd-codebase-mapper` | Maps project structure |
| `gsd-integration-checker` | Cross-phase integration |
| `gsd-nyquist-auditor` | Validation coverage |
| `gsd-project-researcher` | Domain ecosystem research |
| `gsd-research-synthesizer` | Synthesizes research outputs |
| `gsd-roadmapper` | Creates project roadmaps |
| `gsd-advisor-researcher` | Gray area decisions |
| `gsd-assumptions-analyzer` | Surfaces assumptions |
| `gsd-user-profiler` | Developer behavioral profile |
| `gsd-ui-researcher` | UI/UX research |
| `gsd-ui-checker` | UI quality review |
| `gsd-ui-auditor` | UI design audit |

---

## 9. Project-Specific Setup (OpenHub)

### Clone and Setup
```bash
git clone https://github.com/Battlelamb/OpenHub.git
cd OpenHub
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Run Dev Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 7788 --reload
```

### Run Tests
```bash
AGENTHUB_ADMIN_USER=test AGENTHUB_ADMIN_PASSWORD=test \
  .venv/bin/python -m pytest tests/ -v --tb=short
```

### Project Branch Structure
- `master` -- Main branch
- `gsd/phase-01-backend-hardening` -- Phase 1 (completed)
- `gsd/phase-02-websocket-test-suite` -- Phase 2 (planned, ready to execute)

### Current State
- Phase 1: Backend Hardening -- COMPLETE (9/9 plans)
- Phase 2: WebSocket + Test Suite -- PLANNED (6 plans, 3 waves, ready to execute)
- All planning artifacts in `.planning/` directory

---

## 10. Quick Setup Script (New Machine)

```bash
#!/bin/bash
# Run this on a fresh WSL2/Linux machine

# 1. Node.js
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
source ~/.bashrc
nvm install 25 && nvm use 25

# 2. Python
sudo apt update && sudo apt install -y python3.12 python3.12-venv python3-pip

# 3. Claude Code
npm install -g @anthropic-ai/claude-code
claude login

# 4. AI CLIs (for cross-AI reviews)
npm install -g @google/gemini-cli @openai/codex

# 5. GSD installs automatically on first /gsd: command
# Or manually: claude "/install get-shit-done-cc"

# 6. Clone project
git clone https://github.com/Battlelamb/OpenHub.git
cd OpenHub
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 7. Resume work
claude
# Then run: /gsd:resume-work
```

---

## 11. Important Notes

- **Claude settings sync:** `~/.claude/settings.json` does NOT sync across machines. You need to manually copy or recreate it.
- **Cloud MCPs:** These sync via your claude.ai account. Just login on the new machine.
- **Plugins:** Auto-install on first use once listed in `enabledPlugins`.
- **GSD hooks:** Auto-installed by the GSD skill.
- **API keys:** Gemini and Codex need their API keys configured separately.
- **Hostinger MCP:** Needs API token in mcpServers config.

---

*Generated: 2026-04-11*
*Source machine: WSL2 @ /home/omer*
