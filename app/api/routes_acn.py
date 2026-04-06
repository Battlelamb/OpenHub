"""
ACN (Agent Collaboration Network) endpoints
"""
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request

from ..config import get_settings
from ..logging import get_logger
from ..database.connection import get_database
from ..services.remote_agent_service import RemoteAgentService
from ..models.acn import ACNNode, ACNNodeCreate, RemoteAgentRegister
from ..models.agents import Agent

logger = get_logger(__name__)
settings = get_settings()

router = APIRouter(prefix="/v1/acn", tags=["acn"])


def get_remote_agent_service() -> RemoteAgentService:
    """Get remote agent service instance"""
    database = get_database()
    return RemoteAgentService(database)


@router.post("/nodes", response_model=ACNNode)
async def register_node(
    node_data: ACNNodeCreate,
    request: Request,
    service: RemoteAgentService = Depends(get_remote_agent_service)
) -> ACNNode:
    """
    Register a new ACN node
    """
    logger.info("acn_node_registration_request",
               node_name=node_data.node_name,
               node_url=node_data.node_url,
               client_ip=request.client.host if request.client else None)

    try:
        new_node = service.register_node(node_data)

        logger.info("acn_node_registration_successful",
                   node_id=new_node.id,
                   node_name=new_node.node_name)

        return new_node

    except ValueError as e:
        logger.warning("acn_node_registration_failed",
                      node_name=node_data.node_name,
                      reason=str(e))
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )

    except Exception as e:
        logger.error("acn_node_registration_error",
                    node_name=node_data.node_name,
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Node registration failed"
        )


@router.get("/nodes", response_model=List[ACNNode])
async def list_nodes(
    service: RemoteAgentService = Depends(get_remote_agent_service)
) -> List[ACNNode]:
    """
    List all ACN nodes
    """
    nodes = service.get_all_nodes()

    logger.debug("acn_nodes_listed", count=len(nodes))

    return nodes


@router.post("/nodes/{node_id}/heartbeat")
async def node_heartbeat(
    node_id: str,
    service: RemoteAgentService = Depends(get_remote_agent_service)
) -> Dict[str, str]:
    """
    Send heartbeat for an ACN node
    """
    # Verify node exists
    node = service.get_node(node_id)
    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node '{node_id}' not found"
        )

    success = service.heartbeat_node(node_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Heartbeat update failed"
        )

    return {"status": "heartbeat_received", "node_id": node_id}


@router.post("/agents/register", response_model=Agent)
async def register_remote_agent(
    agent_data: RemoteAgentRegister,
    request: Request,
    service: RemoteAgentService = Depends(get_remote_agent_service)
) -> Agent:
    """
    Register a remote agent through ACN
    """
    logger.info("remote_agent_registration_request",
               agent_name=agent_data.agent_name,
               node_name=agent_data.node_name,
               capabilities=agent_data.capabilities,
               client_ip=request.client.host if request.client else None)

    try:
        new_agent = service.register_remote_agent(agent_data)

        logger.info("remote_agent_registration_successful",
                   agent_id=new_agent.id,
                   agent_name=new_agent.agent_name)

        return new_agent

    except ValueError as e:
        logger.warning("remote_agent_registration_failed",
                      agent_name=agent_data.agent_name,
                      reason=str(e))
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )

    except Exception as e:
        logger.error("remote_agent_registration_error",
                    agent_name=agent_data.agent_name,
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Remote agent registration failed"
        )


@router.get("/agents")
async def list_remote_agents(
    service: RemoteAgentService = Depends(get_remote_agent_service)
) -> Dict[str, Any]:
    """
    List all remote agents
    """
    remote_agents = service.get_remote_agents()

    logger.debug("remote_agents_listed", count=len(remote_agents))

    return {
        "remote_agents": remote_agents,
        "total": len(remote_agents)
    }


@router.get("/health")
async def acn_health(
    service: RemoteAgentService = Depends(get_remote_agent_service)
) -> Dict[str, Any]:
    """
    Get ACN network health summary
    """
    health = service.get_network_health()

    logger.debug("acn_health_requested",
                total_nodes=health["total_nodes"],
                online_nodes=health["online_nodes"])

    return health
