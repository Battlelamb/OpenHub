"""
Clean and simple agent management endpoints
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request

from ..config import get_settings
from ..logging import get_logger
from ..database.connection import get_database
from ..services.agent_service import AgentService
from ..services.heartbeat_service import HeartbeatService, AgentStatusManager
from ..services.capability_matcher import CapabilityMatcher, CapabilityMatch
from ..services.discovery_service import DiscoveryService, AgentMonitoringService, DiscoveryFilter
from ..models.agents import Agent, AgentCreate, AgentStatus
from ..auth.dependencies import CurrentAgent, CurrentAdmin

logger = get_logger(__name__)
settings = get_settings()

router = APIRouter(prefix="/v1/agents", tags=["agents"])


def get_agent_service() -> AgentService:
    """Get agent service instance"""
    database = get_database()
    return AgentService(database)


def get_status_manager() -> AgentStatusManager:
    """Get agent status manager instance"""
    database = get_database()
    return AgentStatusManager(database)


def get_heartbeat_service() -> HeartbeatService:
    """Get heartbeat service instance"""
    database = get_database()
    return HeartbeatService(database)


def get_capability_matcher() -> CapabilityMatcher:
    """Get capability matcher instance"""
    database = get_database()
    return CapabilityMatcher(database)


def get_discovery_service() -> DiscoveryService:
    """Get discovery service instance"""
    database = get_database()
    return DiscoveryService(database)


def get_monitoring_service() -> AgentMonitoringService:
    """Get monitoring service instance"""
    database = get_database()
    return AgentMonitoringService(database)


@router.post("/register", response_model=Agent)
async def register_agent(
    agent_data: AgentCreate,
    request: Request,
    agent_service: AgentService = Depends(get_agent_service)
) -> Agent:
    """
    Register a new agent - simple and clean
    """
    logger.info("agent_registration_request", 
               agent_name=agent_data.agent_name,
               capabilities=agent_data.capabilities,
               client_ip=request.client.host if request.client else None)
    
    try:
        # Register the agent
        new_agent = agent_service.register_agent(agent_data)
        
        logger.info("agent_registration_successful", 
                   agent_id=new_agent.id,
                   agent_name=new_agent.agent_name)
        
        return new_agent
    
    except ValueError as e:
        # Agent name already exists
        logger.warning("agent_registration_failed", 
                      agent_name=agent_data.agent_name,
                      reason=str(e))
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    
    except Exception as e:
        logger.error("agent_registration_error", 
                    agent_name=agent_data.agent_name,
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Agent registration failed"
        )


@router.get("/me", response_model=Agent)
async def get_my_info(
    current_agent: CurrentAgent,
    agent_service: AgentService = Depends(get_agent_service)
) -> Agent:
    """
    Get current agent's information
    """
    agent = agent_service.get_agent(current_agent.agent_id)
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    return agent


@router.post("/heartbeat")
async def send_heartbeat(
    current_agent: CurrentAgent,
    agent_service: AgentService = Depends(get_agent_service)
) -> Dict[str, str]:
    """
    Send heartbeat to keep agent alive
    """
    success = agent_service.update_heartbeat(current_agent.agent_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Heartbeat update failed"
        )
    
    return {"status": "heartbeat_received"}


@router.post("/offline")
async def go_offline(
    current_agent: CurrentAgent,
    agent_service: AgentService = Depends(get_agent_service)
) -> Dict[str, str]:
    """
    Set agent to offline status
    """
    success = agent_service.set_agent_offline(current_agent.agent_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Status update failed"
        )
    
    logger.info("agent_went_offline", agent_id=current_agent.agent_id)
    return {"status": "offline"}


@router.get("/online", response_model=List[Agent])
async def get_online_agents(
    current_agent: CurrentAgent,
    agent_service: AgentService = Depends(get_agent_service)
) -> List[Agent]:
    """
    Get list of all online agents
    """
    online_agents = agent_service.get_online_agents()
    
    logger.debug("online_agents_requested", 
                by_agent=current_agent.agent_id,
                count=len(online_agents))
    
    return online_agents


@router.get("/capability/{capability}", response_model=List[Agent])
async def find_agents_by_capability(
    capability: str,
    current_agent: CurrentAgent,
    agent_service: AgentService = Depends(get_agent_service)
) -> List[Agent]:
    """
    Find agents that have specific capability
    """
    matching_agents = agent_service.get_agents_by_capability(capability)
    
    logger.debug("agents_searched_by_capability", 
                capability=capability,
                by_agent=current_agent.agent_id,
                found_count=len(matching_agents))
    
    return matching_agents


# Admin-only endpoints
@router.get("/{agent_id}", response_model=Agent)
async def get_agent(
    agent_id: str,
    current_admin: CurrentAdmin,
    agent_service: AgentService = Depends(get_agent_service)
) -> Agent:
    """
    Get specific agent by ID (admin only)
    """
    agent = agent_service.get_agent(agent_id)
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found"
        )
    
    return agent


@router.post("/status/{status}")
async def update_agent_status(
    status: str,
    current_agent: CurrentAgent,
    status_manager: AgentStatusManager = Depends(get_status_manager)
) -> Dict[str, str]:
    """
    Update agent status (idle, busy, etc.)
    """
    try:
        # Parse status
        agent_status = AgentStatus(status)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status '{status}'. Valid: {[s.value for s in AgentStatus]}"
        )
    
    success = await status_manager.update_agent_status(
        agent_id=current_agent.agent_id,
        new_status=agent_status,
        reason="manual_update"
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Status update failed"
        )
    
    return {"status": status, "message": "Status updated successfully"}


@router.get("/stats/heartbeat")
async def get_heartbeat_stats(
    current_agent: CurrentAgent,
    heartbeat_service: HeartbeatService = Depends(get_heartbeat_service)
) -> Dict[str, Any]:
    """
    Get heartbeat monitoring statistics
    """
    stats = heartbeat_service.get_heartbeat_stats()
    
    logger.debug("heartbeat_stats_requested", 
                by_agent=current_agent.agent_id)
    
    return stats


# Admin-only status endpoints
@router.get("/admin/status-summary")
async def get_status_summary(
    current_admin: CurrentAdmin,
    status_manager: AgentStatusManager = Depends(get_status_manager)
) -> Dict[str, Any]:
    """
    Get agent status summary (admin only)
    """
    summary = status_manager.get_agent_status_summary()
    
    logger.info("status_summary_requested", admin_id=current_admin.agent_id)
    
    return summary


@router.post("/admin/{agent_id}/status/{status}")
async def admin_update_agent_status(
    agent_id: str,
    status: str,
    current_admin: CurrentAdmin,
    status_manager: AgentStatusManager = Depends(get_status_manager)
) -> Dict[str, str]:
    """
    Update any agent's status (admin only)
    """
    try:
        agent_status = AgentStatus(status)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status '{status}'"
        )
    
    success = await status_manager.update_agent_status(
        agent_id=agent_id,
        new_status=agent_status,
        reason=f"admin_update_by_{current_admin.agent_id}"
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Status update failed"
        )
    
    logger.info("admin_status_update", 
               admin_id=current_admin.agent_id,
               target_agent_id=agent_id,
               new_status=status)
    
    return {"status": status, "message": "Status updated by admin"}


@router.post("/match-capabilities")
async def find_best_agent_for_capabilities(
    required_capabilities: List[str],
    min_score: Optional[float] = 0.5,
    current_agent: CurrentAgent = None,
    matcher: CapabilityMatcher = Depends(get_capability_matcher)
) -> Dict[str, Any]:
    """
    Find best agent for given capabilities (simple and clean)
    """
    if not required_capabilities:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Required capabilities cannot be empty"
        )
    
    logger.info("capability_matching_requested", 
               required_capabilities=required_capabilities,
               by_agent=current_agent.agent_id if current_agent else "anonymous",
               min_score=min_score)
    
    best_match = matcher.find_best_agent(required_capabilities, min_score)
    
    if not best_match:
        return {
            "found": False,
            "message": "No agents found matching requirements",
            "required_capabilities": required_capabilities,
            "min_score": min_score
        }
    
    return {
        "found": True,
        "agent": {
            "id": best_match.agent.id,
            "name": best_match.agent.agent_name,
            "status": best_match.agent.status.value,
            "capabilities": best_match.agent.capabilities
        },
        "match_details": {
            "match_score": round(best_match.match_score, 3),
            "confidence_score": round(best_match.confidence_score, 3),
            "matched_capabilities": best_match.matched_capabilities,
            "missing_capabilities": best_match.missing_capabilities
        },
        "required_capabilities": required_capabilities
    }


@router.post("/match-all")
async def find_all_matching_agents(
    required_capabilities: List[str],
    min_score: Optional[float] = 0.3,
    current_agent: CurrentAgent = None,
    matcher: CapabilityMatcher = Depends(get_capability_matcher)
) -> Dict[str, Any]:
    """
    Find all agents matching capabilities (sorted by score)
    """
    if not required_capabilities:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Required capabilities cannot be empty"
        )
    
    matches = matcher.find_all_matching_agents(required_capabilities, min_score)
    
    matching_agents = []
    for match in matches:
        matching_agents.append({
            "agent": {
                "id": match.agent.id,
                "name": match.agent.agent_name,
                "status": match.agent.status.value
            },
            "match_score": round(match.match_score, 3),
            "confidence_score": round(match.confidence_score, 3),
            "matched_capabilities": match.matched_capabilities,
            "missing_capabilities": match.missing_capabilities
        })
    
    return {
        "found_count": len(matching_agents),
        "agents": matching_agents,
        "required_capabilities": required_capabilities,
        "min_score": min_score
    }


@router.get("/stats/capabilities")
async def get_capability_statistics(
    current_agent: CurrentAgent,
    matcher: CapabilityMatcher = Depends(get_capability_matcher)
) -> Dict[str, Any]:
    """
    Get capability distribution statistics
    """
    stats = matcher.get_capability_stats()
    
    logger.debug("capability_stats_requested", 
                by_agent=current_agent.agent_id)
    
    return stats


# Discovery endpoints
@router.post("/discover")
async def discover_agents(
    status: Optional[List[str]] = None,
    capabilities: Optional[List[str]] = None,
    exclude_agents: Optional[List[str]] = None,
    max_results: Optional[int] = 20,
    current_agent: CurrentAgent = None,
    discovery: DiscoveryService = Depends(get_discovery_service)
) -> Dict[str, Any]:
    """
    Discover available agents with filtering options
    """
    filters = DiscoveryFilter(
        status=status,
        capabilities=capabilities,
        exclude_agents=exclude_agents,
        max_results=max_results
    )
    
    logger.info("agent_discovery_requested", 
               by_agent=current_agent.agent_id if current_agent else "anonymous",
               filters=filters)
    
    discovered_agents = discovery.discover_agents(filters)
    
    return {
        "found_count": len(discovered_agents),
        "agents": [
            {
                "agent_id": agent.agent_id,
                "agent_name": agent.agent_name,
                "status": agent.status,
                "capabilities": agent.capabilities,
                "last_seen": agent.last_seen.isoformat(),
                "load_score": agent.load_score
            }
            for agent in discovered_agents
        ],
        "filters": {
            "status": status,
            "capabilities": capabilities,
            "max_results": max_results
        }
    }


@router.get("/discover/available")
async def discover_available_agents(
    exclude_busy: bool = True,
    current_agent: CurrentAgent = None,
    discovery: DiscoveryService = Depends(get_discovery_service)
) -> Dict[str, Any]:
    """
    Discover agents available for work
    """
    available_agents = discovery.discover_available_agents(exclude_busy)
    
    logger.debug("available_agents_requested", 
                by_agent=current_agent.agent_id if current_agent else "anonymous",
                exclude_busy=exclude_busy)
    
    return {
        "available_count": len(available_agents),
        "agents": [
            {
                "agent_id": agent.agent_id,
                "agent_name": agent.agent_name,
                "status": agent.status,
                "capabilities": agent.capabilities,
                "load_score": agent.load_score
            }
            for agent in available_agents
        ]
    }


@router.get("/discover/by-capability/{capability}")
async def discover_by_capability(
    capability: str,
    max_results: int = 10,
    current_agent: CurrentAgent = None,
    discovery: DiscoveryService = Depends(get_discovery_service)
) -> Dict[str, Any]:
    """
    Discover agents by specific capability
    """
    agents_with_capability = discovery.discover_by_capability(capability, max_results)
    
    logger.debug("capability_discovery_requested", 
                capability=capability,
                by_agent=current_agent.agent_id if current_agent else "anonymous")
    
    return {
        "capability": capability,
        "found_count": len(agents_with_capability),
        "agents": [
            {
                "agent_id": agent.agent_id,
                "agent_name": agent.agent_name,
                "status": agent.status,
                "capabilities": agent.capabilities,
                "load_score": agent.load_score
            }
            for agent in agents_with_capability
        ]
    }


@router.get("/discover/neighborhood/{agent_id}")
async def get_agent_neighborhood(
    agent_id: str,
    radius: int = 5,
    current_agent: CurrentAgent = None,
    discovery: DiscoveryService = Depends(get_discovery_service)
) -> Dict[str, Any]:
    """
    Get agents in the neighborhood of a specific agent
    (agents with similar capabilities)
    """
    neighbors = discovery.get_agent_neighborhood(agent_id, radius)
    
    logger.debug("agent_neighborhood_requested", 
                target_agent=agent_id,
                by_agent=current_agent.agent_id if current_agent else "anonymous",
                radius=radius)
    
    return {
        "reference_agent": agent_id,
        "radius": radius,
        "neighbors_count": len(neighbors),
        "neighbors": [
            {
                "agent_id": neighbor.agent_id,
                "agent_name": neighbor.agent_name,
                "status": neighbor.status,
                "capabilities": neighbor.capabilities,
                "load_score": neighbor.load_score
            }
            for neighbor in neighbors
        ]
    }


# Monitoring endpoints  
@router.get("/monitor/health/{agent_id}")
async def get_agent_health(
    agent_id: str,
    current_agent: CurrentAgent = None,
    monitoring: AgentMonitoringService = Depends(get_monitoring_service)
) -> Dict[str, Any]:
    """
    Get comprehensive health status for an agent
    """
    health_status = monitoring.get_agent_health_status(agent_id)
    
    logger.debug("agent_health_requested", 
                target_agent=agent_id,
                by_agent=current_agent.agent_id if current_agent else "anonymous")
    
    return health_status


@router.get("/monitor/system-health")
async def get_system_health(
    current_agent: CurrentAgent = None,
    monitoring: AgentMonitoringService = Depends(get_monitoring_service)
) -> Dict[str, Any]:
    """
    Get overall system health summary
    """
    system_health = monitoring.get_system_health_summary()
    
    logger.debug("system_health_requested", 
                by_agent=current_agent.agent_id if current_agent else "anonymous")
    
    return system_health