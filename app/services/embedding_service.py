"""Pluggable embedding backends for Phase 3 vector search.

This module exposes a small Protocol-based abstraction over text embedding
providers so the rest of the system (auto-indexer, search route, retry worker)
can stay backend-agnostic.

Two concrete backends ship in Wave 2:

- ``LocalSentenceTransformerBackend`` wraps sentence-transformers
  ``all-MiniLM-L6-v2`` (384-dim cosine vectors). The model and the
  ``sentence_transformers`` / ``torch`` imports are loaded lazily inside
  ``_ensure_model`` so that:

  * Importing this module never pulls in ~200MB of torch wheels.
  * Forked workers (uvicorn, alembic) do not inherit a CUDA context they did
    not allocate themselves (Pitfall 4 in 03-RESEARCH.md - fork safety).

- ``OpenAIBackend`` wraps the AsyncOpenAI client and ``text-embedding-3-small``
  (1536-dim). The ``openai`` package is also imported lazily inside
  ``__init__`` so installs that only use the local backend never need the
  dependency on disk.

``get_embedding_service`` is the single factory used by all callers; it reads
``Settings.embedding_provider`` and ``Settings.openai_api_key`` and degrades
gracefully (returns ``None``) when ``provider=openai`` is requested but no key
is set, per D-03.
"""
from __future__ import annotations

import asyncio
from typing import List, Optional, Protocol, runtime_checkable

from ..config import get_settings
from ..logging import get_logger

logger = get_logger(__name__)

# Hard cap on per-input characters for the OpenAI backend. text-embedding-3-small
# accepts up to ~8192 tokens; 30000 chars is a conservative safety bound that
# avoids the most common 400 errors on accidentally giant documents (Pitfall 7).
_OPENAI_INPUT_CHAR_LIMIT = 30000


@runtime_checkable
class EmbeddingBackend(Protocol):
    """Protocol every embedding backend must satisfy."""

    dim: int
    model_name: str

    async def embed(self, texts: List[str]) -> List[List[float]]:
        ...


class LocalSentenceTransformerBackend:
    """Sentence-transformers backend with lazy model loading.

    The underlying model is constructed on the first call to ``embed`` rather
    than at import or instantiation time. This keeps app boot cheap and lets
    deployments that never call vector endpoints avoid paying the torch tax.
    """

    dim: int = 384
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"

    def __init__(self) -> None:
        self._model = None
        self._lock = asyncio.Lock()

    async def _ensure_model(self) -> None:
        if self._model is not None:
            return
        async with self._lock:
            if self._model is not None:
                return
            # Import inside the lock so torch is only pulled in on first use.
            from sentence_transformers import SentenceTransformer  # type: ignore

            loop = asyncio.get_event_loop()
            model_name = self.model_name
            self._model = await loop.run_in_executor(
                None, lambda: SentenceTransformer(model_name)
            )
            logger.info(
                "embedding_model_loaded",
                backend="local",
                model=model_name,
                dim=self.dim,
            )

    async def embed(self, texts: List[str]) -> List[List[float]]:
        await self._ensure_model()
        loop = asyncio.get_event_loop()
        model = self._model

        def _encode() -> List[List[float]]:
            arr = model.encode(texts, convert_to_numpy=True)  # type: ignore[union-attr]
            # ``encode`` returns numpy.ndarray in normal use and a list-like
            # in tests that swap in a fake; both expose ``tolist``.
            if hasattr(arr, "tolist"):
                return arr.tolist()
            return [list(row) for row in arr]

        return await loop.run_in_executor(None, _encode)


class OpenAIBackend:
    """OpenAI text-embedding-3-small backend (1536-dim).

    The AsyncOpenAI client is imported lazily on construction so the ``openai``
    package is only required when this backend is actually selected. Tests can
    inject a pre-built client via the ``client`` keyword argument to avoid
    monkeypatching the import machinery.
    """

    dim: int = 1536
    model_name: str = "text-embedding-3-small"

    def __init__(self, api_key: str, client: Optional[object] = None) -> None:
        self._api_key = api_key
        if client is not None:
            self._client = client
        else:
            from openai import AsyncOpenAI  # type: ignore

            self._client = AsyncOpenAI(api_key=api_key, max_retries=3)

    async def embed(self, texts: List[str]) -> List[List[float]]:
        # Cheap defensive truncation per Pitfall 7 in 03-RESEARCH.md.
        safe_inputs = [t[:_OPENAI_INPUT_CHAR_LIMIT] for t in texts]
        resp = await self._client.embeddings.create(  # type: ignore[attr-defined]
            model=self.model_name,
            input=safe_inputs,
        )
        return [item.embedding for item in resp.data]


def get_embedding_service() -> Optional[EmbeddingBackend]:
    """Return the configured embedding backend or ``None``.

    Selection rules:

    - ``AGENTHUB_EMBEDDING_PROVIDER=openai`` + ``AGENTHUB_OPENAI_API_KEY`` set:
      returns an ``OpenAIBackend``.
    - ``AGENTHUB_EMBEDDING_PROVIDER=openai`` without a key: logs a warning and
      returns ``None`` so callers can short-circuit (D-03 graceful degradation).
    - Any other value (including unset, ``local``, or unknown strings): returns
      a fresh ``LocalSentenceTransformerBackend``.
    """
    settings = get_settings()
    provider = (settings.embedding_provider or "local").lower()

    if provider == "openai":
        if not settings.openai_api_key:
            logger.warning(
                "embedding_provider_openai_missing_key_disabled",
                provider="openai",
                hint="set AGENTHUB_OPENAI_API_KEY to enable OpenAI embeddings",
            )
            return None
        logger.debug("embedding_provider_openai", model=OpenAIBackend.model_name)
        return OpenAIBackend(api_key=settings.openai_api_key)

    if provider != "local":
        logger.warning(
            "embedding_provider_unknown_falling_back_to_local",
            requested=provider,
        )
    else:
        logger.debug(
            "embedding_provider_local",
            model=LocalSentenceTransformerBackend.model_name,
        )
    return LocalSentenceTransformerBackend()


__all__ = [
    "EmbeddingBackend",
    "LocalSentenceTransformerBackend",
    "OpenAIBackend",
    "get_embedding_service",
]
