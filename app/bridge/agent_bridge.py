"""
Agent Bridge Client - connects a remote agent to OpenHub

Usage:
    bridge = AgentBridge(
        hub_url="https://hub.brunhilde.cloud",
        agent_name="my-agent",
        capabilities=["code_edit", "review"],
        api_key="oh_...",
    )
    asyncio.run(bridge.run())
"""
import asyncio
import signal
from typing import List, Optional, Dict, Any, Callable

import httpx

from ..logging import get_logger

logger = get_logger(__name__)


class AgentBridge:
    """Lightweight bridge client for remote agents"""

    def __init__(
        self,
        hub_url: str,
        agent_name: str,
        capabilities: List[str],
        api_key: str,
        node_name: str = "default-node",
        description: Optional[str] = None,
        heartbeat_interval: int = 60,
        task_poll_interval: int = 10,
    ):
        self.hub_url = hub_url.rstrip("/")
        self.agent_name = agent_name
        self.capabilities = capabilities
        self.api_key = api_key
        self.node_name = node_name
        self.description = description or f"Remote agent: {agent_name}"
        self.heartbeat_interval = heartbeat_interval
        self.task_poll_interval = task_poll_interval

        self.client = httpx.AsyncClient(
            base_url=self.hub_url,
            headers={
                "Content-Type": "application/json",
                "X-API-Key": api_key,
            },
            timeout=30.0,
        )

        self.agent_id: Optional[str] = None
        self.node_id: Optional[str] = None
        self._running = False
        self._task_handler: Optional[Callable] = None

    def on_task(self, handler: Callable):
        """Register a task handler callback"""
        self._task_handler = handler
        return handler

    async def _discover_self(self) -> bool:
        """Find this agent's ID from the hub"""
        try:
            resp = await self.client.get("/v1/acn/agents")
            if resp.status_code == 200:
                agents = resp.json().get("remote_agents", [])
                for agent in agents:
                    if agent["agent_name"] == self.agent_name:
                        self.agent_id = agent["agent_id"]
                        self.node_id = agent.get("node_id")
                        logger.info("bridge_agent_found",
                                   agent_id=self.agent_id,
                                   agent_name=self.agent_name)
                        return True

            logger.warning("bridge_agent_not_found", agent_name=self.agent_name)
            return False
        except Exception as e:
            logger.error("bridge_discover_error", error=str(e))
            return False

    async def _try_register(self) -> bool:
        """Try to register if not found"""
        try:
            resp = await self.client.post("/v1/acn/agents/register", json={
                "agent_name": self.agent_name,
                "capabilities": self.capabilities,
                "node_name": self.node_name,
                "description": self.description,
            })
            if resp.status_code == 200:
                data = resp.json()
                self.agent_id = data.get("id")
                logger.info("bridge_agent_registered", agent_id=self.agent_id)
                return True
        except Exception:
            pass
        return False

    async def heartbeat(self) -> bool:
        """Send heartbeat via node endpoint"""
        try:
            if self.node_id:
                resp = await self.client.post(f"/v1/acn/nodes/{self.node_id}/heartbeat")
                if resp.status_code == 200:
                    logger.debug("bridge_heartbeat_sent", node_id=self.node_id)
                    return True
            return False
        except Exception as e:
            logger.warning("bridge_heartbeat_failed", error=str(e))
            return False

    async def _heartbeat_loop(self):
        """Background heartbeat loop"""
        while self._running:
            await self.heartbeat()
            await asyncio.sleep(self.heartbeat_interval)

    async def _task_poll_loop(self):
        """Background task polling - checks for claimed tasks assigned to this agent"""
        while self._running:
            try:
                if self.agent_id:
                    # Check for tasks assigned to me (claimed = needs start, or available = needs claim)
                    resp = await self.client.get(
                        f"/v1/acn/tasks/available?agent_id={self.agent_id}&limit=5"
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        tasks = data.get("tasks", [])
                        if tasks:
                            logger.info("bridge_tasks_available", count=len(tasks))

                    # Also check my assigned tasks (claimed/running)
                    resp2 = await self.client.get(
                        f"/v1/acn/tasks/mine?agent_id={self.agent_id}"
                    )
                    if resp2.status_code == 200:
                        my_tasks = resp2.json().get("tasks", [])
                        for task in my_tasks:
                            task_status = task.get("status", "")
                            if task_status == "claimed":
                                logger.info("bridge_task_claimed_found",
                                           task_id=task.get("task_id"), title=task.get("title"))
                                if self._task_handler:
                                    try:
                                        await self._task_handler(task)
                                    except Exception as e:
                                        logger.error("bridge_task_handler_error",
                                                   task_id=task.get("task_id"), error=str(e))
            except Exception as e:
                logger.warning("bridge_task_poll_error", error=str(e))

            await asyncio.sleep(self.task_poll_interval)

    async def submit_result(self, task_id: str, result_summary: str, output: Optional[Dict] = None) -> bool:
        """Submit task result"""
        try:
            resp = await self.client.post(
                f"/v1/acn/tasks/{task_id}/complete?agent_id={self.agent_id}&result_summary={result_summary}"
            )
            return resp.status_code == 200
        except Exception as e:
            logger.error("bridge_submit_error", error=str(e))
            return False

    async def run(self):
        """Main run loop"""
        logger.info("bridge_starting", hub_url=self.hub_url, agent_name=self.agent_name)

        # Discover or register
        found = await self._discover_self()
        if not found:
            registered = await self._try_register()
            if not registered:
                logger.error("bridge_cannot_find_or_register")
                return

        self._running = True

        # Graceful shutdown
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, lambda: self.stop())
            except NotImplementedError:
                pass

        logger.info("bridge_running", agent_id=self.agent_id, agent_name=self.agent_name)

        tasks = [
            asyncio.create_task(self._heartbeat_loop()),
            asyncio.create_task(self._task_poll_loop()),
        ]

        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            pass
        finally:
            await self.client.aclose()
            logger.info("bridge_stopped", agent_name=self.agent_name)

    def stop(self):
        self._running = False
