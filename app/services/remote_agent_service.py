"""
Remote agent service - ACN federation business logic
"""
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any


HEARTBEAT_TTL_SECONDS = 300
from uuid import uuid4

from ..logging import get_logger
from ..database.connection import Database
from ..database.repositories.acn_nodes import ACNNodeRepository
from ..database.repositories.remote_agent_mappings import RemoteAgentMappingRepository
from ..database.repositories.agents import AgentRepository
from ..models.acn import (
    ACNNode, ACNNodeCreate, ACNNodeStatus,
    RemoteAgentRegister, RemoteAgentMapping,
)
from ..models.agents import Agent, AgentCreate, AgentStatus

logger = get_logger(__name__)


def _coerce_datetime(value: Any) -> Optional[datetime]:
    """Parse repository datetime values into timezone-aware UTC datetimes."""
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _isoformat(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _heartbeat_status(last_heartbeat: Any, declared_status: Any, now: datetime, ttl_seconds: int = HEARTBEAT_TTL_SECONDS) -> str:
    status_value = declared_status if isinstance(declared_status, str) else getattr(declared_status, "value", declared_status)
    if status_value == "offline":
        return "offline"

    heartbeat = _coerce_datetime(last_heartbeat)
    if not heartbeat:
        return "offline"

    elapsed = (now - heartbeat).total_seconds()
    return "online" if elapsed <= ttl_seconds else "offline"


def _offline_reason(last_heartbeat: Any, declared_status: Any, now: datetime, ttl_seconds: int = HEARTBEAT_TTL_SECONDS) -> Optional[str]:
    if _heartbeat_status(last_heartbeat, declared_status, now, ttl_seconds) == "online":
        return None
    status_value = declared_status if isinstance(declared_status, str) else getattr(declared_status, "value", declared_status)
    if status_value == "offline":
        heartbeat = _coerce_datetime(last_heartbeat)
        if heartbeat and (now - heartbeat).total_seconds() > ttl_seconds:
            return "stale_agent_heartbeat"
        return "agent_marked_offline"
    if not _coerce_datetime(last_heartbeat):
        return "missing_agent_heartbeat"
    return "stale_agent_heartbeat"


class RemoteAgentService:
    """ACN federation business logic"""

    def __init__(self, database: Database):
        self.db = database
        self.node_repo = ACNNodeRepository(database)
        self.mapping_repo = RemoteAgentMappingRepository(database)
        self.agent_repo = AgentRepository(database)

    def register_node(self, data: ACNNodeCreate) -> ACNNode:
        """Register a new ACN node"""

        logger.info("acn_node_registration_started", node_name=data.node_name)

        # Check if node name already exists
        existing = self.node_repo.find_by_name(data.node_name)
        if existing:
            logger.warning("acn_node_registration_duplicate",
                          node_name=data.node_name)
            raise ValueError(f"Node name '{data.node_name}' already exists")

        # Create new node
        new_node = ACNNode(
            id=str(uuid4()),
            node_name=data.node_name,
            node_url=data.node_url,
            status=ACNNodeStatus.ONLINE,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            last_heartbeat=datetime.now(timezone.utc),
        )

        created_node = self.node_repo.create(new_node)

        logger.info("acn_node_registered_successfully",
                   node_id=created_node.id,
                   node_name=created_node.node_name)

        return created_node

    def get_node(self, node_id: str) -> Optional[ACNNode]:
        """Get node by ID"""
        return self.node_repo.get_by_id(node_id)

    def get_all_nodes(self) -> List[ACNNode]:
        """Get all ACN nodes"""
        return self.node_repo.list_all()

    def heartbeat_node(self, node_id: str, agent_id: Optional[str] = None) -> bool:
        """Update the ACN node heartbeat and, when known, the caller agent.

        A node heartbeat proves that the node/bridge is reachable; it does not
        prove that every agent mapped to that node is actively running. When the
        authenticated API key identifies a specific mapped agent, refresh only
        that agent. Never fan out one node heartbeat to every mapped agent.
        """

        logger.debug("acn_node_heartbeat_received", node_id=node_id, agent_id=agent_id)
        success = self.node_repo.update_heartbeat(node_id)
        if not success:
            return False

        if agent_id:
            mapping = self.mapping_repo.find_by_agent_id(agent_id)
            if mapping and mapping.node_id == node_id:
                self.agent_repo.update(agent_id, {
                    "status": "online",
                    "last_heartbeat": datetime.now(timezone.utc),
                })

        return True

    def register_remote_agent(self, data: RemoteAgentRegister, client_ip: Optional[str] = None) -> Agent:
        """Register a remote agent - creates local Agent record + mapping"""

        logger.info("remote_agent_registration_started",
                   agent_name=data.agent_name,
                   node_name=data.node_name)

        # Find the node
        node = self.node_repo.find_by_name(data.node_name)
        if not node:
            raise ValueError(f"ACN node '{data.node_name}' not found. Register the node first.")

        # Check if agent name already exists
        existing_agent = self.agent_repo.find_by_name(data.agent_name)
        if existing_agent:
            raise ValueError(f"Agent name '{data.agent_name}' already exists")

        # Build rich metadata from registration data
        agent_metadata = {
            "is_remote": True,
            "node_name": data.node_name,
            "model": data.model,
            "platform": data.platform,
            "version": data.version,
            "hostname": data.hostname,
            "os_info": data.os_info,
            "workspace_path": data.workspace_path,
            "channels": data.channels or [],
            "skills": data.skills or [],
            "mcp_servers": data.mcp_servers or [],
            "languages": data.languages or [],
            "context_window": data.context_window,
            "callback_url": data.callback_url,
            "ip_address": client_ip,
            "registered_at": datetime.now(timezone.utc).isoformat(),
        }
        # Remove None values
        agent_metadata = {k: v for k, v in agent_metadata.items() if v is not None}

        # Create local Agent record
        new_agent = Agent(
            id=str(uuid4()),
            agent_name=data.agent_name,
            description=data.description,
            capabilities=data.capabilities,
            status=AgentStatus.ONLINE,
            labels={"acn_node": data.node_name, "remote": "true"},
            metadata=agent_metadata,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            last_heartbeat=datetime.now(timezone.utc),
            tasks_completed=0,
            tasks_failed=0,
        )

        created_agent = self.agent_repo.create(new_agent)

        # Create remote agent mapping
        mapping = RemoteAgentMapping(
            id=str(uuid4()),
            local_agent_id=created_agent.id,
            node_id=node.id,
            remote_agent_name=data.agent_name,
            callback_url=data.callback_url,
            connection_metadata={
                "node_name": data.node_name,
                "node_url": node.node_url,
            },
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        self.mapping_repo.create(mapping)

        logger.info("remote_agent_registered_successfully",
                   agent_id=created_agent.id,
                   agent_name=created_agent.agent_name,
                   node_name=data.node_name)

        return created_agent

    def get_remote_agents(self) -> List[Dict[str, Any]]:
        """List remote agents with separate node and agent presence state."""

        mappings = self.mapping_repo.list_all()
        result = []
        now = datetime.now(timezone.utc)

        for mapping in mappings:
            agent = self.agent_repo.get_by_id(mapping.local_agent_id)
            node = self.node_repo.get_by_id(mapping.node_id)

            if agent:
                agent_status = _heartbeat_status(agent.last_heartbeat, agent.status, now)
                node_status = _heartbeat_status(
                    node.last_heartbeat if node else None,
                    node.status if node else "offline",
                    now,
                )

                # Keep the stored status conservative for stale agents, but never
                # let node heartbeat fan out into agent online status.
                if agent_status == "offline":
                    stored_status = agent.status if isinstance(agent.status, str) else agent.status.value
                    if stored_status != "offline":
                        self.agent_repo.update(agent.id, {"status": "offline"})

                metadata = agent.metadata or {}
                mcp_profiles = metadata.get("mcp_profiles") or metadata.get("mcp_servers") or []
                if not isinstance(mcp_profiles, list):
                    mcp_profiles = []

                result.append({
                    "agent_id": agent.id,
                    "agent_name": agent.agent_name,
                    "status": agent_status,  # Backwards-compatible alias for agent_status.
                    "agent_status": agent_status,
                    "capabilities": agent.capabilities,
                    "node_id": mapping.node_id,
                    "node_name": node.node_name if node else "unknown",
                    "node_status": node_status,
                    "callback_url": mapping.callback_url,
                    "last_heartbeat": _isoformat(agent.last_heartbeat),  # Backwards-compatible alias.
                    "last_agent_heartbeat": _isoformat(agent.last_heartbeat),
                    "last_node_heartbeat": _isoformat(node.last_heartbeat) if node else None,
                    "offline_reason": _offline_reason(agent.last_heartbeat, agent.status, now),
                    "mcp_profiles": mcp_profiles,
                })

        return result

    def is_remote(self, agent_id: str) -> bool:
        """Check if an agent is a remote agent"""
        return self.mapping_repo.is_remote_agent(agent_id)

    def get_network_health(self) -> Dict[str, Any]:
        """Get ACN network health summary"""

        all_nodes = self.node_repo.list_all()
        online_nodes = self.node_repo.find_online_nodes()
        all_mappings = self.mapping_repo.list_all()

        return {
            "total_nodes": len(all_nodes),
            "online_nodes": len(online_nodes),
            "offline_nodes": len(all_nodes) - len(online_nodes),
            "total_remote_agents": len(all_mappings),
            "nodes": [
                {
                    "node_id": node.id,
                    "node_name": node.node_name,
                    "node_url": node.node_url,
                    "status": node.status,
                    "last_heartbeat": node.last_heartbeat.isoformat() if node.last_heartbeat else None,
                }
                for node in all_nodes
            ],
        }
