"""Turso vector binding smoke test.

Run: .venv/bin/python scripts/smoke_turso_vector.py

Validates the vector32(json.dumps(list_of_floats)) binding pattern against a
real Turso DB. Requires TURSO_DATABASE_URL and TURSO_AUTH_TOKEN env vars (or
the AGENTHUB_-prefixed variants honoured by Settings).

Exit codes:
    0 - binding works, phase can proceed
    1 - binding broken, do not build on VectorSearchService until fixed
    2 - skipped (no Turso credentials provided)
"""
import json
import os
import sys
import uuid
from pathlib import Path

# Allow running as a standalone script from the repo root.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from app.database.connection import get_database  # noqa: E402
from app.services.vector_search_service import VectorSearchService  # noqa: E402


def main() -> int:
    has_creds = bool(
        (os.environ.get("TURSO_DATABASE_URL") or os.environ.get("AGENTHUB_TURSO_DATABASE_URL"))
        and (os.environ.get("TURSO_AUTH_TOKEN") or os.environ.get("AGENTHUB_TURSO_AUTH_TOKEN"))
    )
    if not has_creds:
        print(
            "SKIP: TURSO_DATABASE_URL and TURSO_AUTH_TOKEN required",
            file=sys.stderr,
        )
        return 2

    # Mirror plain env -> AGENTHUB_ env so Settings picks them up.
    if os.environ.get("TURSO_DATABASE_URL"):
        os.environ.setdefault("AGENTHUB_TURSO_DATABASE_URL", os.environ["TURSO_DATABASE_URL"])
    if os.environ.get("TURSO_AUTH_TOKEN"):
        os.environ.setdefault("AGENTHUB_TURSO_AUTH_TOKEN", os.environ["TURSO_AUTH_TOKEN"])

    db = get_database()
    if not getattr(db, "_use_turso", False):
        print("FAIL: Database did not activate Turso mode", file=sys.stderr)
        return 1

    test_id = f"__smoke_{uuid.uuid4().hex[:8]}"
    known_vec = [0.0] * 384
    known_vec[0] = 1.0
    known_vec[1] = 0.5

    try:
        db.execute(
            "INSERT INTO shared_memory (id, key, value, created_at) "
            "VALUES (:id, :k, :v, CURRENT_TIMESTAMP)",
            {"id": test_id, "k": test_id, "v": "smoke test content"},
        )

        svc = VectorSearchService(db)
        svc.write_embedding("memory", test_id, known_vec, "smoke-test-model")

        rows = db.fetch_all(
            "SELECT vector_distance_cos(embedding, vector32(:qv)) AS distance "
            "FROM shared_memory WHERE id = :id",
            {"qv": json.dumps(known_vec), "id": test_id},
        )
        if not rows:
            print("FAIL: row not found after write", file=sys.stderr)
            return 1

        first = rows[0]
        distance = first["distance"] if isinstance(first, dict) else first[0]
        if distance is None or distance > 0.001:
            print(
                f"FAIL: roundtrip distance {distance} exceeds 0.001 - binding is broken",
                file=sys.stderr,
            )
            return 1

        print(
            f"OK: roundtrip distance {distance} - vector32(json.dumps(...)) binding verified"
        )
        return 0
    finally:
        try:
            db.execute(
                "DELETE FROM shared_memory WHERE id = :id", {"id": test_id}
            )
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
