"""
Event delivery service - webhook notifications to remote agents
"""
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

import httpx

from ..logging import get_logger
from ..database.connection import Database

logger = get_logger(__name__)


class EventDeliveryService:
    """Delivers events to agents via webhook callbacks"""

    def __init__(self, database: Database):
        self.db = database
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=15.0)
        return self._client

    async def notify_task_assigned(self, agent_id: str, task_data: Dict[str, Any]) -> bool:
        """Notify an agent that a task has been assigned to them"""
        callback_url = self._get_agent_callback(agent_id)
        if not callback_url:
            logger.debug("no_callback_url", agent_id=agent_id)
            return False

        payload = {
            "event": "task_assigned",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": task_data,
        }

        return await self._deliver(callback_url, payload)

    async def notify_task_completed(self, agent_id: str, task_id: str, result: str) -> bool:
        """Notify task creator that task is complete"""
        callback_url = self._get_agent_callback(agent_id)
        if not callback_url:
            return False

        payload = {
            "event": "task_completed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {"task_id": task_id, "result_summary": result},
        }

        return await self._deliver(callback_url, payload)

    async def broadcast(self, event_type: str, data: Dict[str, Any]) -> int:
        """Broadcast event to all agents with callback URLs"""
        mappings = self.db.fetch_all(
            "SELECT local_agent_id, callback_url FROM remote_agent_mappings WHERE callback_url IS NOT NULL"
        )

        delivered = 0
        payload = {
            "event": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }

        for mapping in mappings:
            url = mapping["callback_url"] if isinstance(mapping, dict) else mapping[1]
            if url:
                success = await self._deliver(url, payload)
                if success:
                    delivered += 1

        logger.info("event_broadcast", event_type=event_type, delivered=delivered)
        return delivered

    def _get_agent_callback(self, agent_id: str) -> Optional[str]:
        """Get callback URL for an agent"""
        row = self.db.fetch_one(
            "SELECT callback_url FROM remote_agent_mappings WHERE local_agent_id = :id",
            {"id": agent_id}
        )
        if row:
            return row["callback_url"] if isinstance(row, dict) else row[0]
        return None

    async def _deliver(self, url: str, payload: Dict[str, Any]) -> bool:
        """Deliver event via HTTP POST"""
        try:
            client = await self._get_client()
            resp = await client.post(url, json=payload)
            if resp.status_code < 300:
                logger.debug("event_delivered", url=url[:50])
                return True
            else:
                logger.warning("event_delivery_failed", url=url[:50], status=resp.status_code)
                return False
        except Exception as e:
            logger.warning("event_delivery_error", url=url[:50], error=str(e))
            return False

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
