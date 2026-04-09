"""
ACN node repository for database operations
"""
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from ...logging import get_logger
from ...models.acn import ACNNode, ACNNodeStatus
from .base import BaseRepository

logger = get_logger(__name__)


class ACNNodeRepository(BaseRepository[ACNNode]):
    """ACN node database operations"""

    def __init__(self, database):
        super().__init__(database, "acn_nodes")

    def _row_to_model(self, row: Dict[str, Any]) -> ACNNode:
        """Convert database row to ACNNode model"""

        capabilities = json.loads(row.get("capabilities", "[]"))
        labels = json.loads(row.get("labels", "{}"))
        metadata = json.loads(row.get("metadata", "{}"))

        return ACNNode(
            id=row["id"],
            node_name=row["node_name"],
            node_url=row["node_url"],
            status=ACNNodeStatus(row["status"]),
            capabilities=capabilities,
            labels=labels,
            metadata=metadata,
            last_heartbeat=row.get("last_heartbeat"),
            created_at=row["created_at"],
            updated_at=row.get("updated_at"),
        )

    def _model_to_dict(self, node: ACNNode) -> Dict[str, Any]:
        """Convert ACNNode model to database dict"""

        return {
            "id": node.id,
            "node_name": node.node_name,
            "node_url": node.node_url,
            "status": node.status.value if isinstance(node.status, ACNNodeStatus) else node.status,
            "capabilities": json.dumps(node.capabilities),
            "labels": json.dumps(node.labels),
            "metadata": json.dumps(node.metadata),
            "last_heartbeat": node.last_heartbeat,
            "created_at": node.created_at,
            "updated_at": node.updated_at,
        }

    def find_by_name(self, node_name: str) -> Optional[ACNNode]:
        """Find node by name"""
        return self.find_one_by({"node_name": node_name})

    def find_online_nodes(self) -> List[ACNNode]:
        """Find all online nodes"""
        return self.find_by({"status": ACNNodeStatus.ONLINE.value})

    def update_heartbeat(self, node_id: str) -> bool:
        """Update node's last heartbeat and set status to online"""

        try:
            updated = self.update(node_id, {
                "last_heartbeat": datetime.now(timezone.utc),
                "status": ACNNodeStatus.ONLINE.value
            })

            if updated:
                logger.debug("acn_node_heartbeat_updated", node_id=node_id)
                return True

            logger.warning("acn_node_heartbeat_update_failed", node_id=node_id)
            return False

        except Exception as e:
            logger.error("acn_node_heartbeat_update_error",
                        node_id=node_id,
                        error=str(e))
            return False
