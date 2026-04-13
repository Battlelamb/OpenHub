"""Unit tests for the embedding service module (Plan 03-03).

Covers backend selection, dimension contracts, lazy loading of
sentence-transformers/torch, and graceful degradation for the OpenAI
backend when no key is configured.
"""
from __future__ import annotations

import sys
import types
from typing import List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

import app.config as app_config
from app.services.embedding_service import (
    EmbeddingBackend,
    LocalSentenceTransformerBackend,
    OpenAIBackend,
    get_embedding_service,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _reset_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force app.config.settings to be re-read from environment.

    pydantic-settings caches the singleton at import; tests need a fresh
    Settings() so monkeypatched env vars take effect.
    """
    fresh = app_config.Settings()
    monkeypatch.setattr(app_config, "settings", fresh)


def _install_fake_sentence_transformers(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Inject a fake sentence_transformers module so torch is never imported."""
    fake_module = types.ModuleType("sentence_transformers")

    class _FakeModel:
        def __init__(self, name: str) -> None:
            self.name = name

        def encode(self, texts: List[str], convert_to_numpy: bool = True):  # noqa: D401
            class _Arr(list):
                def tolist(self_inner):
                    return list(self_inner)

            return _Arr([[0.0] * 768 for _ in texts])

    fake_module.SentenceTransformer = _FakeModel  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)
    return fake_module  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Dimension and naming contracts
# ---------------------------------------------------------------------------


def test_local_dim() -> None:
    assert LocalSentenceTransformerBackend.dim == 768
    assert (
        LocalSentenceTransformerBackend.model_name
        == "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
    )


def test_openai_dim_mocked() -> None:
    assert OpenAIBackend.dim == 1536
    assert OpenAIBackend.model_name == "text-embedding-3-small"


# ---------------------------------------------------------------------------
# Lazy loading guarantees
# ---------------------------------------------------------------------------


def test_local_no_module_import_on_class_construction() -> None:
    snapshot = set(sys.modules)
    backend = LocalSentenceTransformerBackend()
    new_modules = set(sys.modules) - snapshot
    assert "sentence_transformers" not in new_modules
    assert "torch" not in new_modules
    assert backend._model is None


@pytest.mark.asyncio
async def test_local_lazy_load_and_embed_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_sentence_transformers(monkeypatch)
    backend = LocalSentenceTransformerBackend()
    assert backend._model is None
    out = await backend.embed(["hello", "world"])
    assert backend._model is not None
    assert len(out) == 2
    assert all(len(vec) == 768 for vec in out)


# ---------------------------------------------------------------------------
# OpenAI backend
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_openai_embed_calls_client() -> None:
    fake_client = MagicMock()
    fake_resp = MagicMock()
    fake_resp.data = [
        MagicMock(embedding=[0.1] * 1536),
        MagicMock(embedding=[0.2] * 1536),
    ]
    fake_client.embeddings.create = AsyncMock(return_value=fake_resp)

    backend = OpenAIBackend(api_key="sk-test", client=fake_client)
    out = await backend.embed(["alpha", "beta"])

    fake_client.embeddings.create.assert_awaited_once()
    call_kwargs = fake_client.embeddings.create.call_args.kwargs
    assert call_kwargs["model"] == "text-embedding-3-small"
    assert call_kwargs["input"] == ["alpha", "beta"]
    assert len(out) == 2
    assert all(len(vec) == 1536 for vec in out)


@pytest.mark.asyncio
async def test_openai_truncates_long_input() -> None:
    fake_client = MagicMock()
    fake_resp = MagicMock()
    fake_resp.data = [MagicMock(embedding=[0.0] * 1536)]
    fake_client.embeddings.create = AsyncMock(return_value=fake_resp)

    long_text = "x" * 50000
    backend = OpenAIBackend(api_key="sk-test", client=fake_client)
    await backend.embed([long_text])

    sent_input = fake_client.embeddings.create.call_args.kwargs["input"]
    assert len(sent_input[0]) == 30000


# ---------------------------------------------------------------------------
# Factory / provider selection
# ---------------------------------------------------------------------------


def test_local_is_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AGENTHUB_EMBEDDING_PROVIDER", raising=False)
    monkeypatch.delenv("AGENTHUB_OPENAI_API_KEY", raising=False)
    _reset_settings(monkeypatch)
    backend = get_embedding_service()
    assert isinstance(backend, LocalSentenceTransformerBackend)


def test_provider_unknown_falls_back_to_local(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENTHUB_EMBEDDING_PROVIDER", "bogus")
    monkeypatch.delenv("AGENTHUB_OPENAI_API_KEY", raising=False)
    _reset_settings(monkeypatch)
    backend = get_embedding_service()
    assert isinstance(backend, LocalSentenceTransformerBackend)


def test_openai_missing_key_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENTHUB_EMBEDDING_PROVIDER", "openai")
    monkeypatch.delenv("AGENTHUB_OPENAI_API_KEY", raising=False)
    _reset_settings(monkeypatch)
    assert get_embedding_service() is None


def test_openai_with_key_returns_openai_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENTHUB_EMBEDDING_PROVIDER", "openai")
    monkeypatch.setenv("AGENTHUB_OPENAI_API_KEY", "sk-test-key")
    _reset_settings(monkeypatch)

    # Inject a fake openai module so OpenAIBackend.__init__ does not import the real one.
    fake_openai = types.ModuleType("openai")

    class _FakeAsyncOpenAI:
        def __init__(
            self, api_key: str, max_retries: int = 3, base_url: Optional[str] = None
        ) -> None:
            self.api_key = api_key
            self.max_retries = max_retries
            self.base_url = base_url

    fake_openai.AsyncOpenAI = _FakeAsyncOpenAI  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "openai", fake_openai)

    backend = get_embedding_service()
    assert isinstance(backend, OpenAIBackend)


@pytest.mark.asyncio
async def test_openai_backend_ollama_override() -> None:
    """Verify base_url + model + dim overrides flow through the OpenAI client.

    Simulates pointing OpenAIBackend at a local Ollama server with a 768-dim
    multilingual model, as required by the Phase 3 VPS deployment with
    F32_BLOB(768) in migration 0003.
    """
    fake_client = MagicMock()
    fake_resp = MagicMock()
    fake_resp.data = [MagicMock(embedding=[0.3] * 768)]
    fake_client.embeddings.create = AsyncMock(return_value=fake_resp)

    backend = OpenAIBackend(
        api_key="ollama",
        client=fake_client,
        base_url="http://127.0.0.1:11434/v1",
        model="paraphrase-multilingual",
        dim=768,
    )

    assert backend.dim == 768
    assert backend.model_name == "paraphrase-multilingual"

    out = await backend.embed(["merhaba dunya"])
    fake_client.embeddings.create.assert_awaited_once()
    call_kwargs = fake_client.embeddings.create.call_args.kwargs
    assert call_kwargs["model"] == "paraphrase-multilingual"
    assert len(out) == 1
    assert len(out[0]) == 768


def test_openai_factory_wires_ollama_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Factory must pass AGENTHUB_EMBEDDING_* overrides into OpenAIBackend."""
    monkeypatch.setenv("AGENTHUB_EMBEDDING_PROVIDER", "openai")
    monkeypatch.setenv("AGENTHUB_OPENAI_API_KEY", "ollama")
    monkeypatch.setenv("AGENTHUB_EMBEDDING_BASE_URL", "http://127.0.0.1:11434/v1")
    monkeypatch.setenv(
        "AGENTHUB_EMBEDDING_MODEL_OVERRIDE", "paraphrase-multilingual"
    )
    monkeypatch.setenv("AGENTHUB_EMBEDDING_DIM_OVERRIDE", "768")
    _reset_settings(monkeypatch)

    captured: dict = {}

    fake_openai = types.ModuleType("openai")

    class _FakeAsyncOpenAI:
        def __init__(
            self, api_key: str, max_retries: int = 3, base_url: Optional[str] = None
        ) -> None:
            captured["api_key"] = api_key
            captured["max_retries"] = max_retries
            captured["base_url"] = base_url

    fake_openai.AsyncOpenAI = _FakeAsyncOpenAI  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "openai", fake_openai)

    backend = get_embedding_service()
    assert isinstance(backend, OpenAIBackend)
    assert backend.dim == 768
    assert backend.model_name == "paraphrase-multilingual"
    assert captured["base_url"] == "http://127.0.0.1:11434/v1"
    assert captured["api_key"] == "ollama"


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


def test_protocol_runtime_check() -> None:
    assert isinstance(LocalSentenceTransformerBackend(), EmbeddingBackend)
