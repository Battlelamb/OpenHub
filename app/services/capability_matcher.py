"""
Agent capability matching service - simple and smart
"""
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import json

from ..logging import get_logger
from ..database.connection import Database
from ..database.repositories.agents import AgentRepository
from ..models.agents import Agent, AgentStatus

logger = get_logger(__name__)


@dataclass
class CapabilityMatch:
    """Clean capability match result"""
    agent: Agent
    match_score: float
    matched_capabilities: List[str]
    missing_capabilities: List[str]
    confidence_score: float


class CapabilityMatcher:
    """Simple and clean capability matching"""
    
    def __init__(self, database: Database):
        self.db = database
        self.agent_repo = AgentRepository(database)
    
    def find_best_agent(
        self, 
        required_capabilities: List[str],
        min_score: float = 0.5
    ) -> Optional[CapabilityMatch]:
        """
        Find the best agent for given capabilities
        
        Args:
            required_capabilities: List of required capability names
            min_score: Minimum match score (0.0 to 1.0)
            
        Returns:
            Best matching agent or None
        """
        
        logger.debug("capability_matching_started", 
                    required_capabilities=required_capabilities,
                    min_score=min_score)
        
        # Get all available agents (online + idle)
        available_agents = self._get_available_agents()
        
        if not available_agents:
            logger.info("no_available_agents_for_matching")
            return None
        
        # Score each agent
        matches = []
        for agent in available_agents:
            match = self._score_agent(agent, required_capabilities)
            if match and match.match_score >= min_score:
                matches.append(match)
        
        if not matches:
            logger.info("no_agents_meet_minimum_score", 
                       min_score=min_score,
                       checked_agents=len(available_agents))
            return None
        
        # Sort by score (highest first)
        matches.sort(key=lambda m: m.match_score, reverse=True)
        best_match = matches[0]
        
        logger.info("best_agent_found", 
                   agent_id=best_match.agent.id,
                   agent_name=best_match.agent.agent_name,
                   match_score=best_match.match_score,
                   matched_capabilities=best_match.matched_capabilities)
        
        return best_match
    
    def find_all_matching_agents(
        self,
        required_capabilities: List[str],
        min_score: float = 0.3
    ) -> List[CapabilityMatch]:
        """Find all agents that match capabilities (sorted by score)"""
        
        available_agents = self._get_available_agents()
        matches = []
        
        for agent in available_agents:
            match = self._score_agent(agent, required_capabilities)
            if match and match.match_score >= min_score:
                matches.append(match)
        
        # Sort by score (highest first)
        matches.sort(key=lambda m: m.match_score, reverse=True)
        
        logger.debug("all_matching_agents_found", 
                    required_capabilities=required_capabilities,
                    found_count=len(matches))
        
        return matches
    
    def _get_available_agents(self) -> List[Agent]:
        """Get agents available for work"""
        
        # Get agents that are online or idle
        online_agents = self.agent_repo.find_by_status(AgentStatus.ONLINE)
        idle_agents = self.agent_repo.find_by_status(AgentStatus.IDLE)
        
        available = online_agents + idle_agents
        
        logger.debug("available_agents_retrieved", count=len(available))
        return available
    
    def _score_agent(
        self, 
        agent: Agent, 
        required_capabilities: List[str]
    ) -> Optional[CapabilityMatch]:
        """Score an agent against required capabilities"""
        
        if not required_capabilities:
            return None
        
        # Parse agent capabilities
        agent_caps = agent.capabilities
        if isinstance(agent_caps, str):
            try:
                agent_caps = json.loads(agent_caps)
            except:
                agent_caps = [agent_caps]  # Single capability as string
        
        if not agent_caps:
            return None
        
        # Simple capability names (could be enhanced with confidence later)
        agent_cap_names = []
        for cap in agent_caps:
            if isinstance(cap, str):
                agent_cap_names.append(cap.lower())
            elif isinstance(cap, dict) and "name" in cap:
                agent_cap_names.append(cap["name"].lower())
        
        # Calculate match
        required_lower = [cap.lower() for cap in required_capabilities]
        matched = []
        missing = []
        
        for req_cap in required_lower:
            if req_cap in agent_cap_names:
                matched.append(req_cap)
            else:
                missing.append(req_cap)
        
        if not matched:
            return None  # No capabilities match
        
        # Calculate scores
        match_score = len(matched) / len(required_lower)
        confidence_score = self._calculate_confidence_score(agent_caps, matched)
        
        return CapabilityMatch(
            agent=agent,
            match_score=match_score,
            matched_capabilities=matched,
            missing_capabilities=missing,
            confidence_score=confidence_score
        )
    
    def _calculate_confidence_score(
        self, 
        agent_caps: List, 
        matched_caps: List[str]
    ) -> float:
        """Calculate confidence score based on agent's capability confidence"""
        
        if not matched_caps:
            return 0.0
        
        total_confidence = 0.0
        count = 0
        
        for cap in agent_caps:
            if isinstance(cap, dict) and "name" in cap:
                if cap["name"].lower() in matched_caps:
                    confidence = cap.get("confidence", 1.0)
                    total_confidence += confidence
                    count += 1
            elif isinstance(cap, str) and cap.lower() in matched_caps:
                total_confidence += 1.0  # Default confidence
                count += 1
        
        return total_confidence / count if count > 0 else 1.0
    
    def get_capability_stats(self) -> Dict[str, any]:
        """Get capability distribution statistics"""
        
        try:
            agents = self.agent_repo.list_all()
            
            capability_counts = {}
            total_agents = len(agents)
            
            for agent in agents:
                agent_caps = agent.capabilities
                if isinstance(agent_caps, str):
                    try:
                        agent_caps = json.loads(agent_caps)
                    except:
                        agent_caps = [agent_caps]
                
                for cap in agent_caps:
                    cap_name = cap
                    if isinstance(cap, dict):
                        cap_name = cap.get("name", "unknown")
                    
                    cap_name = cap_name.lower()
                    capability_counts[cap_name] = capability_counts.get(cap_name, 0) + 1
            
            # Sort by frequency
            sorted_caps = sorted(
                capability_counts.items(), 
                key=lambda x: x[1], 
                reverse=True
            )
            
            return {
                "total_agents": total_agents,
                "unique_capabilities": len(capability_counts),
                "capability_distribution": dict(sorted_caps),
                "most_common": sorted_caps[:5] if sorted_caps else []
            }
        
        except Exception as e:
            logger.error("capability_stats_failed", error=str(e))
            return {"error": str(e)}