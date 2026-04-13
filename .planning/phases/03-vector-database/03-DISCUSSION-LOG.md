# Phase 3: Vector Database - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md - this log preserves the alternatives considered.

**Date:** 2026-04-12
**Phase:** 03-vector-database
**Areas discussed:** Embedding strategy, Storage + indexing approach, Auto-indexing hooks, Search API design, Turso scope

---

## Embedding Strategy

### Model Choice

| Option | Description | Selected |
|--------|-------------|----------|
| Local sentence-transformers | all-MiniLM-L6-v2, offline, free | |
| OpenAI text-embedding-3-small | API-based, higher quality, costs money | |
| Configurable (both supported) | Default local, OpenAI via env var | yes |

**User's choice:** Configurable

### Generation Mode

| Option | Description | Selected |
|--------|-------------|----------|
| Async background | Write returns immediately, embed later | yes |
| Sync inline | Write blocks on embedding | |
| You decide | Claude picks | |

**User's choice:** Async background

---

## Storage + Indexing

### Local Dev Behavior (Turso scope)

| Option | Description | Selected |
|--------|-------------|----------|
| Only vector features require Turso | Core app on SQLite, vector on Turso | |
| Entire app requires Turso | App won't start without Turso | |
| Turso preferred, SQLite fallback with limitations | Hybrid - warning at startup | yes |

**User's choice:** Turso preferred with SQLite fallback (clarification of "Turso first and always")

### Index Type

| Option | Description | Selected |
|--------|-------------|----------|
| DiskANN from day one | Scales to millions, VEC-03 compliant | yes |
| Brute-force first, DiskANN later | Simpler initial implementation | |
| You decide | Claude picks | |

**User's choice:** DiskANN from day one

---

## Auto-indexing Hooks

### Entities to Index

| Option | Description | Selected |
|--------|-------------|----------|
| Memories (shared_memory.value) | Primary use case | yes |
| Tasks (description + output) | Find similar tasks | yes |
| Artifacts (content) | Find similar documents | yes |
| Messages (content) | Search past conversations | yes |

**User's choice:** All 4 entity types

### Failure Mode

| Option | Description | Selected |
|--------|-------------|----------|
| Log error, entity saved without embedding | Background retry every 5 min | yes |
| Retry with exponential backoff | Dead letter queue on exhaustion | |
| You decide | Claude picks | |

**User's choice:** Log error, save without embedding, periodic retry

---

## Search API Design

### API Shape

| Option | Description | Selected |
|--------|-------------|----------|
| Unified /v1/search | Single cross-entity endpoint | |
| Per-entity endpoints | Four separate endpoints | |
| Both - unified + per-entity shortcuts | Hybrid | yes |

**User's choice:** Both - unified + per-entity shortcuts

### top_k Defaults

| Option | Description | Selected |
|--------|-------------|----------|
| Default 10, max 50 | Sensible UI default, capped | yes |
| Default 20, max 100 | More generous | |
| You decide | Claude picks | |

**User's choice:** Default 10, max 50

---

## Claude's Discretion

- Exact sentence-transformers loading pattern
- Background task queue implementation choice
- DiskANN index parameters
- Test strategy for Turso-only features
- Re-indexing endpoint shape

## Deferred Ideas

- Real-time embedding updates over WebSocket
- Multi-language embedding support
- Cross-encoder re-ranking
- Hybrid BM25 + vector search
- Vector compression/quantization
