"""Regression tests for workflow runtime visibility.

The dashboard needs a workflow created through POST /v1/workflows/ to be
immediately visible through list/detail endpoints. This catches the bug where
routes construct a fresh HatchetService per request, losing the in-memory
_running_workflows registry between POST and GET.
"""

import pytest

from app.services.hatchet_service import HatchetService


@pytest.mark.asyncio
async def test_created_workflow_is_visible_to_detail_endpoint(test_client, admin_headers, monkeypatch):
    async def allow_test_agents(self, steps):
        return None

    async def keep_workflow_running(self, workflow_run_id):
        return None

    monkeypatch.setattr(HatchetService, "_validate_workflow_agents", allow_test_agents)
    monkeypatch.setattr(HatchetService, "_execute_workflow", keep_workflow_running)

    create = test_client.post(
        "/v1/workflows/",
        headers=admin_headers,
        json={
            "workflow_name": "Runtime visibility regression",
            "steps": [
                {
                    "step_name": "First step",
                    "agent_id": "test-agent-001",
                    "task_type": "regression",
                    "input_data": {"source": "test"},
                    "timeout_seconds": 30,
                    "retry_count": 0,
                }
            ],
            "input_data": {"source": "integration-test"},
        },
    )

    assert create.status_code == 200, create.text
    run_id = create.json()["workflow_run_id"]

    detail = test_client.get(f"/v1/workflows/{run_id}", headers=admin_headers)

    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["run_id"] == run_id
    assert body["name"] == "Runtime visibility regression"
    assert body["progress"]["total_steps"] == 1


@pytest.mark.asyncio
async def test_created_workflow_is_visible_to_list_endpoint(test_client, admin_headers, monkeypatch):
    async def allow_test_agents(self, steps):
        return None

    async def keep_workflow_running(self, workflow_run_id):
        return None

    monkeypatch.setattr(HatchetService, "_validate_workflow_agents", allow_test_agents)
    monkeypatch.setattr(HatchetService, "_execute_workflow", keep_workflow_running)

    create = test_client.post(
        "/v1/workflows/",
        headers=admin_headers,
        json={
            "workflow_name": "Runtime list regression",
            "steps": [
                {
                    "step_name": "Listed step",
                    "agent_id": "test-agent-001",
                    "task_type": "regression",
                    "input_data": {},
                    "timeout_seconds": 30,
                    "retry_count": 0,
                }
            ],
        },
    )

    assert create.status_code == 200, create.text
    run_id = create.json()["workflow_run_id"]

    listing = test_client.get("/v1/workflows/", headers=admin_headers)

    assert listing.status_code == 200, listing.text
    assert any(workflow["run_id"] == run_id for workflow in listing.json())
