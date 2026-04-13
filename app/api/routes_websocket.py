"""
WebSocket real-time events for agents
"""
import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from ..logging import get_logger
from ..database.connection import get_database
from ..auth.api_key_deps import resolve_agent_id
from ..auth.api_keys import APIKeyManager

logger = get_logger(__name__)

router = APIRouter(tags=["websocket"])

# Active WebSocket connections: {agent_id: WebSocket}
_connections: Dict[str, WebSocket] = {}


@router.websocket("/v1/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(None),
):
    """
    WebSocket connection for real-time events.
    Connect with: ws://hub.brunhilde.cloud/v1/ws?token=oh_...

    Events pushed to client:
    - task_assigned: new task assigned to you
    - message_received: new DM or thread message
    - agent_status_changed: agent went online/offline
    - task_completed: a task you created was completed
    """
    # Authenticate
    if not token:
        await websocket.close(code=4001, reason="token query param required")
        return

    db = get_database()
    mgr = APIKeyManager(db)
    key_info = mgr.validate_api_key(token)
    if not key_info:
        await websocket.close(code=4001, reason="invalid token")
        return

    # Resolve agent ID
    agent_id = resolve_agent_id(key_info, db)
    if not agent_id:
        await websocket.close(code=4002, reason="agent not found")
        return

    await websocket.accept()

    _connections[agent_id] = websocket
    logger.info("ws_connected", agent_id=agent_id)

    try:
        # Send welcome
        await websocket.send_json({
            "event": "connected",
            "agent_id": agent_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        # Keep alive + listen for client messages
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=60)
                # Handle client messages (ping/pong, etc)
                msg = json.loads(data) if data else {}
                if msg.get("type") == "ping":
                    await websocket.send_json({"event": "pong"})
            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_json({"event": "heartbeat", "timestamp": datetime.now(timezone.utc).isoformat()})
            except WebSocketDisconnect:
                break

    except Exception as e:
        logger.warning("ws_error", agent_id=agent_id, error=str(e))
    finally:
        _connections.pop(agent_id, None)
        logger.info("ws_disconnected", agent_id=agent_id)


async def push_event(agent_id: str, event_type: str, data: Dict) -> bool:
    """Push an event to a connected agent via WebSocket."""
    ws = _connections.get(agent_id)
    if not ws:
        return False

    try:
        await ws.send_json({
            "event": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return True
    except Exception:
        _connections.pop(agent_id, None)
        return False


async def broadcast_event(event_type: str, data: Dict, exclude: str = None) -> int:
    """Broadcast event to all connected agents."""
    sent = 0
    for agent_id, ws in list(_connections.items()):
        if agent_id == exclude:
            continue
        try:
            await ws.send_json({
                "event": event_type,
                "data": data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            sent += 1
        except Exception:
            _connections.pop(agent_id, None)
    return sent


def get_connected_count() -> int:
    return len(_connections)


def get_connected_agents() -> list:
    return list(_connections.keys())
