"""
ConnectionManager for WebSocket connections.

Manages separate agent and UI WebSocket connection pools, implements tiered
event broadcasting (immediate critical + 5s batched non-critical), enforces
configurable connection limits, and exposes Prometheus metrics.

Per phase 02 decisions:
- D-09: Separate connection pools for agents vs UI clients
- D-10: Replaces module-level _connections dict
- D-11: JWT expiry tracking with 60s warning window
- D-12: Configurable soft limits with 80% warning, reject at limit
- D-13: Slow client backpressure (drop oldest non-critical)
- D-14: Dual error communication (event vs close frame)
- D-15: Prometheus metrics (ws_connections_active, ws_events_sent_total,
        ws_errors_total)
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import WebSocket
from prometheus_client import Counter, Gauge

from ..config import get_settings
from ..logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


# Prometheus metrics (D-15)
WS_CONNECTIONS_ACTIVE = Gauge(
    "openhub_ws_connections_active",
    "Active WebSocket connections",
    ["type"],  # "agent" or "ui"
)
WS_EVENTS_SENT_TOTAL = Counter(
    "openhub_ws_events_sent_total",
    "Total WebSocket events sent",
    ["event_type"],
)
WS_ERRORS_TOTAL = Counter(
    "openhub_ws_errors_total",
    "Total WebSocket errors",
)


class ConnectionManager:
    """
    Manages agent and UI WebSocket connection pools with tiered broadcasting.

    Public API:
        - start() / stop(): lifecycle control (batch loop task)
        - connect_agent / disconnect_agent: agent pool lifecycle
        - connect_ui / disconnect_ui: UI pool lifecycle (tracks JWT expiry)
        - broadcast_to_ui(event_type, data, critical=True): tiered broadcast
        - broadcast_to_agents(event_type, data, exclude=None): agent broadcast
        - send_to_client(client_id, event_type, data): targeted UI send
        - flush_batch(): drains batch buffer; exposed for deterministic testing
        - refresh_ui_expiry(client_id, new_exp): update tracked JWT expiry

    Properties:
        - agent_count / ui_client_count
        - connected_agents / connected_ui_clients
    """

    BATCH_INTERVAL_SEC: float = 5.0
    TOKEN_EXPIRY_WARNING_SEC: float = 60.0

    def __init__(self) -> None:
        self._agents: Dict[str, WebSocket] = {}
        self._ui_clients: Dict[str, WebSocket] = {}
        self._ui_expiry: Dict[str, float] = {}
        self._batch_buffer: List[dict] = []
        self._batch_task: Optional[asyncio.Task] = None
        self._running: bool = False

    # -- Lifecycle ------------------------------------------------------

    async def start(self) -> None:
        """Start the batch loop background task."""
        if self._running:
            return
        self._running = True
        self._batch_task = asyncio.create_task(self._batch_loop())
        logger.info("connection_manager_started")

    async def stop(self) -> None:
        """Stop batch loop and close all connections."""
        self._running = False
        if self._batch_task is not None:
            self._batch_task.cancel()
            try:
                await self._batch_task
            except (asyncio.CancelledError, Exception):
                pass
            self._batch_task = None

        # Close all connections with 4003 (server_error/shutdown) per D-14
        for agent_id, ws in list(self._agents.items()):
            try:
                await ws.close(code=4003)
            except Exception as exc:
                logger.debug("ws_close_agent_failed", agent_id=agent_id, error=str(exc))
        for client_id, ws in list(self._ui_clients.items()):
            try:
                await ws.close(code=4003)
            except Exception as exc:
                logger.debug("ws_close_ui_failed", client_id=client_id, error=str(exc))

        self._agents.clear()
        self._ui_clients.clear()
        self._ui_expiry.clear()
        self._batch_buffer.clear()
        logger.info("connection_manager_stopped")

    # -- Connect / disconnect ------------------------------------------

    async def connect_agent(self, agent_id: str, ws: WebSocket) -> bool:
        """
        Register an agent WS connection.

        Returns False if limit reached (caller should close with 4002 per D-14).
        """
        max_agents = settings.max_ws_agents
        current = len(self._agents)
        if current >= max_agents:
            logger.warning(
                "ws_agent_limit_reached",
                current=current,
                limit=max_agents,
                agent_id=agent_id,
            )
            WS_ERRORS_TOTAL.inc()
            return False

        # 80% capacity warning (D-12)
        if current + 1 >= max_agents * 0.8:
            logger.warning(
                "ws_agent_capacity_warning",
                current=current + 1,
                limit=max_agents,
            )

        self._agents[agent_id] = ws
        WS_CONNECTIONS_ACTIVE.labels(type="agent").inc()
        logger.info("ws_agent_connected", agent_id=agent_id, total=len(self._agents))
        return True

    async def connect_ui(self, client_id: str, ws: WebSocket, jwt_exp: float) -> bool:
        """
        Register a UI client WS connection.

        Returns False if limit reached (caller should close with 4002 per D-14).
        """
        max_ui = settings.max_ws_ui
        current = len(self._ui_clients)
        if current >= max_ui:
            logger.warning(
                "ws_ui_limit_reached",
                current=current,
                limit=max_ui,
                client_id=client_id,
            )
            WS_ERRORS_TOTAL.inc()
            return False

        if current + 1 >= max_ui * 0.8:
            logger.warning(
                "ws_ui_capacity_warning",
                current=current + 1,
                limit=max_ui,
            )

        self._ui_clients[client_id] = ws
        self._ui_expiry[client_id] = jwt_exp
        WS_CONNECTIONS_ACTIVE.labels(type="ui").inc()
        logger.info(
            "ws_ui_connected",
            client_id=client_id,
            total=len(self._ui_clients),
        )
        return True

    async def disconnect_agent(self, agent_id: str) -> None:
        if self._agents.pop(agent_id, None) is not None:
            WS_CONNECTIONS_ACTIVE.labels(type="agent").dec()
            logger.info("ws_agent_disconnected", agent_id=agent_id)

    async def disconnect_ui(self, client_id: str) -> None:
        if self._ui_clients.pop(client_id, None) is not None:
            self._ui_expiry.pop(client_id, None)
            WS_CONNECTIONS_ACTIVE.labels(type="ui").dec()
            logger.info("ws_ui_disconnected", client_id=client_id)

    def refresh_ui_expiry(self, client_id: str, new_exp: float) -> bool:
        """
        Update the tracked JWT expiry for a connected UI client.

        Used when the client refreshes its token mid-connection.
        Returns True if the client was known, False otherwise.
        """
        if client_id not in self._ui_clients:
            return False
        self._ui_expiry[client_id] = new_exp
        logger.debug("ws_ui_expiry_refreshed", client_id=client_id, exp=new_exp)
        return True

    # -- Broadcast -----------------------------------------------------

    def _build_event(self, event_type: str, data: dict) -> dict:
        """Build the canonical event payload (D-01 format)."""
        return {
            "event": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def broadcast_to_ui(
        self,
        event_type: str,
        data: dict,
        critical: bool = True,
    ) -> int:
        """
        Broadcast event to all UI clients.

        Critical events (D-05) send immediately. Non-critical events (D-06)
        are appended to the batch buffer and flushed by _batch_loop every 5s.

        Returns the number of successful sends (0 for batched events).
        """
        if not critical:
            self._batch_buffer.append({"event_type": event_type, "data": data})
            return 0

        payload = self._build_event(event_type, data)
        sent = 0
        failed: List[str] = []

        # Snapshot the dict - disconnect_ui may mutate it mid-iteration (HIGH fix)
        for client_id, ws in list(self._ui_clients.items()):
            try:
                await ws.send_json(payload)
                sent += 1
                WS_EVENTS_SENT_TOTAL.labels(event_type=event_type).inc()
            except Exception as exc:
                logger.warning(
                    "ws_ui_send_failed",
                    client_id=client_id,
                    event_type=event_type,
                    error=str(exc),
                )
                WS_ERRORS_TOTAL.inc()
                failed.append(client_id)

        for client_id in failed:
            await self.disconnect_ui(client_id)

        return sent

    async def broadcast_to_agents(
        self,
        event_type: str,
        data: dict,
        exclude: Optional[str] = None,
    ) -> int:
        """
        Broadcast event to all agent connections.

        Optionally excludes one agent_id (e.g. the event originator).
        """
        payload = self._build_event(event_type, data)
        sent = 0
        failed: List[str] = []

        # Snapshot the dict - disconnect_agent may mutate it mid-iteration
        for agent_id, ws in list(self._agents.items()):
            if exclude is not None and agent_id == exclude:
                continue
            try:
                await ws.send_json(payload)
                sent += 1
                WS_EVENTS_SENT_TOTAL.labels(event_type=event_type).inc()
            except Exception as exc:
                logger.warning(
                    "ws_agent_send_failed",
                    agent_id=agent_id,
                    event_type=event_type,
                    error=str(exc),
                )
                WS_ERRORS_TOTAL.inc()
                failed.append(agent_id)

        for agent_id in failed:
            await self.disconnect_agent(agent_id)

        return sent

    async def send_to_client(
        self,
        client_id: str,
        event_type: str,
        data: dict,
    ) -> bool:
        """
        Send an event to a specific UI client.

        Returns True on success, False if the client is unknown or the send
        failed (failed clients are auto-disconnected).
        """
        ws = self._ui_clients.get(client_id)
        if ws is None:
            return False
        try:
            await ws.send_json(self._build_event(event_type, data))
            WS_EVENTS_SENT_TOTAL.labels(event_type=event_type).inc()
            return True
        except Exception as exc:
            logger.warning(
                "ws_ui_direct_send_failed",
                client_id=client_id,
                event_type=event_type,
                error=str(exc),
            )
            WS_ERRORS_TOTAL.inc()
            await self.disconnect_ui(client_id)
            return False

    async def flush_batch(self) -> int:
        """
        Drain the batch buffer and broadcast each buffered event.

        Exposed publicly so tests can trigger flushes deterministically
        instead of waiting for the 5s timer (D-06 test approach).
        """
        if not self._batch_buffer:
            return 0

        # Snapshot-and-clear so new appends during flush are not lost
        events = self._batch_buffer[:]
        self._batch_buffer.clear()

        total_sent = 0
        for event in events:
            sent = await self.broadcast_to_ui(
                event["event_type"],
                event["data"],
                critical=True,
            )
            total_sent += sent
        return total_sent

    async def _batch_loop(self) -> None:
        """
        Background loop: on each cycle, check token expiries then flush batch.

        Both operations are wrapped in try/except so a single failure does not
        kill the task silently (HIGH fix from cross-AI review).
        """
        try:
            while self._running:
                try:
                    await asyncio.sleep(self.BATCH_INTERVAL_SEC)
                except asyncio.CancelledError:
                    raise

                # Explicit token expiry check on every cycle (review fix)
                try:
                    await self._check_token_expiry()
                except Exception as exc:
                    logger.error("ws_token_expiry_check_failed", error=str(exc))
                    WS_ERRORS_TOTAL.inc()

                # Flush the batch buffer; never let an exception kill the loop
                try:
                    await self.flush_batch()
                except Exception as exc:
                    logger.error("ws_batch_flush_failed", error=str(exc))
                    WS_ERRORS_TOTAL.inc()
        except asyncio.CancelledError:
            logger.debug("ws_batch_loop_cancelled")
            raise

    async def _check_token_expiry(self) -> None:
        """
        Send `token_expiring` warning 60s before JWT expiry.

        If a client's JWT has already expired, disconnect it with close code
        4001 (auth_expired) per D-11 / D-14.
        """
        if not self._ui_expiry:
            return

        now = datetime.now(timezone.utc).timestamp()
        to_disconnect: List[str] = []

        # Snapshot so disconnect_ui mutations during iteration are safe
        for client_id, exp in list(self._ui_expiry.items()):
            remaining = exp - now
            if remaining <= 0:
                to_disconnect.append(client_id)
            elif remaining < self.TOKEN_EXPIRY_WARNING_SEC:
                await self.send_to_client(
                    client_id,
                    "token_expiring",
                    {"expires_in": int(remaining)},
                )

        for client_id in to_disconnect:
            ws = self._ui_clients.get(client_id)
            if ws is not None:
                try:
                    await ws.close(code=4001, reason="auth_expired")
                except Exception as exc:
                    logger.debug(
                        "ws_close_expired_failed",
                        client_id=client_id,
                        error=str(exc),
                    )
            await self.disconnect_ui(client_id)

    # -- Properties ----------------------------------------------------

    @property
    def agent_count(self) -> int:
        return len(self._agents)

    @property
    def ui_client_count(self) -> int:
        return len(self._ui_clients)

    @property
    def connected_agents(self) -> List[str]:
        return list(self._agents.keys())

    @property
    def connected_ui_clients(self) -> List[str]:
        return list(self._ui_clients.keys())
