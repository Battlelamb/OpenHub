"""Tests for TaskService.admin_transition_status (Phase 06-01)."""
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.services.task_service import TaskService


@pytest.fixture
def service():
    return TaskService(MagicMock())


def _task(status: str = "queued", task_id: str = "task-1"):
    return SimpleNamespace(id=task_id, status=status)


class TestAdminTransitionStatus:
    """Admin Kanban task status transitions."""

    @pytest.mark.parametrize(
        ("from_status", "to_status"),
        [
            ("queued", "claimed"),
            ("queued", "running"),
            ("queued", "cancelled"),
            ("claimed", "queued"),
            ("claimed", "running"),
            ("claimed", "cancelled"),
            ("running", "queued"),
            ("running", "completed"),
            ("running", "failed"),
            ("running", "cancelled"),
            ("completed", "queued"),
            ("failed", "queued"),
            ("cancelled", "queued"),
        ],
    )
    def test_valid_transitions_update_task(self, service, from_status, to_status):
        service.task_repo = MagicMock()
        service.task_repo.get_by_id.return_value = _task(from_status)
        service.task_repo.update.return_value = _task(to_status)

        result = service.admin_transition_status("task-1", to_status, "admin-1")

        assert result.status == to_status
        service.task_repo.update.assert_called_once()
        task_id, updates = service.task_repo.update.call_args.args
        assert task_id == "task-1"
        assert updates["status"] == to_status
        assert "updated_at" in updates

    @pytest.mark.parametrize(
        ("from_status", "to_status"),
        [
            ("queued", "completed"),
            ("queued", "failed"),
            ("claimed", "completed"),
            ("claimed", "failed"),
            ("running", "claimed"),
            ("completed", "running"),
            ("completed", "failed"),
            ("failed", "running"),
            ("failed", "completed"),
            ("cancelled", "running"),
            ("cancelled", "completed"),
        ],
    )
    def test_invalid_transitions_raise_value_error(self, service, from_status, to_status):
        service.task_repo = MagicMock()
        service.task_repo.get_by_id.return_value = _task(from_status)

        with pytest.raises(ValueError, match="not allowed"):
            service.admin_transition_status("task-1", to_status, "admin-1")

        service.task_repo.update.assert_not_called()

    def test_missing_task_returns_none(self, service):
        service.task_repo = MagicMock()
        service.task_repo.get_by_id.return_value = None

        result = service.admin_transition_status("missing", "claimed", "admin-1")

        assert result is None
        service.task_repo.update.assert_not_called()

    def test_claimed_transition_sets_claimed_at(self, service):
        service.task_repo = MagicMock()
        service.task_repo.get_by_id.return_value = _task("queued")
        service.task_repo.update.return_value = _task("claimed")

        service.admin_transition_status("task-1", "claimed", "admin-1")

        updates = service.task_repo.update.call_args.args[1]
        assert "claimed_at" in updates

    def test_running_transition_sets_started_at(self, service):
        service.task_repo = MagicMock()
        service.task_repo.get_by_id.return_value = _task("claimed")
        service.task_repo.update.return_value = _task("running")

        service.admin_transition_status("task-1", "running", "admin-1")

        updates = service.task_repo.update.call_args.args[1]
        assert "started_at" in updates

    def test_completed_transition_sets_completed_at(self, service):
        service.task_repo = MagicMock()
        service.task_repo.get_by_id.return_value = _task("running")
        service.task_repo.update.return_value = _task("completed")

        service.admin_transition_status("task-1", "completed", "admin-1")

        updates = service.task_repo.update.call_args.args[1]
        assert "completed_at" in updates

    def test_queued_transition_resets_assignment_and_lease_fields(self, service):
        service.task_repo = MagicMock()
        service.task_repo.get_by_id.return_value = _task("running")
        service.task_repo.update.return_value = _task("queued")

        service.admin_transition_status("task-1", "queued", "admin-1")

        updates = service.task_repo.update.call_args.args[1]
        assert updates["owner_agent_id"] is None
        assert updates["claimed_at"] is None
        assert updates["started_at"] is None
        assert updates["lease_until"] is None
