"""Regression coverage for the Phase 08 dependency drift guard."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from scripts.check_dependency_drift import check_repository, format_errors


ROOT = Path(__file__).resolve().parents[2]


def _write_minimal_repo(
    root: Path,
    *,
    requirement_version: str = "1.0.0",
    pyproject_version: str = "1.0.0",
    package_json_spec: str = "^19.0.0",
    package_lock_spec: str = "^19.0.0",
) -> None:
    (root / "web").mkdir()
    (root / "requirements.txt").write_text(
        f"# Runtime\nfastapi=={requirement_version}\n", encoding="utf-8"
    )
    (root / "pyproject.toml").write_text(
        textwrap.dedent(
            f"""
            [project]
            name = "openhub-test"
            version = "0.0.0"
            dependencies = [
                "fastapi>={pyproject_version}",
            ]
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    (root / "web" / "package.json").write_text(
        json.dumps(
            {
                "dependencies": {"react": package_json_spec},
                "devDependencies": {},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "web" / "package-lock.json").write_text(
        json.dumps(
            {
                "lockfileVersion": 3,
                "packages": {
                    "": {
                        "dependencies": {"react": package_lock_spec},
                        "devDependencies": {},
                    }
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def test_current_dependency_manifests_have_no_drift() -> None:
    errors = check_repository(ROOT)

    assert errors == [], format_errors(errors)


def test_guard_detects_backend_version_drift(tmp_path: Path) -> None:
    _write_minimal_repo(
        tmp_path,
        requirement_version="1.0.1",
        pyproject_version="1.0.0",
    )

    errors = check_repository(tmp_path)

    assert "fastapi" in format_errors(errors)
    assert "requirements.txt pins 1.0.1" in format_errors(errors)
    assert "pyproject.toml declares >=1.0.0" in format_errors(errors)


def test_guard_detects_frontend_lockfile_drift(tmp_path: Path) -> None:
    _write_minimal_repo(
        tmp_path,
        package_json_spec="^19.0.0",
        package_lock_spec="^18.0.0",
    )

    errors = check_repository(tmp_path)

    assert "web/package-lock.json" in format_errors(errors)
    assert "react" in format_errors(errors)
    assert "package.json has ^19.0.0" in format_errors(errors)
    assert "package-lock root has ^18.0.0" in format_errors(errors)
