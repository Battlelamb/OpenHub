# Phase 1: Backend Hardening - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md - this log preserves the alternatives considered.

**Date:** 2026-04-07
**Phase:** 01-backend-hardening
**Areas discussed:** Error response format, Admin credentials, Auth stub cleanup, Migration strategy, Redis fail behavior

---

## Error Response Format

| Option | Description | Selected |
|--------|-------------|----------|
| RFC 7807 Problem Details | Standard format: {type, title, status, detail, instance} - widely adopted | X |
| Simple {error, message} | Minimal: {error, message, status} - easy to parse | |
| You decide | Claude picks | |

**User's choice:** RFC 7807 Problem Details
**Notes:** Standard, self-documenting format

### Validation Error Detail

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, field-level | Include 'errors' array with field name + message per invalid field | X |
| Single message only | Just one error message | |
| You decide | Claude picks | |

**User's choice:** Field-level detail

### Rate Limiting Headers

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, Retry-After | Include Retry-After + remaining/limit headers | X |
| No extras | Just 429 status | |
| You decide | Claude picks | |

**User's choice:** Include Retry-After headers

### 500 Error Stack Traces

| Option | Description | Selected |
|--------|-------------|----------|
| Never | Generic message in response, trace in logs only | X |
| Dev mode only | Expose traces when DEBUG=true | |
| You decide | Claude picks | |

**User's choice:** Never expose traces

### Server-side Logging

| Option | Description | Selected |
|--------|-------------|----------|
| Structured JSON | structlog with machine-parseable fields | X |
| Human-readable text | Standard Python logging | |
| You decide | Claude picks | |

**User's choice:** Structured JSON via structlog

---

## Admin Credentials

| Option | Description | Selected |
|--------|-------------|----------|
| Env var credentials | AGENTHUB_ADMIN_USER + AGENTHUB_ADMIN_PASSWORD - refuse to start if not set | X |
| First-run setup | /setup endpoint creates admin on first use | |
| DB-backed admin users | Full admin user table with hashed passwords | |

**User's choice:** Env var credentials

### Dev Defaults

| Option | Description | Selected |
|--------|-------------|----------|
| Always require | No defaults - server exits with error if missing | X |
| Dev default allowed | Allow defaults in development mode | |
| You decide | Claude picks | |

**User's choice:** Always require, even in dev

---

## Auth Stub Cleanup

### Stub Handling

| Option | Description | Selected |
|--------|-------------|----------|
| Delete entirely | Remove app/dependencies.py, all routes use real auth | X |
| Keep as dev bypass | Only active in development mode | |
| You decide | Claude picks | |

**User's choice:** Delete entirely

### Helper Consolidation

| Option | Description | Selected |
|--------|-------------|----------|
| Shared dependency module | Single app/auth/api_key_deps.py | |
| FastAPI middleware | Auth as middleware before all routes | X |
| You decide | Claude picks | |

**User's choice:** FastAPI middleware

---

## Migration Strategy

### Migration Tool

| Option | Description | Selected |
|--------|-------------|----------|
| Custom versioned | Simple numbered SQL files with _schema_version table | |
| Use Alembic | Full Alembic with revision history | X |
| You decide | Claude picks | |

**User's choice:** Alembic

### Alembic Style

| Option | Description | Selected |
|--------|-------------|----------|
| Raw SQL revisions | Hand-written SQL, Alembic manages versioning | |
| SQLAlchemy models | Full ORM models, auto-generate migrations | X |
| You decide | Claude picks | |

**User's choice:** SQLAlchemy models with auto-generated migrations

---

## Redis Fail Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Fail open | Skip blacklist when Redis down, log failure | |
| Fail closed | Keep current - block all auth when Redis down | X |
| Skip blacklist entirely | Rely on JWT expiry only | |
| You decide | Claude picks | |

**User's choice:** Fail closed (strictest security)

---

## Claude's Discretion

- Prometheus metrics endpoint layout
- structlog configuration and processors
- decode_token_without_verification rename
- ACN admin key and invite code persistence
- API key validation optimization

## Deferred Ideas

None
