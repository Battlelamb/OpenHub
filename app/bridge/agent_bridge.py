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
        dry_run: bool = True,
    ):
        self.hub_url = hub_url.rstrip("/")
        self.agent_name = agent_name
        self.capabilities = capabilities
        self.api_key = api_key
        self.node_name = node_name
        self.description = description or f"Remote agent: {agent_name}"
        self.heartbeat_interval = heartbeat_interval
        self.task_poll_interval = task_poll_interval
        self.dry_run = dry_run

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
                    if agent.get("agent_name") == self.agent_name or agent.get("name") == self.agent_name:
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
        """Poll available and owned tasks.

        Safe default: dry-run only observes and logs. If a task handler is
        registered and dry_run is false, the bridge claims, starts, handles,
        and submits completion/failure for available work.
        """
        while self._running:
            try:
                if self.agent_id:
                    resp = await self.client.get("/v1/acn/tasks/poll?limit=5")
                    if resp.status_code == 200:
                        data = resp.json()
                        available = data.get("available", [])
                        owned = data.get("owned", [])
                        if available:
                            logger.info("bridge_tasks_available", count=len(available), dry_run=self.dry_run)
                        if owned:
                            logger.info("bridge_tasks_owned", count=len(owned))

                        if self._task_handler and not self.dry_run:
                            for task in available:
                                await self._claim_start_handle(task)
                            for task in owned:
                                if task.get("status") == "claimed":
                                    await self._start_and_handle(task)
            except Exception as e:
                logger.warning("bridge_task_poll_error", error=str(e))

            await asyncio.sleep(self.task_poll_interval)

    async def _claim_start_handle(self, task: Dict[str, Any]) -> None:
        task_id = task.get("task_id")
        if not task_id:
            return
        claim_resp = await self.client.post(f"/v1/acn/tasks/{task_id}/claim")
        if claim_resp.status_code != 200:
            logger.warning("bridge_task_claim_failed", task_id=task_id, status_code=claim_resp.status_code)
            return
        await self._start_and_handle(task)

    async def _start_and_handle(self, task: Dict[str, Any]) -> None:
        task_id = task.get("task_id")
        if not task_id or not self._task_handler:
            return
        start_resp = await self.client.post(f"/v1/acn/tasks/{task_id}/start")
        if start_resp.status_code != 200:
            logger.warning("bridge_task_start_failed", task_id=task_id, status_code=start_resp.status_code)
            return
        try:
            result = await self._task_handler(task)
            summary = "Task completed"
            output: Dict[str, Any] = {}
            if isinstance(result, dict):
                summary = str(result.get("result_summary") or result.get("summary") or summary)
                output = result.get("output") if isinstance(result.get("output"), dict) else result
            elif result is not None:
                summary = str(result)
            await self.submit_result(task_id, summary, output)
        except Exception as e:
            logger.error("bridge_task_handler_error", task_id=task_id, error=str(e))
            await self.client.post(
                f"/v1/acn/tasks/{task_id}/fail",
                params={"error_message": str(e), "retryable": True},
            )

    async def submit_result(self, task_id: str, result_summary: str, output: Optional[Dict] = None) -> bool:
        """Submit task result"""
        try:
            resp = await self.client.post(
                f"/v1/acn/tasks/{task_id}/complete",
                params={"result_summary": result_summary},
                json=output or {},
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
