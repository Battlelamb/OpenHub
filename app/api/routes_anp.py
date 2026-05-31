"""Experimental public ANP compatibility routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.database.connection import get_database
from app.database.repositories.agents import AgentRepository
from app.services.anp_compatibility_service import (
    build_agent_description,
    build_discovery_page,
    is_anp_public,
)

router = APIRouter(tags=["anp [experimental]"])


def get_agent_repository() -> AgentRepository:
    """Create the repository dependency used by ANP discovery routes."""

    return AgentRepository(get_database())


@router.get("/v1/anp/agents/{agent_id}/ad.json")
def get_agent_description(
    agent_id: str,
    request: Request,
    repository: AgentRepository = Depends(get_agent_repository),
):
    """Return a public-safe ANP Agent Description for one opted-in agent."""

    agent = repository.get_by_id(agent_id)
    if not agent or not is_anp_public(agent):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Public ANP agent description not found",
        )

    return build_agent_description(agent, str(request.base_url))


@router.get("/.well-known/agent-descriptions", include_in_schema=False)
def get_agent_descriptions(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    repository: AgentRepository = Depends(get_agent_repository),
):
    """Return the public ANP discovery collection for opted-in agents."""

    agents = repository.list_all()
    return build_discovery_page(
        agents,
        str(request.base_url),
        page=page,
        page_size=page_size,
    )
