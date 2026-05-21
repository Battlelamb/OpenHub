"""Integration tests for PATCH /v1/tasks/{task_id}/status (Phase 06-02)."""
from fastapi.testclient import TestClient


def _create_task(test_client: TestClient, admin_headers: dict[str, str], title: str = "Patch status task") -> str:
    response = test_client.post(
        "/v1/tasks/",
        headers=admin_headers,
        json={
            "title": title,
            "description": "Task used by PATCH /status integration tests.",
            # Use a deliberately unique capability so automatic agent matching
            # does not immediately claim the task during creation. The endpoint
            # under test should start from a real queued task.
            "required_capabilities": [f"phase06-unmatched-{title}"],
            "priority": 50,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


def _patch_status(
    test_client: TestClient,
    admin_headers: dict[str, str],
    task_id: str,
    status: str,
):
    return test_client.patch(
        f"/v1/tasks/{task_id}/status",
        headers=admin_headers,
        json={"status": status},
    )


class TestPatchTaskStatusEndpoint:
    """Admin Kanban status transition endpoint."""

    def test_queued_to_claimed_returns_updated_task(
        self, test_client: TestClient, admin_headers: dict[str, str]
    ):
        task_id = _create_task(test_client, admin_headers, "queued to claimed")

        response = _patch_status(test_client, admin_headers, task_id, "claimed")

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["id"] == task_id
        assert body["status"] == "claimed"

    def test_invalid_transition_returns_409(
        self, test_client: TestClient, admin_headers: dict[str, str]
    ):
        task_id = _create_task(test_client, admin_headers, "queued to completed invalid")

        response = _patch_status(test_client, admin_headers, task_id, "completed")

        assert response.status_code == 409, response.text
        body = response.json()
        assert body["status"] == 409
        assert "not allowed" in body["detail"]

    def test_unknown_task_returns_404(
        self, test_client: TestClient, admin_headers: dict[str, str]
    ):
        response = _patch_status(test_client, admin_headers, "missing-task-id", "queued")

        assert response.status_code == 404, response.text
        body = response.json()
        assert body["status"] == 404
        assert "not found" in body["detail"]

    def test_invalid_status_value_returns_422(
        self, test_client: TestClient, admin_headers: dict[str, str]
    ):
        task_id = _create_task(test_client, admin_headers, "invalid status value")

        response = _patch_status(test_client, admin_headers, task_id, "bogus")

        assert response.status_code == 422, response.text

    def test_full_happy_path_lifecycle(
        self, test_client: TestClient, admin_headers: dict[str, str]
    ):
        task_id = _create_task(test_client, admin_headers, "full lifecycle")

        for target_status in ["claimed", "running", "completed"]:
            response = _patch_status(test_client, admin_headers, task_id, target_status)
            assert response.status_code == 200, response.text
            assert response.json()["status"] == target_status

    def test_running_task_can_be_cancelled(
        self, test_client: TestClient, admin_headers: dict[str, str]
    ):
        task_id = _create_task(test_client, admin_headers, "running to cancelled")

        for target_status in ["claimed", "running", "cancelled"]:
            response = _patch_status(test_client, admin_headers, task_id, target_status)
            assert response.status_code == 200, response.text
            assert response.json()["status"] == target_status
