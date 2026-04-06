"""
Remote agent mappings repository for database operations
"""
import json
from typing import Dict, Any, List, Optional

from ...logging import get_logger
from ...models.acn import RemoteAgentMapping
from .base import BaseRepository

logger = get_logger(__name__)


class RemoteAgentMappingRepository(BaseRepository[RemoteAgentMapping]):
    """Remote agent mapping database operations"""

    def __init__(self, database):
        super().__init__(database, "remote_agent_mappings")

    def _row_to_model(self, row: Dict[str, Any]) -> RemoteAgentMapping:
        """Convert database row to RemoteAgentMapping model"""

        connection_metadata = json.loads(row.get("connection_metadata", "{}"))

        return RemoteAgentMapping(
            id=row["id"],
            local_agent_id=row["local_agent_id"],
            node_id=row["node_id"],
            remote_agent_name=row["remote_agent_name"],
            callback_url=row.get("callback_url"),
            connection_metadata=connection_metadata,
            created_at=row["created_at"],
            updated_at=row.get("updated_at"),
        )

    def _model_to_dict(self, mapping: RemoteAgentMapping) -> Dict[str, Any]:
        """Convert RemoteAgentMapping model to database dict"""

        return {
            "id": mapping.id,
            "local_agent_id": mapping.local_agent_id,
            "node_id": mapping.node_id,
            "remote_agent_name": mapping.remote_agent_name,
            "callback_url": mapping.callback_url,
            "connection_metadata": json.dumps(mapping.connection_metadata),
            "created_at": mapping.created_at,
            "updated_at": mapping.updated_at,
        }

    def find_by_agent_id(self, local_agent_id: str) -> Optional[RemoteAgentMapping]:
        """Find mapping by local agent ID"""
        return self.find_one_by({"local_agent_id": local_agent_id})

    def find_by_node_id(self, node_id: str) -> List[RemoteAgentMapping]:
        """Find all mappings for a node"""
        return self.find_by({"node_id": node_id})

    def is_remote_agent(self, agent_id: str) -> bool:
        """Check if an agent is a remote agent"""
        mapping = self.find_by_agent_id(agent_id)
        return mapping is not None
