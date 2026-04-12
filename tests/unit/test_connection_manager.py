"""
Unit tests for ConnectionManager (WS-02, WS-03).

Exercises the ConnectionManager class directly using in-memory mock
WebSocket objects. Covers:

    - Pool management (connect / disconnect for UI and agent pools)
    - Limit enforcement (max_ws_ui, max_ws_agents)
    - Broadcast isolation (broadcast_to_ui must not touch the agent pool)
    - Batch buffering + flush_batch drain semantics
    - Safe no-op disconnect of unknown client_id

These tests do NOT use the full FastAPI app - they instantiate
ConnectionManager directly and feed it MockWebSocket stand-ins.
"""
from __future__ import annotations

import pytest

from app.services.connection_manager import ConnectionManager


class MockWebSocket:
    """Minimal WebSocket stand-in for unit tests.

    Only implements the two coroutine methods ConnectionManager calls
    (send_json, close). Captures sent payloads in a list for assertion.
    """

    def __init__(self) -> None:
        self.sent: list[dict] = []
        self.closed: bool = False
        self.close_code: int | None = None

    async def send_json(self, data: dict) -> None:
        self.sent.append(data)

    async def close(self, code: int = 1000, reason: str = "") -> None:
        self.closed = True
        self.close_code = code


# A far-future JWT expiry (year 2100+) for UI clients so the batch loop's
# token expiry check never disconnects them during a test run.
FAR_FUTURE_EXP: float = 4102444800.0  # 2100-01-01 UTC


@pytest.fixture
def manager() -> ConnectionManager:
    """Fresh ConnectionManager instance per test (no batch loop started)."""
    return ConnectionManager()


async def test_connect_ui_stores_client(manager: ConnectionManager) -> None:
    """connect_ui returns True and ui_client_count increments."""
    ws = MockWebSocket()

    accepted = await manager.connect_ui("ui-1", ws, FAR_FUTURE_EXP)

    assert accepted is True
    assert manager.ui_client_count == 1
    assert "ui-1" in manager.connected_ui_clients


async def test_disconnect_ui_removes_client(manager: ConnectionManager) -> None:
    """After disconnect, ui_client_count decrements and client is gone."""
    ws = MockWebSocket()
    await manager.connect_ui("ui-1", ws, FAR_FUTURE_EXP)
    assert manager.ui_client_count == 1

    await manager.disconnect_ui("ui-1")

    assert manager.ui_client_count == 0
    assert "ui-1" not in manager.connected_ui_clients


async def test_connect_agent_stores_agent(manager: ConnectionManager) -> None:
    """connect_agent returns True and agent_count increments."""
    ws = MockWebSocket()

    accepted = await manager.connect_agent("agent-1", ws)

    assert accepted is True
    assert manager.agent_count == 1
    assert "agent-1" in manager.connected_agents


async def test_ui_limit_enforcement(
    manager: ConnectionManager, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Connecting max_ws_ui+1 clients: the last call returns False."""
    # Shrink the UI limit to 2 for deterministic test; patch the module-level
    # `settings` reference that ConnectionManager reads at call time.
    from app.services import connection_manager as cm_module
    monkeypatch.setattr(cm_module.settings, "max_ws_ui", 2, raising=False)

    assert await manager.connect_ui("ui-1", MockWebSocket(), FAR_FUTURE_EXP) is True
    assert await manager.connect_ui("ui-2", MockWebSocket(), FAR_FUTURE_EXP) is True
    # Third client exceeds the limit and must be rejected.
    assert await manager.connect_ui("ui-3", MockWebSocket(), FAR_FUTURE_EXP) is False
    assert manager.ui_client_count == 2


async def test_agent_limit_enforcement(
    manager: ConnectionManager, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Connecting max_ws_agents+1 agents: the last call returns False."""
    from app.services import connection_manager as cm_module
    monkeypatch.setattr(cm_module.settings, "max_ws_agents", 2, raising=False)

    assert await manager.connect_agent("a-1", MockWebSocket()) is True
    assert await manager.connect_agent("a-2", MockWebSocket()) is True
    assert await manager.connect_agent("a-3", MockWebSocket()) is False
    assert manager.agent_count == 2


async def test_broadcast_to_ui_skips_agents(manager: ConnectionManager) -> None:
    """broadcast_to_ui delivers only to UI pool, never to the agent pool."""
    ui_a = MockWebSocket()
    ui_b = MockWebSocket()
    agent_c = MockWebSocket()

    await manager.connect_ui("ui-a", ui_a, FAR_FUTURE_EXP)
    await manager.connect_ui("ui-b", ui_b, FAR_FUTURE_EXP)
    await manager.connect_agent("agent-c", agent_c)

    sent = await manager.broadcast_to_ui(
        "task_status", {"task_id": "t-1", "status": "running"}
    )

    assert sent == 2
    assert len(ui_a.sent) == 1
    assert len(ui_b.sent) == 1
    # Agent pool must not receive broadcast_to_ui traffic (D-09).
    assert agent_c.sent == []
    assert ui_a.sent[0]["event"] == "task_status"
    assert ui_a.sent[0]["data"]["task_id"] == "t-1"


async def test_flush_batch_drains_buffer(manager: ConnectionManager) -> None:
    """Non-critical events buffer until flush_batch is called."""
    ws = MockWebSocket()
    await manager.connect_ui("ui-1", ws, FAR_FUTURE_EXP)

    # Non-critical: nothing should be sent yet.
    sent_now = await manager.broadcast_to_ui(
        "heartbeat_tick", {"agent_id": "a-1"}, critical=False
    )
    assert sent_now == 0
    assert ws.sent == []

    # flush_batch drains the buffer and actually delivers the event.
    flushed = await manager.flush_batch()
    assert flushed == 1
    assert len(ws.sent) == 1
    assert ws.sent[0]["event"] == "heartbeat_tick"
    # Buffer is now empty - a second flush is a no-op.
    assert await manager.flush_batch() == 0


async def test_disconnect_nonexistent_is_safe(manager: ConnectionManager) -> None:
    """Disconnecting an unknown client_id / agent_id must not raise."""
    # No connects have been performed - these should be silent no-ops.
    await manager.disconnect_ui("does-not-exist")
    await manager.disconnect_agent("also-missing")

    assert manager.ui_client_count == 0
    assert manager.agent_count == 0
