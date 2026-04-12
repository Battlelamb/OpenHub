"""
WebSocket endpoint for dashboard UI clients (WS-01).

Authenticates via JWT in the initial client message frame (D-03) - tokens
never appear in URL query strings or access logs. Registers accepted clients
with the ConnectionManager (from app.state) and then enters a message loop
that handles ping/pong and mid-connection token refresh.

Close codes (D-14):
    4001 - auth failure (missing / invalid / expired token, auth timeout)
    4002 - connection limit reached
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..auth.jwt_auth import verify_token
from ..logging import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["websocket"])


# Auth handshake timeout in seconds. Long enough for normal browser clients,
# short enough that idle/misbehaving connections do not pile up.
_AUTH_TIMEOUT_SEC: float = 10.0


@router.websocket("/v1/ws/ui")
async def websocket_ui_endpoint(websocket: WebSocket) -> None:
    """
    Dashboard UI WebSocket entry point.

    Protocol:
        1. Server accepts the WebSocket handshake.
        2. Client MUST send a JSON message `{"token": "<jwt>"}` within
           _AUTH_TIMEOUT_SEC seconds. Tokens MUST NOT be passed via query
           string (D-03).
        3. On successful auth, server emits a `connected` welcome event and
           registers the client with the ConnectionManager.
        4. Client may send:
             - `{"type": "ping"}`                          -> `{"event": "pong"}`
             - `{"type": "refresh_token", "token": "..."}` -> expiry refreshed
    """
    # Step 1: Accept the handshake. WS protocol requires accept() before any
    # close frame can be delivered (close frames on an un-accepted socket are
    # silently dropped by some client implementations).
    await websocket.accept()
    logger.info("ws_ui_auth_started")

    # Step 2: Wait for the auth message.
    try:
        raw = await asyncio.wait_for(
            websocket.receive_text(), timeout=_AUTH_TIMEOUT_SEC
        )
    except asyncio.TimeoutError:
        logger.warning("ws_ui_auth_failed", reason="auth_timeout")
        await websocket.close(code=4001, reason="auth timeout")
        return
    except WebSocketDisconnect:
        logger.info("ws_ui_disconnected", phase="pre_auth")
        return

    try:
        msg = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        logger.warning("ws_ui_auth_failed", reason="invalid_json")
        await websocket.close(code=4001, reason="invalid auth format")
        return

    token = msg.get("token") if isinstance(msg, dict) else None
    if not token or not isinstance(token, str):
        logger.warning("ws_ui_auth_failed", reason="token_missing")
        await websocket.close(code=4001, reason="token required in first message")
        return

    # Step 3: Verify JWT.
    try:
        payload = verify_token(token, expected_type="access")
    except jwt.ExpiredSignatureError:
        logger.warning("ws_ui_auth_failed", reason="token_expired")
        await websocket.close(code=4001, reason="expired token")
        return
    except jwt.InvalidTokenError:
        logger.warning("ws_ui_auth_failed", reason="token_invalid")
        await websocket.close(code=4001, reason="invalid token")
        return
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("ws_ui_auth_failed", reason="verify_error", error=str(exc))
        await websocket.close(code=4001, reason="auth error")
        return

    client_id = str(payload.get("sub", ""))
    jwt_exp = float(payload.get("exp", 0))
    if not client_id or jwt_exp <= 0:
        logger.warning("ws_ui_auth_failed", reason="malformed_claims")
        await websocket.close(code=4001, reason="malformed token claims")
        return

    # Step 4: Register with ConnectionManager (stored on app.state in lifespan).
    cm = getattr(websocket.app.state, "connection_manager", None)
    if cm is None:
        logger.error("ws_ui_connection_manager_missing")
        await websocket.close(code=4003, reason="server not ready")
        return

    accepted = await cm.connect_ui(client_id, websocket, jwt_exp)
    if not accepted:
        logger.warning("ws_ui_limit_reached", client_id=client_id)
        await websocket.close(code=4002, reason="connection limit reached")
        return

    logger.info("ws_ui_connected", client_id=client_id)

    # Step 5: Welcome event. The canonical envelope (D-01) uses `agent_id`
    # field; for UI clients we set it to null and carry the session identity
    # inside `data.client_id` so UI clients are not misrepresented as agents
    # (review MED fix).
    try:
        await websocket.send_json(
            {
                "event": "connected",
                "agent_id": None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {
                    "client_id": client_id,
                    "role": payload.get("role", "unknown"),
                },
            }
        )
    except Exception as exc:
        logger.warning(
            "ws_ui_welcome_send_failed", client_id=client_id, error=str(exc)
        )
        await cm.disconnect_ui(client_id)
        return

    # Step 6: Message loop.
    try:
        while True:
            try:
                raw = await websocket.receive_text()
            except WebSocketDisconnect:
                break

            try:
                msg = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                logger.debug("ws_ui_invalid_json", client_id=client_id)
                continue

            if not isinstance(msg, dict):
                continue

            msg_type = msg.get("type")

            if msg_type == "ping":
                try:
                    await websocket.send_json(
                        {
                            "event": "pong",
                            "agent_id": None,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "data": {"client_id": client_id},
                        }
                    )
                except Exception as exc:
                    logger.warning(
                        "ws_ui_pong_failed", client_id=client_id, error=str(exc)
                    )
                    break
                continue

            if msg_type == "refresh_token":
                new_token = msg.get("token")
                if not new_token or not isinstance(new_token, str):
                    logger.debug(
                        "ws_ui_refresh_failed",
                        client_id=client_id,
                        reason="token_missing",
                    )
                    continue
                try:
                    new_payload = verify_token(new_token, expected_type="access")
                except (jwt.ExpiredSignatureError, jwt.InvalidTokenError) as exc:
                    # Refresh failure is not fatal to the existing connection:
                    # the old JWT still governs the session. The batch loop
                    # will disconnect on its own when the tracked exp lapses.
                    logger.warning(
                        "ws_ui_refresh_rejected",
                        client_id=client_id,
                        error=str(exc),
                    )
                    continue
                new_exp = float(new_payload.get("exp", 0))
                if new_exp <= 0:
                    logger.debug(
                        "ws_ui_refresh_failed",
                        client_id=client_id,
                        reason="malformed_exp",
                    )
                    continue
                # Use the public API (review HIGH fix) - no direct dict mutation.
                cm.refresh_ui_expiry(client_id, new_exp)
                logger.info("ws_ui_token_refreshed", client_id=client_id)
                continue

            # Unknown message type: ignore but log at debug.
            logger.debug(
                "ws_ui_unknown_message", client_id=client_id, type=msg_type
            )

    except Exception as exc:
        logger.warning(
            "ws_ui_loop_error", client_id=client_id, error=str(exc)
        )
    finally:
        await cm.disconnect_ui(client_id)
        logger.info("ws_ui_disconnected", client_id=client_id)
