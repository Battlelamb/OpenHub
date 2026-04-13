---
phase: 03-vector-database
plan: 03
subsystem: embedding-service
tags: [embeddings, sentence-transformers, openai, lazy-load, protocol]
requires:
  - app.config.Settings.embedding_provider (Plan 01)
  - app.config.Settings.openai_api_key (Plan 01)
  - tests/conftest.py mock_embedding_backend (Plan 01)
provides:
  - app.services.embedding_service.EmbeddingBackend Protocol
  - app.services.embedding_service.LocalSentenceTransformerBackend
  - app.services.embedding_service.OpenAIBackend
  - app.services.embedding_service.get_embedding_service factory
affects:
  - requirements.txt (sentence-transformers + openai pins)
  - pyproject.toml (optional 'vector' extra, dropped stale zvec dep)
tech_stack:
  added:
    - sentence-transformers==3.3.1
    - openai==1.54.0
  removed:
    - zvec (pyproject only - already gone from requirements in Plan 01)
  patterns:
    - lazy module import inside asyncio.Lock double-check
    - run_in_executor for blocking model.encode calls
    - factory returns None for graceful degradation when openai key missing
    - Protocol with @runtime_checkable for isinstance checks
key_files:
  created:
    - app/services/embedding_service.py
  modified:
    - tests/unit/test_embedding_service.py
    - requirements.txt
    - pyproject.toml
decisions:
  - "sentence-transformers and openai are listed in requirements.txt as hard pins (sentence-transformers==3.3.1, openai==1.54.0) so the default install path works out of the box; pyproject.toml mirrors them under the optional 'vector' extra for the future Poetry-based OSS install."
  - "AsyncOpenAI client is constructed inside OpenAIBackend.__init__ with a test injection seam (client= kwarg) so unit tests can pass MagicMock without touching the openai module at import time."
  - "OpenAI inputs are unconditionally truncated to 30000 chars before each embeddings.create call - cheap defensive bound against the 8192-token / >8KB request errors documented in 03-RESEARCH Pitfall 7."
  - "get_embedding_service falls back to LocalSentenceTransformerBackend on unknown provider strings (logged as warning) instead of raising, so an unset env var or typo never breaks app boot."
metrics:
  duration: 4m
  completed: 2026-04-13T06:48:06Z
  tasks: 1
  files_created: 1
  files_modified: 3
  commits: 2
---

# Phase 03 Plan 03: Embedding Service Summary

Pluggable text-embedding backend layer for Phase 3 vector search: a Protocol contract, a lazy-loaded sentence-transformers backend (384-dim), and a graceful-degradation OpenAI backend (1536-dim), all wired through a single `get_embedding_service()` factory that Plans 04 (auto-index), 05 (search), and 06 (search route) can call without caring which backend is active.

## What Was Done

### Task 1 - EmbeddingService module + tests (TDD)

- **app/services/embedding_service.py** (new):
  - `EmbeddingBackend` Protocol with `dim: int`, `model_name: str`, and `async def embed(texts) -> List[List[float]]`. Decorated with `@runtime_checkable` so callers can `isinstance(backend, EmbeddingBackend)` for diagnostics.
  - `LocalSentenceTransformerBackend`:
    - Class attrs `dim=384`, `model_name="sentence-transformers/all-MiniLM-L6-v2"` (D-01).
    - `__init__` sets `_model = None` and creates an `asyncio.Lock`. Constructor never imports `sentence_transformers` or `torch`.
    - `_ensure_model` uses double-checked locking: outer fast-path check, lock, inner check, then `from sentence_transformers import SentenceTransformer` *inside the if-block*, then `loop.run_in_executor(None, lambda: SentenceTransformer(model_name))` so the cold-start blocking call does not stall the event loop. Logs `embedding_model_loaded` at info.
    - `embed` calls `_ensure_model`, then runs `model.encode(texts, convert_to_numpy=True)` in the threadpool. The encoder helper handles both `numpy.ndarray.tolist()` (real backend) and our list-like fake (unit tests) so we never depend on numpy in tests.
  - `OpenAIBackend`:
    - Class attrs `dim=1536`, `model_name="text-embedding-3-small"` (D-05).
    - `__init__(api_key, client=None)`: if `client` is provided, uses it directly (test injection); otherwise imports `AsyncOpenAI` inline and constructs with `max_retries=3`.
    - `embed` truncates each input to `_OPENAI_INPUT_CHAR_LIMIT = 30000` chars, then awaits `client.embeddings.create(model=..., input=safe_inputs)` and returns `[item.embedding for item in resp.data]`.
  - `get_embedding_service()` factory:
    - Reads `Settings.embedding_provider` (lowercased, defaulting to `"local"`).
    - `provider == "openai"` + `openai_api_key` present -> `OpenAIBackend(api_key=...)`.
    - `provider == "openai"` + key missing -> logs `embedding_provider_openai_missing_key_disabled` warning and returns `None` (D-03 graceful degradation).
    - Anything else (including unknown strings) -> `LocalSentenceTransformerBackend()`. Unknown values log a `embedding_provider_unknown_falling_back_to_local` warning so misconfigurations are visible.

- **tests/unit/test_embedding_service.py** (replaced Plan 01 stubs):
  - 11 tests, all `async`-aware via the existing `pytest-asyncio` `auto` mode.
  - `test_local_dim`, `test_openai_dim_mocked` - class-attribute contracts, no instantiation cost.
  - `test_local_no_module_import_on_class_construction` - takes a `set(sys.modules)` snapshot, instantiates the local backend, and asserts that neither `sentence_transformers` nor `torch` appears in the diff. This is the strict anti-fork-safety guard from RESEARCH Pitfall 4.
  - `test_local_lazy_load_and_embed_shape` - `monkeypatch.setitem(sys.modules, "sentence_transformers", fake)` injects an in-memory `SentenceTransformer` returning a list-of-list shaped `[len(texts), 384]`. Verifies `backend._model is None` before embed and not None after.
  - `test_openai_embed_calls_client` - injects a `MagicMock` client whose `embeddings.create` is an `AsyncMock`; asserts the call args (model, input) and the returned shape (2 vectors of 1536 floats).
  - `test_openai_truncates_long_input` - sends a 50000-char string and checks the actual call was 30000 chars (Pitfall 7 truncation).
  - `test_local_is_default`, `test_provider_unknown_falls_back_to_local` - factory returns local for unset and bogus values.
  - `test_openai_missing_key_returns_none` - factory returns `None` when key absent.
  - `test_openai_with_key_returns_openai_backend` - injects a fake `openai` module so `OpenAIBackend.__init__` can construct without the real package; asserts `isinstance` of result.
  - `test_protocol_runtime_check` - `isinstance(LocalSentenceTransformerBackend(), EmbeddingBackend)` confirms the runtime_checkable protocol matches.

- **requirements.txt**: added pinned `sentence-transformers==3.3.1` and `openai==1.54.0` under a `# Vector search backends (Phase 3)` comment block, kept the existing Phase 3 placeholder note.

- **pyproject.toml**:
  - Removed the stale `zvec = "^0.1.0"` line from `[tool.poetry.dependencies]` (it was already gone from `requirements.txt` in Plan 01).
  - Added `sentence-transformers = {version = "^3.3.1", optional = true}` and `openai = {version = "^1.54.0", optional = true}` plus a new `[tool.poetry.extras]` block exposing them as `vector = ["sentence-transformers", "openai"]`. Pip users still get them via `requirements.txt`; future Poetry/OSS users can opt-in with `poetry install -E vector`.

## Verification

```bash
# Unit tests pass
.venv/bin/python -m pytest tests/unit/test_embedding_service.py -v --tb=short --no-cov
# 11 passed in 0.07s

# Full non-turso suite green
.venv/bin/python -m pytest tests/ --no-cov -m "not turso"
# 71 passed, 1 skipped, 6 deselected, 7 xfailed

# App boots without ML deps
AGENTHUB_ADMIN_USER=x AGENTHUB_ADMIN_PASSWORD=y .venv/bin/python -c \
  "from app.main import app; import sys; print('torch:', 'torch' in sys.modules, 'st:', 'sentence_transformers' in sys.modules)"
# torch: False st: False

# Embedding module itself does not pull ML deps at import
AGENTHUB_ADMIN_USER=x AGENTHUB_ADMIN_PASSWORD=y .venv/bin/python -c \
  "import sys; from app.services import embedding_service; assert 'sentence_transformers' not in sys.modules; assert 'torch' not in sys.modules; print('lazy ok')"
# lazy ok
```

All acceptance grep checks pass:

```
OK: class EmbeddingBackend
OK: class LocalSentenceTransformerBackend
OK: class OpenAIBackend
OK: def get_embedding_service
OK: dim: int = 384
OK: dim: int = 1536
OK: text-embedding-3-small
OK: all-MiniLM-L6-v2
OK: asyncio.Lock
OK: run_in_executor
top-30 ML-import lines: 0
```

## Deviations from Plan

None - plan executed exactly as written. No Rule 1/2/3 auto-fixes were needed.

The plan suggested deferring the Poetry extras block to Phase 5 if it could not be added cleanly; it landed cleanly, so the `vector` extra is in `pyproject.toml` now.

## Known Gotchas For Downstream Plans

- **`get_embedding_service()` returns `Optional[EmbeddingBackend]`.** Plans 04/05/06 must handle the `None` case (provider=openai with no key) instead of assuming the call always returns a backend. Mirror the `require_vector` pattern from Plan 01: log + 503 / disable feature.
- **Lazy-load test pattern is reusable.** Any future test that needs to assert "import X never happens at module load" can copy the `sys.modules` snapshot pattern from `test_local_no_module_import_on_class_construction`.
- **Fake-module injection trick.** Tests inject `types.ModuleType("sentence_transformers")` and `types.ModuleType("openai")` via `monkeypatch.setitem(sys.modules, ...)` so the production code's lazy `import` resolves to the fake without ever touching the real package. Plans 04/05 should reuse this for any backend wiring tests so CI never has to install torch.
- **Settings reset helper.** `_reset_settings(monkeypatch)` rebuilds `app.config.settings` after env mutation. Required because `pydantic-settings` evaluates env at instance construction, not on attribute access; the cached singleton in `app/config.py` will not see fresh `monkeypatch.setenv` values unless replaced.
- **OpenAI input is truncated to 30000 chars per item.** This is silent. If Plans 04/05 need full-text embeddings (>30000 chars), they must chunk before calling `embed`, not after.
- **`SentenceTransformer.encode` is run in `loop.run_in_executor(None, ...)`.** Plans that batch embed calls should be aware that the default executor is shared with other sync work; consider passing a dedicated `ThreadPoolExecutor` if vector ingestion becomes a bottleneck (out of scope for Wave 2).

## Self-Check: PASSED

- app/services/embedding_service.py: FOUND
- tests/unit/test_embedding_service.py: FOUND (replaced from stub)
- requirements.txt sentence-transformers line: FOUND
- requirements.txt openai line: FOUND
- pyproject.toml [tool.poetry.extras] vector: FOUND
- Commit cfbd4f8 (RED tests): FOUND
- Commit 3eb4414 (GREEN implementation): FOUND
