from types import SimpleNamespace

import pytest

from app.api.routes_acn import _broadcast_acn_ui_event


class FakeConnectionManager:
    def __init__(self):
        self.calls = []

    async def broadcast_to_ui(self, event_type, data, critical=True):
        self.calls.append((event_type, data, critical))
        return 1


@pytest.mark.asyncio
async def test_broadcast_acn_ui_event_sends_via_connection_manager():
    cm = FakeConnectionManager()
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(connection_manager=cm)))

    sent = await _broadcast_acn_ui_event(
        request,
        "agent_status_changed",
        {"agent_id": "agent-1", "status": "online"},
    )

    assert sent == 1
    assert cm.calls == [
        (
            "agent_status_changed",
            {"agent_id": "agent-1", "status": "online"},
            True,
        )
    ]


@pytest.mark.asyncio
async def test_broadcast_acn_ui_event_is_safe_when_manager_missing():
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))

    sent = await _broadcast_acn_ui_event(
        request,
        "agent_status_changed",
        {"agent_id": "agent-1", "status": "online"},
    )

    assert sent == 0
