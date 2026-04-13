"""VectorSearchService: thin wrapper around Turso's vector SQL functions.

This module is the single source of truth for how OpenHub talks to Turso's
native vector index. Two patterns in here are LOAD-BEARING and must not be
"refactored" without re-running the smoke test (scripts/smoke_turso_vector.py)
against a real Turso DB:

    1. Vectors are bound as ``vector32(:vec)`` with the parameter value being
       ``json.dumps(list_of_floats)`` (a JSON string). Do NOT pass bytes,
       packed binary blobs, raw lists, numpy arrays, or pickled objects. The
       Python libsql driver only accepts the JSON-string form for the
       ``vector32()`` function on Turso. RESEARCH.md "Pattern 2" / Pitfall 1.

    2. The ``vector_top_k`` join uses ``t.rowid = v.id`` (NOT ``t.id = v.id``).
       libSQL's vector_top_k returns the rowid of the underlying base table,
       which only equals the user-facing id column when the table uses
       ``INTEGER PRIMARY KEY``. Joining on the wrong column silently returns
       empty results. RESEARCH.md Pitfall 5.

The 4 entity types that are auto-indexed (D-12) are listed in
``ENTITY_CONFIG`` as ``(table_name, content_column, id_column)``.
"""
import json
from typing import Any, Dict, List, Optional, Tuple

from ..database.connection import Database
from ..logging import get_logger

logger = get_logger(__name__)


# (table, content_column, id_column) for each indexable entity type.
# Per D-12: shared_memory.value, tasks.description, artifacts.content, messages.content.
ENTITY_CONFIG: Dict[str, Tuple[str, str, str]] = {
    "memory": ("shared_memory", "value", "id"),
    "task": ("tasks", "description", "id"),
    "artifact": ("artifacts", "content", "id"),
    "message": ("messages", "content", "id"),
}


_ALLOWED_FILTER_KEYS = {"owner_agent_id", "created_after", "created_before"}


class VectorSearchService:
    """Service layer wrapping Turso vector_top_k / vector32 / vector_distance_cos."""

    def __init__(self, db: Database) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve(self, entity_type: str) -> Tuple[str, str, str]:
        if entity_type not in ENTITY_CONFIG:
            raise ValueError(
                f"Unknown entity_type '{entity_type}'. "
                f"Expected one of {sorted(ENTITY_CONFIG.keys())}."
            )
        return ENTITY_CONFIG[entity_type]

    # ------------------------------------------------------------------
    # Write path
    # ------------------------------------------------------------------

    def write_embedding(
        self,
        entity_type: str,
        entity_id: str,
        vector: List[float],
        model_name: str,
    ) -> None:
        """Persist an embedding vector and mark the row as 'ok'.

        SQL uses vector32(:vec) with json.dumps(vector) - see module docstring.
        """
        table, _, id_col = self._resolve(entity_type)
        sql = (
            f"UPDATE {table} "
            "SET embedding = vector32(:vec), "
            "    embedding_model = :model, "
            "    embedding_status = 'ok', "
            "    embedding_error = NULL, "
            "    embedded_at = CURRENT_TIMESTAMP "
            f"WHERE {id_col} = :id"
        )
        params = {
            "vec": json.dumps(vector),
            "model": model_name,
            "id": entity_id,
        }
        self.db.execute(sql, params)
        logger.info(
            "vector_write",
            entity_type=entity_type,
            entity_id=entity_id,
            dim=len(vector),
            model=model_name,
        )

    def mark_pending(self, entity_type: str, entity_id: str) -> None:
        """Reset an entity's embedding status to 'pending'."""
        table, _, id_col = self._resolve(entity_type)
        sql = (
            f"UPDATE {table} "
            "SET embedding_status = 'pending', embedding_error = NULL "
            f"WHERE {id_col} = :id"
        )
        self.db.execute(sql, {"id": entity_id})
        logger.debug(
            "vector_mark_pending", entity_type=entity_type, entity_id=entity_id
        )

    def mark_failed(self, entity_type: str, entity_id: str, error: str) -> None:
        """Mark an embedding write as failed and store a truncated error message."""
        table, _, id_col = self._resolve(entity_type)
        truncated = (error or "")[:500]
        sql = (
            f"UPDATE {table} "
            "SET embedding_status = 'failed', embedding_error = :err "
            f"WHERE {id_col} = :id"
        )
        self.db.execute(sql, {"err": truncated, "id": entity_id})
        logger.warning(
            "vector_mark_failed",
            entity_type=entity_type,
            entity_id=entity_id,
            error=truncated,
        )

    # ------------------------------------------------------------------
    # Read path
    # ------------------------------------------------------------------

    def search_entity(
        self,
        entity_type: str,
        query_vector: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Return top_k nearest entities by cosine distance ascending.

        Filter clauses live in the OUTER WHERE (after vector_top_k has produced
        candidates) per RESEARCH.md Pitfall 3 - applying filters before
        vector_top_k either silently drops the index or returns wrong results.
        """
        table, content_col, id_col = self._resolve(entity_type)
        index_name = f"idx_{table}_embedding"

        params: Dict[str, Any] = {
            "qvec": json.dumps(query_vector),
            "idx": index_name,
            "k": top_k,
        }

        where_clauses = ["t.embedding_status = 'ok'"]
        if filters:
            for key, value in filters.items():
                if key not in _ALLOWED_FILTER_KEYS:
                    raise ValueError(
                        f"Unsupported filter '{key}'. "
                        f"Allowed: {sorted(_ALLOWED_FILTER_KEYS)}"
                    )
                if key == "owner_agent_id":
                    where_clauses.append("t.owner_agent_id = :owner_agent_id")
                    params["owner_agent_id"] = value
                elif key == "created_after":
                    where_clauses.append("t.created_at >= :created_after")
                    params["created_after"] = value
                elif key == "created_before":
                    where_clauses.append("t.created_at <= :created_before")
                    params["created_before"] = value

        where_sql = " AND ".join(where_clauses)
        sql = (
            f"SELECT t.{id_col} AS id, "
            f"       t.{content_col} AS content, "
            "       vector_distance_cos(t.embedding, vector32(:qvec)) AS distance "
            f"FROM vector_top_k(:idx, vector32(:qvec), :k) AS v "
            f"JOIN {table} t ON t.rowid = v.id "
            f"WHERE {where_sql} "
            "ORDER BY distance ASC"
        )

        rows = self.db.fetch_all(sql, params) or []
        results: List[Dict[str, Any]] = []
        for row in rows:
            results.append(
                {
                    "entity_type": entity_type,
                    "id": row["id"] if isinstance(row, dict) else row[0],
                    "content": row["content"] if isinstance(row, dict) else row[1],
                    "distance": row["distance"] if isinstance(row, dict) else row[2],
                }
            )
        logger.info(
            "vector_search",
            entity_type=entity_type,
            top_k=top_k,
            result_count=len(results),
        )
        return results

    def list_unindexed(
        self, entity_type: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Return rows that have no embedding yet (NULL or 'failed' status).

        Used by the retry worker in Plan 04.
        """
        table, content_col, id_col = self._resolve(entity_type)
        sql = (
            f"SELECT {id_col} AS id, {content_col} AS content "
            f"FROM {table} "
            "WHERE embedding_status IS NULL OR embedding_status = 'failed' "
            "LIMIT :limit"
        )
        rows = self.db.fetch_all(sql, {"limit": limit}) or []
        return [
            {
                "id": row["id"] if isinstance(row, dict) else row[0],
                "content": row["content"] if isinstance(row, dict) else row[1],
            }
            for row in rows
        ]
