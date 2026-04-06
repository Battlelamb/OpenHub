"""
Agent Bridge Client - connects a remote agent to OpenHub

Usage:
    bridge = AgentBridge(
        hub_url="https://hub.brunhilde.cloud",
        agent_name="my-agent",
        capabilities=["code_edit", "review"],
    )
    asyncio.run(bridge.run())
"""
import asyncio
import signal
import sys
from datetime import datetime
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
        node_name: str = "default-node",
        node_url: str = "http://localhost",
        description: Optional[str] = None,
        api_key: Optional[str] = None,
        heartbeat_interval: int = 60,
        task_poll_interval: int = 10,
    ):
        self.hub_url = hub_url.rstrip("/")
        self.agent_name = agent_name
        self.capabilities = capabilities
        self.node_name = node_name
        self.node_url = node_url
        self.description = description or f"Remote agent: {agent_name}"
        self.heartbeat_interval = heartbeat_interval
        self.task_poll_interval = task_poll_interval

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["X-API-Key"] = api_key

        self.client = httpx.AsyncClient(
            base_url=self.hub_url,
            headers=headers,
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

    async def register(self) -> bool:
        """Register node and agent with OpenHub"""
        try:
            # Register node (ignore if already exists)
            try:
                resp = await self.client.post("/v1/acn/nodes", json={
                    "node_name": self.node_name,
                    "node_url": self.node_url,
                })
                if resp.status_code == 200:
                    data = resp.json()
                    self.node_id = data.get("id")
                    logger.info("bridge_node_registered",
                               node_id=self.node_id, node_name=self.node_name)
            except Exception:
                logger.debug("bridge_node_already_exists", node_name=self.node_name)

            # Register agent
            resp = await self.client.post("/v1/acn/agents/register", json={
                "agent_name": self.agent_name,
                "capabilities": self.capabilities,
                "node_name": self.node_name,
                "description": self.description,
            })

            if resp.status_code == 200:
                data = resp.json()
                self.agent_id = data.get("id")
                logger.info("bridge_agent_registered",
                           agent_id=self.agent_id, agent_name=self.agent_name)
                return True
            else:
                error = resp.json()
                # Agent might already exist - try to find it
                if "already exists" in str(error):
                    logger.info("bridge_agent_already_registered",
                               agent_name=self.agent_name)
                    # Fetch agent list to get ID
                    agents_resp = await self.client.get("/v1/acn/agents")
                    if agents_resp.status_code == 200:
                        agents = agents_resp.json().get("remote_agents", [])
                        for agent in agents:
                            if agent["agent_name"] == self.agent_name:
                                self.agent_id = agent["agent_id"]
                                return True
                logger.error("bridge_registration_failed", error=error)
                return False

        except Exception as e:
            logger.error("bridge_registration_error", error=str(e))
            return False

    async def heartbeat(self) -> bool:
        """Send heartbeat to OpenHub"""
        try:
            if self.node_id:
                resp = await self.client.post(
                    f"/v1/acn/nodes/{self.node_id}/heartbeat"
                )
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
        """Background task polling loop"""
        while self._running:
            try:
                # Poll for tasks assigned to this agent
                if self.agent_id:
                    resp = await self.client.get(
                        "/v1/tasks/search",
                        params={
                            "assigned_agent_id": self.agent_id,
                            "status": "claimed",
                        }
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        tasks = data.get("tasks", [])
                        for task in tasks:
                            if self._task_handler:
                                try:
                                    await self._task_handler(task)
                                except Exception as e:
                                    logger.error("bridge_task_handler_error",
                                               task_id=task.get("id"), error=str(e))
            except Exception as e:
                logger.warning("bridge_task_poll_error", error=str(e))

            await asyncio.sleep(self.task_poll_interval)

    async def submit_task_result(
        self,
        task_id: str,
        status: str = "completed",
        result_summary: Optional[str] = None,
        output: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ) -> bool:
        """Submit task result to OpenHub"""
        try:
            resp = await self.client.post(
                f"/v1/acn/tasks/{task_id}/result",
                json={
                    "task_id": task_id,
                    "status": status,
                    "result_summary": result_summary,
                    "output": output,
                    "error_message": error_message,
                }
            )
            if resp.status_code == 200:
                logger.info("bridge_task_result_submitted", task_id=task_id)
                return True
            return False
        except Exception as e:
            logger.error("bridge_task_submit_error", error=str(e))
            return False

    async def run(self):
        """Main run loop - register, heartbeat, poll tasks"""
        logger.info("bridge_starting",
                   hub_url=self.hub_url, agent_name=self.agent_name)

        # Register
        success = await self.register()
        if not success:
            logger.error("bridge_registration_failed_exiting")
            return

        self._running = True

        # Handle graceful shutdown
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, lambda: self.stop())
            except NotImplementedError:
                pass

        logger.info("bridge_running",
                   agent_id=self.agent_id, agent_name=self.agent_name)

        # Run heartbeat and task poll concurrently
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
        """Stop the bridge"""
        logger.info("bridge_stopping", agent_name=self.agent_name)
        self._running = False


async def run_bridge(
    hub_url: str,
    agent_name: str,
    capabilities: List[str],
    node_name: str = "default-node",
    **kwargs,
):
    """Convenience function to run a bridge"""
    bridge = AgentBridge(
        hub_url=hub_url,
        agent_name=agent_name,
        capabilities=capabilities,
        node_name=node_name,
        **kwargs,
    )
    await bridge.run()
