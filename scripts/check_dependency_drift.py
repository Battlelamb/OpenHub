#!/usr/bin/env python3
"""Guard OpenHub dependency manifests against backend/frontend drift.

The guard is intentionally dependency-free so CI can run it before installing
project packages. It checks the contracts that currently matter for release
repeatability:

* runtime requirements pinned in requirements.txt match pyproject.toml runtime
  lower bounds;
* every pinned requirements.txt entry is declared somewhere in pyproject.toml
  (runtime, vector, or dev optional dependencies);
* web/package-lock.json root dependency specs mirror web/package.json exactly.
"""

from __future__ import annotations

import json
import re
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class DependencySpec:
    name: str
    normalized_name: str
    extras: tuple[str, ...]
    version: str
    source: str


@dataclass(frozen=True)
class DriftError:
    scope: str
    message: str


_NAME_RE = re.compile(r"^\s*([A-Za-z0-9_.-]+)(\[[^\]]+\])?\s*(.*)$")
_REQUIREMENT_PIN_RE = re.compile(r"==\s*([^,;\s]+)")
_PYPROJECT_MIN_RE = re.compile(r">=\s*([^,;\s]+)")


def normalize_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _parse_extras(raw: str | None) -> tuple[str, ...]:
    if not raw:
        return ()
    return tuple(sorted(part.strip().lower() for part in raw.strip("[]").split(",") if part.strip()))


def _strip_inline_comment(line: str) -> str:
    before_comment, *_ = line.split(" #", 1)
    return before_comment.strip()


def _parse_dependency_line(
    line: str,
    *,
    source: str,
    version_pattern: re.Pattern[str],
) -> DependencySpec | DriftError | None:
    clean = _strip_inline_comment(line)
    if not clean or clean.startswith("#"):
        return None

    match = _NAME_RE.match(clean)
    if not match:
        return DriftError(source, f"could not parse dependency line: {line!r}")

    name, extras_raw, remainder = match.groups()
    version_match = version_pattern.search(remainder)
    if not version_match:
        operator = "==" if version_pattern is _REQUIREMENT_PIN_RE else ">="
        return DriftError(
            source,
            f"{name} must declare a {operator} version for drift comparison: {line!r}",
        )

    return DependencySpec(
        name=name,
        normalized_name=normalize_name(name),
        extras=_parse_extras(extras_raw),
        version=version_match.group(1),
        source=source,
    )


def _read_requirements(path: Path) -> tuple[dict[str, DependencySpec], list[DriftError]]:
    specs: dict[str, DependencySpec] = {}
    errors: list[DriftError] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        parsed = _parse_dependency_line(
            line,
            source=f"requirements.txt:{number}",
            version_pattern=_REQUIREMENT_PIN_RE,
        )
        if parsed is None:
            continue
        if isinstance(parsed, DriftError):
            errors.append(parsed)
            continue
        previous = specs.get(parsed.normalized_name)
        if previous and previous.version != parsed.version:
            errors.append(
                DriftError(
                    "requirements.txt",
                    f"{parsed.name} is pinned more than once with conflicting versions: "
                    f"{previous.version} and {parsed.version}",
                )
            )
        specs[parsed.normalized_name] = parsed
    return specs, errors


def _pyproject_dependency_entries(pyproject: dict) -> Iterable[tuple[str, str]]:
    project = pyproject.get("project", {})
    for entry in project.get("dependencies", []):
        yield "pyproject.toml project.dependencies", entry
    optional = project.get("optional-dependencies", {})
    for group, entries in optional.items():
        for entry in entries:
            yield f"pyproject.toml project.optional-dependencies.{group}", entry


def _read_pyproject(path: Path) -> tuple[dict[str, DependencySpec], set[str], list[DriftError]]:
    pyproject = tomllib.loads(path.read_text(encoding="utf-8"))
    specs: dict[str, DependencySpec] = {}
    runtime_names: set[str] = set()
    errors: list[DriftError] = []

    for source, entry in _pyproject_dependency_entries(pyproject):
        parsed = _parse_dependency_line(
            entry,
            source=source,
            version_pattern=_PYPROJECT_MIN_RE,
        )
        if parsed is None:
            continue
        if isinstance(parsed, DriftError):
            errors.append(parsed)
            continue
        if source == "pyproject.toml project.dependencies":
            runtime_names.add(parsed.normalized_name)
        previous = specs.get(parsed.normalized_name)
        if previous and previous.version != parsed.version:
            errors.append(
                DriftError(
                    "pyproject.toml",
                    f"{parsed.name} appears in multiple pyproject dependency groups with "
                    f"different lower bounds: {previous.version} and {parsed.version}",
                )
            )
        specs[parsed.normalized_name] = parsed

    return specs, runtime_names, errors


def _compare_backend_manifests(root: Path) -> list[DriftError]:
    requirements, errors = _read_requirements(root / "requirements.txt")
    pyproject, runtime_names, py_errors = _read_pyproject(root / "pyproject.toml")
    errors.extend(py_errors)

    for name in sorted(runtime_names):
        py_spec = pyproject[name]
        req_spec = requirements.get(name)
        if req_spec is None:
            errors.append(
                DriftError(
                    "backend dependencies",
                    f"{py_spec.name} is a runtime pyproject.toml dependency but is missing "
                    "from requirements.txt",
                )
            )

    for name, req_spec in sorted(requirements.items()):
        py_spec = pyproject.get(name)
        if py_spec is None:
            errors.append(
                DriftError(
                    "backend dependencies",
                    f"{req_spec.name} is pinned in requirements.txt but is not declared "
                    "in pyproject.toml dependencies or optional-dependencies",
                )
            )
            continue
        if req_spec.extras != py_spec.extras:
            errors.append(
                DriftError(
                    "backend dependencies",
                    f"{req_spec.name} extras drift: requirements.txt uses "
                    f"{req_spec.extras or 'no extras'}, pyproject.toml uses "
                    f"{py_spec.extras or 'no extras'}",
                )
            )
        if req_spec.version != py_spec.version:
            errors.append(
                DriftError(
                    "backend dependencies",
                    f"{req_spec.name} version drift: requirements.txt pins "
                    f"{req_spec.version}, pyproject.toml declares >={py_spec.version}",
                )
            )

    return errors


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _compare_dependency_section(
    *,
    section: str,
    package_json_root: dict,
    package_lock_root: dict,
) -> list[DriftError]:
    errors: list[DriftError] = []
    package_json_deps = package_json_root.get(section, {}) or {}
    package_lock_deps = package_lock_root.get(section, {}) or {}

    for name in sorted(set(package_json_deps) | set(package_lock_deps)):
        package_json_spec = package_json_deps.get(name)
        package_lock_spec = package_lock_deps.get(name)
        if package_json_spec != package_lock_spec:
            errors.append(
                DriftError(
                    "frontend dependencies",
                    f"web/package-lock.json {section} drift for {name}: "
                    f"package.json has {package_json_spec}, package-lock root has {package_lock_spec}",
                )
            )

    return errors


def _compare_frontend_manifests(root: Path) -> list[DriftError]:
    package_json = _load_json(root / "web" / "package.json")
    package_lock = _load_json(root / "web" / "package-lock.json")
    package_lock_root = package_lock.get("packages", {}).get("")
    if not isinstance(package_lock_root, dict):
        return [
            DriftError(
                "frontend dependencies",
                "web/package-lock.json is missing the lockfileVersion 3 root packages[''] entry",
            )
        ]

    errors: list[DriftError] = []
    for section in ("dependencies", "devDependencies"):
        errors.extend(
            _compare_dependency_section(
                section=section,
                package_json_root=package_json,
                package_lock_root=package_lock_root,
            )
        )
    return errors


def check_repository(root: Path | str) -> list[DriftError]:
    root_path = Path(root)
    errors: list[DriftError] = []
    errors.extend(_compare_backend_manifests(root_path))
    errors.extend(_compare_frontend_manifests(root_path))
    return errors


def format_errors(errors: Iterable[DriftError]) -> str:
    errors = list(errors)
    if not errors:
        return "No dependency drift detected."
    return "\n".join(f"- [{error.scope}] {error.message}" for error in errors)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    root = Path(argv[0]) if argv else Path(__file__).resolve().parents[1]
    errors = check_repository(root)
    if errors:
        print("Dependency drift detected:")
        print(format_errors(errors))
        return 1

    requirements, _ = _read_requirements(root / "requirements.txt")
    pyproject, runtime_names, _ = _read_pyproject(root / "pyproject.toml")
    package_json = _load_json(root / "web" / "package.json")
    print("Dependency drift guard passed:")
    print(f"- backend pins checked: {len(requirements)}")
    print(f"- pyproject dependencies known: {len(pyproject)} ({len(runtime_names)} runtime)")
    print(
        "- frontend specs checked: "
        f"{len(package_json.get('dependencies', {}) or {})} dependencies, "
        f"{len(package_json.get('devDependencies', {}) or {})} devDependencies"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
