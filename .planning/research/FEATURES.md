# Feature Landscape

**Domain:** Multi-agent AI coordination platform / self-hosted command center
**Researched:** 2026-04-07
**Scope:** OpenHub v1.0 open source release - command center UI, WebSocket, vector DB, tests, docs

---

## Table Stakes

Features users expect from a coordination platform. Missing any of these and users leave or don't adopt.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Live agent status board | Operators need to know what's running, idle, dead - without refreshing | Medium | Online/offline/idle states with last-seen timestamp. WebSocket-driven. |
| Task list with status and owner | Primary work surface - what's queued, claimed, running, done | Medium | Filterable by status, agent, time range. |
| Real-time updates (no polling) | DevOps dashboards that require page refresh feel broken in 2026 | Medium | WebSocket events push state changes; React state updates in-place. |
| Task create + cancel from UI | Users must be able to dispatch and abort work from the command center | Low-Medium | Forms for create; cancel button on running tasks. |
| Agent detail view | See capabilities, current task, heartbeat history, error rate for a specific agent | Low | Drilldown from agent list. |
| Workflow visualization | DAG-based workflows are opaque without a visual step-by-step trace | Medium | Step list with status badges is sufficient for v1.0; graph layout is v2. |
| Authentication gate | UI must require login - hub is exposed over network | Low | JWT login form; token stored in httpOnly cookie or memory, not localStorage. |
| One-command setup | `docker compose up` or `pip install openhub && openhub start` - no multi-step config | Low | Docker Compose already exists; pip install wrapper is new. |
| Health / connectivity indicator | Users need to know if hub itself is reachable | Very Low | Top-bar status chip using `/v1/health`. |
| Structured error display | Errors in task/agent operations must surface in UI, not silently fail | Low | Toast notifications or inline error states, not just console logs. |
| API documentation | Developers integrating agents need endpoint reference | Low | FastAPI auto-generates OpenAPI; expose `/docs` and link from README. |
| README with quickstart | First thing every potential adopter reads | Low | 5-minute from-zero-to-running guide with Docker and pip paths. |
| MIT or Apache 2 license | Open source adopters won't use projects with ambiguous licensing | Very Low | Must be present and clearly stated before v1.0 tag. |

---

## Differentiators

Features that create genuine competitive advantage. Users don't expect them but value them strongly once they see them.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Multi-IDE agent support | Works with Claude Code, Cursor, Copilot, not locked to one vendor | Low (already built) | The bridge/ACN onboarding model is the differentiator - surface this prominently in docs. |
| Capability-based task routing | Tasks go to the agent best equipped to handle them, not just any free agent | Low (already built) | Expose the match score in the UI so users trust the routing decision. |
| Cost tracking per agent | Real-time spend visibility per agent - rare in self-hosted tools | Medium | Already in backend (P1); surface total cost, cost per task in dashboard. |
| Resource locks with deadlock prevention | Prevents two agents touching the same file simultaneously | Low (already built) | Show active locks on a dedicated panel; lock conflicts surface as warnings. |
| Shared context/memory store | Agents read each other's intermediate outputs - true coordination not just task dispatch | Low (already built) | Show memory keys/values in UI with size/age metadata. |
| Distributed tracing per task | See every step an agent took on a task - tool calls, sub-steps, timing | Medium | Already in backend (P1 tracing); UI trace viewer is the new work. |
| MCP tool sharing | Agents share tool definitions via the hub rather than each embedding them | Low (already built) | Highlight in README - this is genuinely rare in open source. |
| Dead letter queue with retry | Failed tasks don't disappear - they land in DLQ and can be retried from UI | Low (already built) | DLQ panel with manual retry button is the UI work. |
| Semantic search over context (vector DB) | Find relevant past context by meaning, not exact key - enables smarter agent coordination | High | New; use a lightweight local vector DB (ChromaDB or similar); v1.0 can ship as optional/beta. |
| Mobile-responsive command center | Operators can check agent status from phone - most dashboards ignore mobile | Medium | Responsive layout with Tailwind; table-to-card transforms at breakpoints. |
| Invite-based agent onboarding | Single-use invite codes for remote agents - secure without complex IAM | Very Low (already built) | Show invite flow in UI; make it obvious in docs. This is a clean UX. |

---

## Anti-Features

Things to deliberately NOT build for v1.0. Each one is tempting but wrong for this stage.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Visual workflow builder (drag-drop DAG) | 3-4x complexity of a read-only workflow view; CrewAI/n8n already do this; not OpenHub's advantage | Ship step-list view with status badges. Workflow creation stays API/code-based for v1.0. |
| Prompt editing / LLM model config in UI | Scope creep into LLM management - that's not what OpenHub coordinates | Agents manage their own LLM config. Hub coordinates tasks, not prompts. |
| Multi-tenancy / team management | Multiple orgs sharing one hub instance requires auth overhaul - PROJECT.md explicitly out of scope | Single-instance, single-owner for v1.0. Document this clearly. |
| OAuth / SSO (GitHub, Google login) | Adds 2+ weeks of auth work; JWT + API keys cover the self-hosted use case | Ship with username/password JWT. Add SSO only if community demands it. |
| Agent code execution sandbox | Running untrusted agent code is a security scope unto itself | Agents run in their own process; hub coordinates, never executes agent code. |
| Plugin/extension marketplace | Premature at v1.0 - creates maintenance burden before core is stable | Focus on stable API contracts first; community plugins come after. |
| Hosted / SaaS offering | Project scope is self-hosted open source only - hybrid model creates confusion | Keep it purely self-hosted. Cloud is a v2+ business decision. |
| Real-time log streaming (shell-level) | Log aggregation is solved by Grafana/Loki; building it here is pure scope creep | Emit structured JSON logs; let users point their own log aggregator at them. |
| Native mobile app (iOS / Android) | PROJECT.md explicitly defers to v2; responsive web reaches the same audience | Responsive React SPA covers mobile browsers for v1.0. |
| AI-powered anomaly detection / alerting | Interesting but complex; well-served by external tools like Grafana alerts | Surface raw metrics in UI; users wire their own alerting. |

---

## Feature Dependencies

```
JWT login form              -> all protected UI pages
WebSocket connection        -> live agent status board
WebSocket connection        -> task list real-time updates
WebSocket connection        -> workflow step progress
Agent list + detail view    -> task create (need agent to assign to)
Task list                   -> DLQ panel (DLQ is a filtered task view)
Cost tracking display       -> agent detail view (cost is per-agent)
Tracing UI                  -> task detail view (trace is attached to a task)
Resource lock panel         -> agent detail view (locks are per-agent context)
Shared memory viewer        -> standalone panel (memory is global context)
Vector DB integration       -> semantic search in memory/context panel
Docker Compose working      -> pip install path (validate config model first)
OpenAPI /docs exposed       -> API documentation (FastAPI auto-generates, just expose it)
```

---

## MVP Recommendation for v1.0

The platform backend is mature. The gap is visibility and control. Prioritize ruthlessly:

**Must ship (blocking v1.0):**
1. Live agent status board with WebSocket updates
2. Task list with real-time status changes and create/cancel actions
3. Workflow step-list view (read-only, status badges)
4. JWT login + auth gate
5. Agent detail drilldown (capabilities, current task, cost summary)
6. DLQ panel with manual retry
7. Health indicator
8. Comprehensive test suite (backend unit + integration; zero tests currently is the biggest stability risk)
9. README quickstart + API docs link

**Ship as beta/optional in v1.0:**
10. Vector DB semantic search (ChromaDB, opt-in, documented as experimental)
11. Distributed trace viewer in task detail

**Defer to v1.x (post-launch):**
- Resource lock panel (nice to have, not critical for initial adopters)
- Shared memory key/value viewer (useful but secondary)
- Full mobile responsive polish (get core working first, then polish breakpoints)
- Cost breakdown charts (surface number first, chart later)

**Rationale for ordering:**
- Agent status + task list + WebSocket are the core loop. Without these, the UI has no value.
- Auth gate is required before any public URL exposure.
- Tests must land before v1.0 tag - a platform with zero tests cannot be trusted in production by OSS adopters.
- Vector DB is genuinely differentiating but also genuinely complex; opt-in beta ships without blocking release.
- Docs and README are not optional - OSS adoption lives or dies on first impressions.

---

## Sources

- [AI Agent Dashboard Platforms 2026 Comparison](https://thecrunch.io/ai-agent-dashboard/) - MEDIUM confidence
- [120+ Agentic AI Tools Mapped 2026 - StackOne](https://www.stackone.com/blog/ai-agent-tools-landscape-2026/) - MEDIUM confidence
- [State of Agent Engineering - LangChain](https://www.langchain.com/state-of-agent-engineering) - HIGH confidence (official LangChain)
- [LLM Observability Tools - LangChain](https://www.langchain.com/articles/llm-observability-tools) - HIGH confidence
- [CrewAI Open Source](https://crewai.com/open-source) - HIGH confidence (official)
- [AG-UI Overview](https://docs.ag-ui.com/introduction) - HIGH confidence (official docs)
- [How to Build Real-Time Dashboards with React and WebSockets](https://www.wildnetedge.com/blogs/building-real-time-dashboards-with-react-and-websockets) - MEDIUM confidence
- [WebSockets in React 2026 - OneUptime](https://oneuptime.com/blog/post/2026-01-15-websockets-react-real-time-applications/view) - MEDIUM confidence
- [The Mythical Agent-Month - O'Reilly](https://www.oreilly.com/radar/the-mythical-agent-month/) - HIGH confidence (scope creep analysis)
- [Best Self-Hosted AI Agent Platforms 2025 - Fast.io](https://fast.io/resources/best-self-hosted-ai-agent-platforms/) - MEDIUM confidence
- [n8n Self-Hosted AI Starter Kit](https://github.com/n8n-io/self-hosted-ai-starter-kit) - HIGH confidence (official GitHub)
