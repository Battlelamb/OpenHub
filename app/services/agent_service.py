"""
Agent business logic service - clean and simple
"""
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from ..logging import get_logger
from ..database.connection import Database
from ..database.repositories.agents import AgentRepository
from ..models.agents import Agent, AgentCreate, AgentStatus

logger = get_logger(__name__)


class AgentService:
    """Clean agent business logic"""
    
    def __init__(self, database: Database):
        self.db = database
        self.agent_repo = AgentRepository(database)
    
    def register_agent(self, agent_data: AgentCreate) -> Agent:
        """Register a new agent"""
        
        logger.info("agent_registration_started", agent_name=agent_data.agent_name)
        
        # Check if agent name already exists
        existing_agent = self.agent_repo.find_by_name(agent_data.agent_name)
        if existing_agent:
            logger.warning("agent_registration_duplicate", 
                          agent_name=agent_data.agent_name)
            raise ValueError(f"Agent name '{agent_data.agent_name}' already exists")
        
        # Create new agent
        new_agent = Agent(
            id=str(uuid4()),
            agent_name=agent_data.agent_name,
            description=agent_data.description,
            capabilities=agent_data.capabilities,
            status=AgentStatus.ONLINE,
            labels=agent_data.labels,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            last_heartbeat=datetime.utcnow(),
            tasks_completed=0,
            tasks_failed=0
        )
        
        # Save to database
        created_agent = self.agent_repo.create(new_agent)
        
        logger.info("agent_registered_successfully", 
                   agent_id=created_agent.id,
                   agent_name=created_agent.agent_name)
        
        return created_agent
    
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID"""
        return self.agent_repo.get_by_id(agent_id)
    
    def get_agent_by_name(self, agent_name: str) -> Optional[Agent]:
        """Get agent by name"""
        return self.agent_repo.find_by_name(agent_name)
    
    def update_heartbeat(self, agent_id: str) -> bool:
        """Update agent heartbeat"""
        
        logger.debug("agent_heartbeat_received", agent_id=agent_id)
        return self.agent_repo.update_heartbeat(agent_id)
    
    def set_agent_offline(self, agent_id: str) -> bool:
        """Set agent to offline status"""
        
        logger.info("agent_going_offline", agent_id=agent_id)
        return self.agent_repo.set_agent_status(agent_id, AgentStatus.OFFLINE)
    
    def get_online_agents(self) -> List[Agent]:
        """Get all online agents"""
        return self.agent_repo.find_online_agents()
    
    def get_agents_by_capability(self, capability: str) -> List[Agent]:
        """Find agents that have specific capability"""
        
        # Get all online agents
        online_agents = self.get_online_agents()
        
        # Filter by capability
        matching_agents = []
        for agent in online_agents:
            if capability in agent.capabilities:
                matching_agents.append(agent)
        
        logger.debug("agents_found_by_capability", 
                    capability=capability,
                    count=len(matching_agents))
        
        return matching_agents