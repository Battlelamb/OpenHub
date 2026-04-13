"""Tests that zvec is fully purged from dependencies and Settings.

VEC-01 requires removing the placeholder zvec package and its associated
config field so downstream plans can introduce a real embedding backend.
"""
import os

from app.config import Settings


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def test_zvec_not_in_requirements():
    req_path = os.path.join(PROJECT_ROOT, "requirements.txt")
    with open(req_path, "r", encoding="utf-8") as fh:
        for line in fh:
            stripped = line.strip()
            assert not stripped.lower().startswith("zvec"), (
                f"requirements.txt still references zvec: {stripped!r}"
            )


def test_zvec_not_in_settings():
    settings = Settings()
    assert not hasattr(settings, "zvec_path"), (
        "Settings still exposes zvec_path - it must be removed for VEC-01"
    )
