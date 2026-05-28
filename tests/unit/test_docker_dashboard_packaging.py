"""Phase 08-03: Docker image must package the React dashboard.

These tests guard the release packaging contract without requiring local Docker
socket access. The GitHub Actions smoke test builds/runs the image; these unit
checks make the Dockerfile and .dockerignore intent explicit.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(path: str) -> str:
    return (ROOT / path).read_text()


def _dockerignore_entries() -> set[str]:
    entries: set[str] = set()
    for line in _read(".dockerignore").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            entries.add(stripped)
    return entries


def test_dockerfile_builds_dashboard_and_copies_dist_into_runtime_image() -> None:
    dockerfile = _read("Dockerfile")

    assert "FROM node:22-slim AS dashboard-build" in dockerfile
    assert "COPY web/package*.json ./" in dockerfile
    assert "RUN npm ci" in dockerfile
    assert "COPY web/ ./" in dockerfile
    assert "RUN npm run build" in dockerfile
    assert "COPY --from=dashboard-build /dashboard/dist ./web/dist" in dockerfile


def test_dockerignore_keeps_dashboard_build_inputs_in_context() -> None:
    entries = _dockerignore_entries()

    assert "web/node_modules" in entries
    assert "web/dist" in entries

    required_inputs = {
        "web/src",
        "web/index.html",
        "web/package.json",
        "web/package-lock.json",
        "web/vite.config.ts",
        "web/tsconfig.json",
        "web/tsconfig.app.json",
        "web/tsconfig.node.json",
    }
    assert required_inputs.isdisjoint(entries)
