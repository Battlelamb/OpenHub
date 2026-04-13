"""
Integration tests for /v1/ws/ui (TEST-05, WS-06).

Exercises the full ASGI WebSocket stack via Starlette's TestClient.
Covers the auth handshake (success, missing, invalid, expired), the
ping/pong message loop, clean disconnect cleanup of the
ConnectionManager UI pool, and the WS-06 requirement that
workflow_progress events broadcast via `broadcast_to_ui` actually
reach connected UI clients.

All test functions are synchronous per research Pitfall 3 - TestClient
runs the ASGI app in a background worker thread with its own anyio
portal. Mixing `async def` test functions with TestClient causes event
loop conflicts. When we need to invoke an async ConnectionManager
method from inside a test, we use `ws.portal.call(coro_fn)` which
schedules the coroutine on the ASGI worker's event loop - this is the
only correct way to drive the same loop that owns the WebSocket.
"""
from __future__ import annotations

from datetime import timedelta

from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.auth.jwt_auth import create_access_token


# ---------------------------------------------------------------------------
# TEST-05: Auth success
# ---------------------------------------------------------------------------


def test_ws_ui_auth_success(test_client: TestClient, auth_token: str) -> None:
    """Valid JWT in the initial frame yields a `connected` welcome event."""
    with test_client.websocket_connect("/v1/ws/ui") as ws:
        ws.send_json({"token": auth_token})

        data = ws.receive_json()

    assert data["event"] == "connected"
    # UI clients are not agents (review MED fix): envelope agent_id is null,
    # session identity lives in data.client_id.
    assert data["agent_id"] is None
    assert data["data"]["client_id"] == "test-admin"
    assert data["data"]["role"] == "admin"


# ---------------------------------------------------------------------------
# TEST-05: Auth failures (invalid / missing / expired)
# ---------------------------------------------------------------------------


def test_ws_ui_auth_invalid_token(test_client: TestClient) -> None:
    """Garbage token closes the WebSocket with code 4001."""
    with test_client.websocket_connect("/v1/ws/ui") as ws:
        ws.send_json({"token": "invalid-garbage-token"})
        try:
            ws.receive_json()
        except WebSocketDisconnect as exc:
            assert exc.code == 4001
        else:
            raise AssertionError("expected WebSocketDisconnect(4001)")


def test_ws_ui_auth_missing_token(test_client: TestClient) -> None:
    """An initial frame that omits `token` closes with 4001."""
    with test_client.websocket_connect("/v1/ws/ui") as ws:
        ws.send_json({"not_a_token": "oops"})
        try:
            ws.receive_json()
        except WebSocketDisconnect as exc:
            assert exc.code == 4001
        else:
            raise AssertionError("expected WebSocketDisconnect(4001)")


def test_ws_ui_auth_expired_token(test_client: TestClient) -> None:
    """An expired JWT closes with 4001."""
    expired_token = create_access_token(
        subject="test-admin-expired",
        expires_delta=timedelta(seconds=-1),
        claims={"role": "admin"},
    )

    with test_client.websocket_connect("/v1/ws/ui") as ws:
        ws.send_json({"token": expired_token})
        try:
            ws.receive_json()
        except WebSocketDisconnect as exc:
            assert exc.code == 4001
        else:
            raise AssertionError("expected WebSocketDisconnect(4001)")


# ---------------------------------------------------------------------------
# TEST-05: Ping/pong message loop
# ---------------------------------------------------------------------------


def test_ws_ui_ping_pong(test_client: TestClient, auth_token: str) -> None:
    """After auth, a {type: ping} message yields a `pong` event."""
    with test_client.websocket_connect("/v1/ws/ui") as ws:
        ws.send_json({"token": auth_token})
        welcome = ws.receive_json()
        assert welcome["event"] == "connected"

        ws.send_json({"type": "ping"})
        reply = ws.receive_json()

    assert reply["event"] == "pong"
    assert reply["data"]["client_id"] == "test-admin"


# ---------------------------------------------------------------------------
# TEST-05: Disconnect cleanup
# ---------------------------------------------------------------------------


def test_ws_ui_disconnect_cleanup(test_client: TestClient, auth_token: str) -> None:
    """Exiting the websocket context removes the client from the UI pool.

    Uses a relative assertion (count_before - 1 after close) because
    tests/conftest.py uses a session-scoped test_client and the
    ConnectionManager singleton on `app.state` persists across tests -
    an absolute `== 0` check would be flaky if another test left a
    stale connection (review HIGH fix).
    """
    cm = test_client.app.state.connection_manager
    count_before = cm.ui_client_count

    with test_client.websocket_connect("/v1/ws/ui") as ws:
        ws.send_json({"token": auth_token})
        ws.receive_json()  # consume welcome
        assert cm.ui_client_count == count_before + 1

    # The server's finally block runs on the ASGI worker thread after the
    # client closes, so count may not have decremented by the time we return
    # here. Poll briefly for the expected count to avoid a race.
    import time as _time
    deadline = _time.monotonic() + 2.0
    while cm.ui_client_count > count_before and _time.monotonic() < deadline:
        _time.sleep(0.01)
    assert cm.ui_client_count == count_before


# ---------------------------------------------------------------------------
# WS-06: workflow_progress events reach connected UI clients
# ---------------------------------------------------------------------------


def test_ws_ui_workflow_progress_event(
    test_client: TestClient, auth_token: str
) -> None:
    """WS-06: `broadcast_to_ui("workflow_progress", ...)` reaches the client.

    We cannot call `broadcast_to_ui` from the test thread because the
    ConnectionManager's ui_clients are backed by WebSockets that live
    on the ASGI worker's event loop. Starlette's WebSocketTestSession
    exposes the worker portal (`ws.portal`), and `portal.call(fn, ...)`
    runs a coroutine on that loop and returns its result - this is the
    only correct way to drive the same loop that owns the socket.
    """
    cm = test_client.app.state.connection_manager

    with test_client.websocket_connect("/v1/ws/ui") as ws:
        ws.send_json({"token": auth_token})
        welcome = ws.receive_json()
        assert welcome["event"] == "connected"

        # Schedule broadcast_to_ui on the ASGI worker's event loop.
        async def _trigger() -> int:
            return await cm.broadcast_to_ui(
                "workflow_progress",
                {
                    "workflow_id": "wf-123",
                    "step": "validate_input",
                    "status": "completed",
                    "progress_pct": 50,
                },
            )

        sent = ws.portal.call(_trigger)
        assert sent >= 1

        event = ws.receive_json()

    assert event["event"] == "workflow_progress"
    assert event["data"]["workflow_id"] == "wf-123"
    assert event["data"]["step"] == "validate_input"
    assert event["data"]["status"] == "completed"
    assert event["data"]["progress_pct"] == 50
