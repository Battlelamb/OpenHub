"""Turso vector binding integration tests.

Validates the load-bearing assumption from RESEARCH.md Pattern 2: vectors must
be bound to ``vector32(:vec)`` as ``json.dumps(list_of_floats)``. Marked turso
so it skips on local dev without credentials.

The ``turso_db`` fixture lives in tests/integration/test_vector_search.py and
is reused here via the standard pytest mechanism (it is session-scoped and
fixtures are visible across files in the same directory once collected).
"""
import json
import struct

import pytest

from app.services.vector_search_service import VectorSearchService

# Re-export the session fixture so this file does not have to import it
# explicitly; pytest discovers fixtures from conftest, but inter-file fixture
# sharing also works as long as one of the files defines it. We instead just
# rely on the module-level fixture in test_vector_search.py being collected
# first (alphabetical order: search before storage). To be explicit we import
# it here so pytest picks it up either way.
from tests.integration.test_vector_search import turso_db  # noqa: F401


pytestmark = pytest.mark.turso


def test_binding_roundtrip(turso_db):
    """vector32(json.dumps(vec)) roundtrips with cosine distance ~0."""
    svc = VectorSearchService(turso_db)
    row_id = "__vector_test_storage_roundtrip"
    known_vec = [0.0] * 768
    known_vec[0] = 1.0
    known_vec[1] = 0.5

    try:
        turso_db.execute(
            "INSERT INTO shared_memory (id, key, value, created_at) "
            "VALUES (:id, :k, :v, CURRENT_TIMESTAMP)",
            {"id": row_id, "k": row_id, "v": "binding roundtrip"},
        )
        svc.write_embedding("memory", row_id, known_vec, "test-binding-model")

        rows = turso_db.fetch_all(
            "SELECT vector_distance_cos(embedding, vector32(:qv)) AS distance "
            "FROM shared_memory WHERE id = :id",
            {"qv": json.dumps(known_vec), "id": row_id},
        )
        assert rows, "row not found after write"
        distance = rows[0]["distance"] if isinstance(rows[0], dict) else rows[0][0]
        assert distance is not None
        assert distance < 0.001, f"roundtrip distance {distance} exceeds 0.001"
    finally:
        try:
            turso_db.execute(
                "DELETE FROM shared_memory WHERE id = :id", {"id": row_id}
            )
        except Exception:
            pass


def test_binding_wrong_type_rejects(turso_db):
    """Binding raw bytes (struct.pack) to vector32() must raise.

    This is the canary for Pitfall 1: if this test ever starts passing it
    means the libsql driver started accepting binary input and the json.dumps
    pattern can be revisited. Until then, do not change write_embedding.
    """
    row_id = "__vector_test_storage_wrongtype"
    try:
        turso_db.execute(
            "INSERT INTO shared_memory (id, key, value, created_at) "
            "VALUES (:id, :k, :v, CURRENT_TIMESTAMP)",
            {"id": row_id, "k": row_id, "v": "wrong type"},
        )
        bad_blob = struct.pack("f" * 768, *([0.1] * 768))
        with pytest.raises(Exception):
            turso_db.execute(
                "UPDATE shared_memory SET embedding = vector32(:vec) WHERE id = :id",
                {"vec": bad_blob, "id": row_id},
            )
    finally:
        try:
            turso_db.execute(
                "DELETE FROM shared_memory WHERE id = :id", {"id": row_id}
            )
        except Exception:
            pass


def test_index_created(turso_db):
    """At least one DiskANN index from migration 0003 exists on Turso."""
    rows = turso_db.fetch_all(
        "SELECT name FROM sqlite_master "
        "WHERE type='index' AND name LIKE 'idx_%_embedding'"
    )
    names = []
    for r in rows or []:
        if isinstance(r, dict):
            names.append(r["name"])
        else:
            names.append(r[0])
    expected = {
        "idx_shared_memory_embedding",
        "idx_tasks_embedding",
        "idx_artifacts_embedding",
        "idx_messages_embedding",
    }
    assert any(n in expected for n in names), (
        "DiskANN index not created - check migration 0003 ran on Turso. "
        f"Found indexes: {names}"
    )
