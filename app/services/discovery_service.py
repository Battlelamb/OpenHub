"""
Agent discovery and monitoring service - clean and simple
"""
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

from ..logging import get_logger
from ..config import get_settings
from ..database.connection import Database
from ..database.repositories.agents import AgentRepository
from ..models.agents import Agent, AgentStatus

logger = get_logger(__name__)
settings = get_settings()


@dataclass
class AgentDiscoveryInfo:
    """Clean discovery information for an agent"""
    agent_id: str
    agent_name: str
    status: str
    capabilities: List[str]
    last_seen: datetime
    response_time_ms: Optional[float] = None
    load_score: Optional[float] = None


@dataclass
class DiscoveryFilter:
    """Simple discovery filter options"""
    status: Optional[List[str]] = None
    capabilities: Optional[List[str]] = None
    exclude_agents: Optional[List[str]] = None
    max_results: Optional[int] = None


class DiscoveryService:
    """Simple agent discovery and monitoring"""
    
    def __init__(self, database: Database):
        self.db = database
        self.agent_repo = AgentRepository(database)
    
    def discover_agents(self, filters: Optional[DiscoveryFilter] = None) -> List[AgentDiscoveryInfo]:
        """
        Discover available agents with optional filtering
        
        Args:
            filters: Optional discovery filters
            
        Returns:
            List of discovered agents
        """
        
        logger.debug("agent_discovery_started", filters=filters)
        
        try:
            # Start with all agents
            agents = self.agent_repo.list_all()
            
            if not agents:
                logger.info("no_agents_available_for_discovery")
                return []
            
            # Apply filters
            filtered_agents = self._apply_filters(agents, filters)
            
            # Convert to discovery info
            discovery_results = []
            for agent in filtered_agents:
                discovery_info = self._create_discovery_info(agent)
                if discovery_info:
                    discovery_results.append(discovery_info)
            
            # Sort by relevance (status priority + last seen)
            discovery_results = self._sort_by_relevance(discovery_results)
            
            # Apply max results limit
            if filters and filters.max_results:
                discovery_results = discovery_results[:filters.max_results]
            
            logger.info("agent_discovery_completed", 
                       total_found=len(discovery_results),
                       filters_applied=filters is not None)
            
            return discovery_results
        
        except Exception as e:
            logger.error("agent_discovery_failed", error=str(e))
            return []
    
    def discover_by_capability(self, capability: str, max_results: int = 10) -> List[AgentDiscoveryInfo]:
        """Discover agents by specific capability"""
        
        filters = DiscoveryFilter(
            capabilities=[capability],
            max_results=max_results
        )
        
        return self.discover_agents(filters)
    
    def discover_available_agents(self, exclude_busy: bool = True) -> List[AgentDiscoveryInfo]:
        """Discover available agents for work"""
        
        status_filter = [AgentStatus.ONLINE.value, AgentStatus.IDLE.value]
        if not exclude_busy:
            status_filter.append(AgentStatus.BUSY.value)
        
        filters = DiscoveryFilter(status=status_filter)
        
        return self.discover_agents(filters)
    
    def get_agent_neighborhood(self, agent_id: str, radius: int = 5) -> List[AgentDiscoveryInfo]:
        """
        Get agents in the 'neighborhood' of a specific agent
        (agents with similar capabilities)
        """
        
        try:
            # Get the reference agent
            reference_agent = self.agent_repo.get_by_id(agent_id)
            if not reference_agent:
                logger.warning("reference_agent_not_found", agent_id=agent_id)
                return []
            
            # Get reference agent capabilities
            ref_capabilities = self._parse_agent_capabilities(reference_agent)
            if not ref_capabilities:
                logger.info("reference_agent_no_capabilities", agent_id=agent_id)
                return []
            
            # Find agents with similar capabilities
            filters = DiscoveryFilter(
                capabilities=ref_capabilities,
                exclude_agents=[agent_id],  # Exclude the reference agent itself
                max_results=radius
            )
            
            neighbors = self.discover_agents(filters)
            
            logger.debug("agent_neighborhood_found", 
                        reference_agent=agent_id,
                        neighbors_count=len(neighbors))
            
            return neighbors
        
        except Exception as e:
            logger.error("agent_neighborhood_failed", 
                        agent_id=agent_id,
                        error=str(e))
            return []
    
    def _apply_filters(self, agents: List[Agent], filters: Optional[DiscoveryFilter]) -> List[Agent]:
        """Apply discovery filters to agent list"""
        
        if not filters:
            return agents
        
        filtered = agents
        
        # Status filter
        if filters.status:
            filtered = [agent for agent in filtered if agent.status.value in filters.status]
        
        # Capabilities filter
        if filters.capabilities:
            filtered = [agent for agent in filtered if self._has_any_capability(agent, filters.capabilities)]
        
        # Exclude agents filter
        if filters.exclude_agents:
            filtered = [agent for agent in filtered if agent.id not in filters.exclude_agents]
        
        return filtered
    
    def _has_any_capability(self, agent: Agent, required_capabilities: List[str]) -> bool:
        """Check if agent has any of the required capabilities"""
        
        agent_caps = self._parse_agent_capabilities(agent)
        agent_caps_lower = [cap.lower() for cap in agent_caps]
        required_lower = [cap.lower() for cap in required_capabilities]
        
        return any(req_cap in agent_caps_lower for req_cap in required_lower)
    
    def _parse_agent_capabilities(self, agent: Agent) -> List[str]:
        """Parse agent capabilities into list of strings"""
        
        import json
        
        agent_caps = agent.capabilities
        if isinstance(agent_caps, str):
            try:
                agent_caps = json.loads(agent_caps)
            except:
                return [agent_caps]  # Single capability as string
        
        if not agent_caps:
            return []
        
        # Extract capability names
        cap_names = []
        for cap in agent_caps:
            if isinstance(cap, str):
                cap_names.append(cap)
            elif isinstance(cap, dict) and "name" in cap:
                cap_names.append(cap["name"])
        
        return cap_names
    
    def _create_discovery_info(self, agent: Agent) -> Optional[AgentDiscoveryInfo]:
        """Create discovery info from agent"""
        
        try:
            capabilities = self._parse_agent_capabilities(agent)
            
            return AgentDiscoveryInfo(
                agent_id=agent.id,
                agent_name=agent.agent_name,
                status=agent.status.value,
                capabilities=capabilities,
                last_seen=agent.last_heartbeat or agent.updated_at,
                response_time_ms=None,  # Could be calculated from recent interactions
                load_score=self._calculate_load_score(agent)
            )
        
        except Exception as e:
            logger.error("discovery_info_creation_failed", 
                        agent_id=agent.id,
                        error=str(e))
            return None
    
    def _calculate_load_score(self, agent: Agent) -> float:
        """Calculate agent load score (0.0 = available, 1.0 = overloaded)"""
        
        # Simple load calculation based on status
        if agent.status == AgentStatus.IDLE:
            return 0.0
        elif agent.status == AgentStatus.ONLINE:
            return 0.3  # Available but might have some background tasks
        elif agent.status == AgentStatus.BUSY:
            return 0.8  # High load
        elif agent.status == AgentStatus.OFFLINE:
            return 1.0  # Not available
        else:
            return 0.5  # Unknown status
    
    def _sort_by_relevance(self, discovery_results: List[AgentDiscoveryInfo]) -> List[AgentDiscoveryInfo]:
        """Sort agents by relevance (status priority + freshness)"""
        
        def relevance_score(info: AgentDiscoveryInfo) -> float:
            # Status priority
            status_scores = {
                AgentStatus.IDLE.value: 1.0,
                AgentStatus.ONLINE.value: 0.8,
                AgentStatus.BUSY.value: 0.3,
                AgentStatus.OFFLINE.value: 0.1
            }
            status_score = status_scores.get(info.status, 0.5)
            
            # Freshness score (recent activity is better)
            now = datetime.utcnow()
            time_diff = (now - info.last_seen).total_seconds()
            freshness_score = max(0.1, 1.0 - (time_diff / 3600))  # Decay over 1 hour
            
            # Load score (lower load is better)
            load_factor = 1.0 - (info.load_score or 0.5)
            
            # Combined relevance score
            return (status_score * 0.5) + (freshness_score * 0.3) + (load_factor * 0.2)
        
        return sorted(discovery_results, key=relevance_score, reverse=True)


class AgentMonitoringService:
    """Monitor agent health and performance"""
    
    def __init__(self, database: Database):
        self.db = database
        self.agent_repo = AgentRepository(database)
    
    def get_agent_health_status(self, agent_id: str) -> Dict[str, Any]:
        """Get comprehensive health status for an agent"""
        
        try:
            agent = self.agent_repo.get_by_id(agent_id)
            if not agent:
                return {"error": f"Agent {agent_id} not found"}
            
            now = datetime.utcnow()
            last_seen = agent.last_heartbeat or agent.updated_at
            offline_duration = (now - last_seen).total_seconds()
            
            # Health assessment
            is_healthy = (
                agent.status in [AgentStatus.ONLINE, AgentStatus.IDLE, AgentStatus.BUSY] and
                offline_duration < settings.heartbeat_timeout_sec
            )
            
            health_score = self._calculate_health_score(agent, offline_duration)
            
            return {
                "agent_id": agent_id,
                "agent_name": agent.agent_name,
                "status": agent.status.value,
                "is_healthy": is_healthy,
                "health_score": health_score,
                "last_seen": last_seen.isoformat(),
                "offline_duration_sec": offline_duration,
                "capabilities_count": len(self._parse_agent_capabilities(agent)),
                "registered_at": agent.created_at.isoformat()
            }
        
        except Exception as e:
            logger.error("agent_health_check_failed", 
                        agent_id=agent_id,
                        error=str(e))
            return {"error": str(e)}
    
    def get_system_health_summary(self) -> Dict[str, Any]:
        """Get overall system health summary"""
        
        try:
            agents = self.agent_repo.list_all()
            now = datetime.utcnow()
            
            health_data = {
                "total_agents": len(agents),
                "healthy_agents": 0,
                "unhealthy_agents": 0,
                "offline_agents": 0,
                "avg_health_score": 0.0,
                "status_distribution": {},
                "last_updated": now.isoformat()
            }
            
            if not agents:
                return health_data
            
            total_health = 0.0
            status_counts = {}
            
            for agent in agents:
                status = agent.status.value
                status_counts[status] = status_counts.get(status, 0) + 1
                
                last_seen = agent.last_heartbeat or agent.updated_at
                offline_duration = (now - last_seen).total_seconds()
                
                if agent.status == AgentStatus.OFFLINE:
                    health_data["offline_agents"] += 1
                elif offline_duration > settings.heartbeat_timeout_sec:
                    health_data["unhealthy_agents"] += 1
                else:
                    health_data["healthy_agents"] += 1
                
                health_score = self._calculate_health_score(agent, offline_duration)
                total_health += health_score
            
            health_data["avg_health_score"] = round(total_health / len(agents), 2)
            health_data["status_distribution"] = status_counts
            
            return health_data
        
        except Exception as e:
            logger.error("system_health_summary_failed", error=str(e))
            return {"error": str(e)}
    
    def _parse_agent_capabilities(self, agent: Agent) -> List[str]:
        """Parse agent capabilities (shared utility)"""
        
        import json
        
        agent_caps = agent.capabilities
        if isinstance(agent_caps, str):
            try:
                agent_caps = json.loads(agent_caps)
            except:
                return [agent_caps]
        
        if not agent_caps:
            return []
        
        cap_names = []
        for cap in agent_caps:
            if isinstance(cap, str):
                cap_names.append(cap)
            elif isinstance(cap, dict) and "name" in cap:
                cap_names.append(cap["name"])
        
        return cap_names
    
    def _calculate_health_score(self, agent: Agent, offline_duration: float) -> float:
        """Calculate health score (0.0 = critical, 1.0 = perfect)"""
        
        # Base score from status
        status_scores = {
            AgentStatus.IDLE: 1.0,
            AgentStatus.ONLINE: 0.9,
            AgentStatus.BUSY: 0.7,
            AgentStatus.OFFLINE: 0.0
        }
        base_score = status_scores.get(agent.status, 0.5)
        
        # Penalize for being offline too long
        if offline_duration > settings.heartbeat_timeout_sec:
            freshness_penalty = min(0.8, offline_duration / 3600)  # Penalty increases over time
            base_score = max(0.0, base_score - freshness_penalty)
        
        return round(base_score, 2)