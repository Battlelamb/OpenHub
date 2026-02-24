"""
Agent repository for database operations
"""
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

from ...logging import get_logger
from ...models.agents import Agent, AgentStatus
from .base import BaseRepository

logger = get_logger(__name__)


class AgentRepository(BaseRepository[Agent]):
    """Simple and clean agent database operations"""
    
    def __init__(self, database):
        super().__init__(database, "agents")
    
    def _row_to_model(self, row: Dict[str, Any]) -> Agent:
        """Convert database row to Agent model"""
        
        # Parse JSON fields
        capabilities = json.loads(row.get("capabilities", "[]"))
        labels = json.loads(row.get("labels", "{}"))
        metadata = json.loads(row.get("metadata", "{}"))
        
        return Agent(
            id=row["id"],
            agent_name=row["agent_name"],
            description=row.get("description"),
            capabilities=capabilities,
            status=AgentStatus(row["status"]),
            labels=labels,
            metadata=metadata,
            created_at=row["created_at"],
            updated_at=row.get("updated_at"),
            last_heartbeat=row.get("last_heartbeat"),
            tasks_completed=row.get("tasks_completed", 0),
            tasks_failed=row.get("tasks_failed", 0),
            average_task_duration=row.get("average_task_duration"),
            current_task=row.get("current_task")
        )
    
    def _model_to_dict(self, agent: Agent) -> Dict[str, Any]:
        """Convert Agent model to database dict"""
        
        return {
            "id": agent.id,
            "agent_name": agent.agent_name,
            "description": agent.description,
            "capabilities": json.dumps(agent.capabilities),
            "status": agent.status.value,
            "labels": json.dumps(agent.labels),
            "metadata": json.dumps(agent.metadata),
            "created_at": agent.created_at,
            "updated_at": agent.updated_at,
            "last_heartbeat": agent.last_heartbeat,
            "tasks_completed": agent.tasks_completed,
            "tasks_failed": agent.tasks_failed,
            "average_task_duration": agent.average_task_duration,
            "current_task": agent.current_task
        }
    
    def find_by_name(self, agent_name: str) -> Optional[Agent]:
        """Find agent by name"""
        return self.find_one_by({"agent_name": agent_name})
    
    def find_by_status(self, status: AgentStatus) -> List[Agent]:
        """Find agents by status"""
        return self.find_by({"status": status.value})
    
    def find_online_agents(self) -> List[Agent]:
        """Find all online agents"""
        return self.find_by_status(AgentStatus.ONLINE)
    
    def update_heartbeat(self, agent_id: str) -> bool:
        """Update agent's last heartbeat"""
        
        try:
            updated = self.update(agent_id, {
                "last_heartbeat": datetime.utcnow(),
                "status": AgentStatus.ONLINE.value
            })
            
            if updated:
                logger.debug("agent_heartbeat_updated", agent_id=agent_id)
                return True
            
            logger.warning("agent_heartbeat_update_failed", agent_id=agent_id)
            return False
        
        except Exception as e:
            logger.error("agent_heartbeat_update_error", 
                        agent_id=agent_id,
                        error=str(e))
            return False
    
    def set_agent_status(self, agent_id: str, status: AgentStatus) -> bool:
        """Set agent status"""
        
        try:
            updated = self.update(agent_id, {"status": status.value})
            
            if updated:
                logger.info("agent_status_changed", 
                           agent_id=agent_id,
                           new_status=status.value)
                return True
            
            return False
        
        except Exception as e:
            logger.error("agent_status_update_error",
                        agent_id=agent_id,
                        status=status.value,
                        error=str(e))
            return False