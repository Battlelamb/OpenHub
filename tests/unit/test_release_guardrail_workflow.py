"""Static safety checks for the manual release verification workflow."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"


def test_release_workflow_is_manual_read_only_and_non_publishing() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in text
    assert "  push:" not in text
    assert "  pull_request:" not in text
    assert "contents: read" in text
    assert "confirm_no_publish" in text
    assert "python -m build" in text
    assert "twine check" in text
    assert "docker build" in text

    forbidden_publish_actions = [
        "twine upload",
        "docker push",
        "gh release create",
        "gh release upload",
        "git push --tags",
    ]
    for forbidden in forbidden_publish_actions:
        assert forbidden not in text


def test_release_workflow_requires_explicit_version_and_existing_version_match() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "version:" in text
    assert "required: true" in text
    assert "refs/tags/$RELEASE_VERSION" in text
    assert "pyproject.toml version" in text
    assert "must match workflow input" in text
