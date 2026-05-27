from datetime import datetime, timedelta, timezone
from typing import Any, cast

import pytest

from app.models.agents import Agent, AgentStatus
from app.services.heartbeat_service import HeartbeatService


class _FakeAgentRepository:
    def __init__(self, agents):
        self._agents = agents

    def find_by(self, filters):
        assert filters == {"status": AgentStatus.ONLINE.value}
        return self._agents


class _FakeDatabase:
    pass


def _agent_with_last_heartbeat(last_heartbeat: datetime) -> Agent:
    return Agent(
        id="agent-naive-heartbeat",
        agent_name="naive-heartbeat-agent",
        capabilities=["test"],
        status=AgentStatus.ONLINE,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        last_heartbeat=last_heartbeat,
    )


@pytest.mark.asyncio
async def test_check_agent_heartbeats_treats_naive_timestamps_as_utc():
    """Legacy SQLite/CURRENT_TIMESTAMP rows are naive; monitor comparisons stay safe."""
    naive_expired = (datetime.now(timezone.utc) - timedelta(hours=1)).replace(tzinfo=None)
    service = HeartbeatService(cast(Any, _FakeDatabase()))
    service.agent_repo = cast(Any, _FakeAgentRepository([_agent_with_last_heartbeat(naive_expired)]))

    expired_agent_ids: list[str] = []

    async def record_expired(agent: Agent) -> None:
        expired_agent_ids.append(agent.id)

    service._handle_expired_agent = record_expired  # type: ignore[method-assign]

    await service._check_agent_heartbeats()

    assert expired_agent_ids == ["agent-naive-heartbeat"]
