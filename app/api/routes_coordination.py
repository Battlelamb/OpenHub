"""
Agent-Workflow Coordination endpoints - clean integration layer
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from ..config import get_settings
from ..logging import get_logger
from ..database.connection import get_database
from ..services.workflow_coordinator import WorkflowCoordinator, WorkflowPriority, WorkflowExecutionPlan
from ..services.hatchet_service import AgentWorkflowStep, AgentWorkflowTemplates
from ..auth.dependencies import CurrentAgent, CurrentAdmin

logger = get_logger(__name__)
settings = get_settings()

router = APIRouter(prefix="/v1/coordination", tags=["coordination"])


def get_workflow_coordinator() -> WorkflowCoordinator:
    """Get workflow coordinator instance"""
    database = get_database()
    return WorkflowCoordinator(database)


# Pydantic models for coordination API
class SmartWorkflowRequest(BaseModel):
    """Request for smart workflow creation with auto-agent assignment"""
    workflow_name: str = Field(..., min_length=1, max_length=200, description="Workflow name")
    workflow_type: str = Field(..., description="Type: custom, code_review, data_processing, research")
    priority: WorkflowPriority = Field(WorkflowPriority.NORMAL, description="Execution priority")
    
    # For custom workflows
    custom_steps: Optional[List[Dict[str, Any]]] = Field(None, description="Custom step definitions")
    
    # For template workflows
    template_params: Optional[Dict[str, Any]] = Field(None, description="Template parameters")
    
    input_data: Optional[Dict[str, Any]] = Field(None, description="Initial workflow data")
    description: Optional[str] = Field(None, max_length=1000, description="Workflow description")
    
    # Smart assignment options
    auto_assign_agents: bool = Field(True, description="Automatically assign best available agents")
    preferred_agents: Optional[List[str]] = Field(None, description="Preferred agent IDs")
    exclude_agents: Optional[List[str]] = Field(None, description="Agent IDs to exclude")


class ExecutionPlanResponse(BaseModel):
    """Response model for execution plan"""
    workflow_name: str
    total_steps: int
    estimated_duration_minutes: int
    required_agents: List[str]
    capability_requirements: Dict[str, List[str]]
    step_dependencies: Dict[str, List[str]]
    resource_requirements: Dict[str, Any]
    feasible: bool
    issues: Optional[List[str]] = None


class CoordinationStatusResponse(BaseModel):
    """Response model for coordination status"""
    workflow_run_id: str
    workflow_status: Dict[str, Any]
    coordination_details: Dict[str, Any]


@router.post("/plan-workflow", response_model=ExecutionPlanResponse)
async def plan_smart_workflow(
    request: SmartWorkflowRequest,
    current_agent: CurrentAgent = None,
    coordinator: WorkflowCoordinator = Depends(get_workflow_coordinator)
) -> ExecutionPlanResponse:
    """
    Create execution plan for smart workflow with auto-agent assignment
    """
    logger.info("smart_workflow_planning_request",
               workflow_name=request.workflow_name,
               workflow_type=request.workflow_type,
               by_agent=current_agent.agent_id if current_agent else "system")
    
    try:
        # Generate steps based on workflow type
        steps = []
        issues = []
        
        if request.workflow_type == "custom":
            if not request.custom_steps:
                raise ValueError("Custom workflow requires custom_steps")
            
            # Convert custom steps to AgentWorkflowStep objects
            for i, step_data in enumerate(request.custom_steps):
                step = AgentWorkflowStep(
                    step_id=f"custom_step_{i+1}",
                    step_name=step_data.get("step_name", f"Step {i+1}"),
                    agent_id=step_data.get("agent_id", "auto"),  # "auto" means find suitable agent
                    task_type=step_data.get("task_type", "general"),
                    input_data=step_data.get("input_data", {}),
                    depends_on=step_data.get("depends_on", []),
                    timeout_seconds=step_data.get("timeout_seconds", 300),
                    retry_count=step_data.get("retry_count", 2)
                )
                steps.append(step)
        
        elif request.workflow_type == "code_review":
            if not request.template_params:
                raise ValueError("Code review workflow requires template_params")
            
            params = request.template_params
            
            # Auto-assign agents if not specified
            if request.auto_assign_agents:
                agents = await coordinator._find_agents_for_template("code_review", params, request.preferred_agents, request.exclude_agents)
                params.update(agents)
            
            steps = AgentWorkflowTemplates.create_code_review_workflow(
                code_agent_id=params.get("code_agent_id", "auto"),
                review_agent_id=params.get("review_agent_id", "auto"),
                test_agent_id=params.get("test_agent_id", "auto"),
                code_input=params.get("code_input", {})
            )
        
        elif request.workflow_type == "data_processing":
            if not request.template_params:
                raise ValueError("Data processing workflow requires template_params")
            
            params = request.template_params
            
            if request.auto_assign_agents:
                agents = await coordinator._find_agents_for_template("data_processing", params, request.preferred_agents, request.exclude_agents)
                params.update(agents)
            
            steps = AgentWorkflowTemplates.create_data_processing_workflow(
                extract_agent_id=params.get("extract_agent_id", "auto"),
                transform_agent_id=params.get("transform_agent_id", "auto"),
                load_agent_id=params.get("load_agent_id", "auto"),
                data_source=params.get("data_source", {})
            )
        
        elif request.workflow_type == "research":
            if not request.template_params:
                raise ValueError("Research workflow requires template_params")
            
            params = request.template_params
            
            if request.auto_assign_agents:
                agents = await coordinator._find_agents_for_template("research", params, request.preferred_agents, request.exclude_agents)
                params.update(agents)
            
            steps = AgentWorkflowTemplates.create_research_workflow(
                research_agent_id=params.get("research_agent_id", "auto"),
                analysis_agent_id=params.get("analysis_agent_id", "auto"),
                report_agent_id=params.get("report_agent_id", "auto"),
                research_topic=params.get("research_topic", "")
            )
        
        else:
            raise ValueError(f"Unknown workflow type: {request.workflow_type}")
        
        # Create execution plan
        execution_plan = await coordinator.plan_workflow_execution(
            workflow_name=request.workflow_name,
            steps=steps,
            priority=request.priority
        )
        
        # Check feasibility
        feasible = True
        if not execution_plan.required_agents:
            feasible = False
            issues.append("No suitable agents found for workflow steps")
        
        # Convert to response format
        return ExecutionPlanResponse(
            workflow_name=execution_plan.workflow_name,
            total_steps=execution_plan.total_steps,
            estimated_duration_minutes=execution_plan.estimated_duration_minutes,
            required_agents=execution_plan.required_agents,
            capability_requirements=execution_plan.capability_requirements,
            step_dependencies=execution_plan.step_dependencies,
            resource_requirements=execution_plan.resource_requirements,
            feasible=feasible,
            issues=issues if issues else None
        )
    
    except ValueError as e:
        logger.warning("smart_workflow_planning_validation_failed",
                      workflow_name=request.workflow_name,
                      error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    except Exception as e:
        logger.error("smart_workflow_planning_failed",
                    workflow_name=request.workflow_name,
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Workflow planning failed"
        )


@router.post("/execute-smart-workflow", response_model=Dict[str, str])
async def execute_smart_workflow(
    request: SmartWorkflowRequest,
    current_agent: CurrentAgent = None,
    coordinator: WorkflowCoordinator = Depends(get_workflow_coordinator)
) -> Dict[str, str]:
    """
    Plan and execute smart workflow with coordinated agent management
    """
    logger.info("smart_workflow_execution_request",
               workflow_name=request.workflow_name,
               workflow_type=request.workflow_type,
               by_agent=current_agent.agent_id if current_agent else "system")
    
    try:
        # First, create execution plan (reuse logic from plan endpoint)
        plan_request = SmartWorkflowRequest(**request.dict())
        execution_plan_response = await plan_smart_workflow(plan_request, current_agent, coordinator)
        
        if not execution_plan_response.feasible:
            raise ValueError(f"Workflow not feasible: {'; '.join(execution_plan_response.issues or [])}")
        
        # Convert execution plan back to workflow steps
        steps = await coordinator._rebuild_steps_from_plan(execution_plan_response, request)
        
        # Convert response back to execution plan object
        execution_plan = WorkflowExecutionPlan(
            workflow_name=execution_plan_response.workflow_name,
            total_steps=execution_plan_response.total_steps,
            estimated_duration_minutes=execution_plan_response.estimated_duration_minutes,
            required_agents=execution_plan_response.required_agents,
            capability_requirements=execution_plan_response.capability_requirements,
            step_dependencies=execution_plan_response.step_dependencies,
            resource_requirements=execution_plan_response.resource_requirements
        )
        
        # Coordinate and execute workflow
        workflow_run_id = await coordinator.coordinate_workflow_execution(
            execution_plan=execution_plan,
            steps=steps,
            input_data=request.input_data,
            created_by=current_agent.agent_id if current_agent else None
        )
        
        return {
            "status": "coordinated_and_started",
            "workflow_run_id": workflow_run_id,
            "message": f"Smart workflow '{request.workflow_name}' coordinated with {len(execution_plan.required_agents)} agents",
            "estimated_duration": f"{execution_plan.estimated_duration_minutes} minutes"
        }
    
    except ValueError as e:
        logger.warning("smart_workflow_execution_validation_failed",
                      workflow_name=request.workflow_name,
                      error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    except Exception as e:
        logger.error("smart_workflow_execution_failed",
                    workflow_name=request.workflow_name,
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Smart workflow execution failed"
        )


@router.get("/{workflow_run_id}/status", response_model=CoordinationStatusResponse)
async def get_coordination_status(
    workflow_run_id: str,
    current_agent: CurrentAgent = None,
    coordinator: WorkflowCoordinator = Depends(get_workflow_coordinator)
) -> CoordinationStatusResponse:
    """
    Get detailed coordination status including agent assignments
    """
    coordination_status = await coordinator.get_coordination_status(workflow_run_id)
    
    if "error" in coordination_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=coordination_status["error"]
        )
    
    return CoordinationStatusResponse(
        workflow_run_id=workflow_run_id,
        workflow_status=coordination_status["workflow_status"],
        coordination_details=coordination_status["coordination_details"]
    )


@router.post("/{workflow_run_id}/release-agents")
async def release_agents_from_workflow(
    workflow_run_id: str,
    reason: Optional[str] = Query(None, description="Reason for releasing agents"),
    current_agent: CurrentAgent = None,
    coordinator: WorkflowCoordinator = Depends(get_workflow_coordinator)
) -> Dict[str, str]:
    """
    Manually release agents from workflow (emergency use)
    """
    logger.info("manual_agent_release_request",
               workflow_run_id=workflow_run_id,
               by_agent=current_agent.agent_id if current_agent else "system",
               reason=reason)
    
    try:
        await coordinator._release_agents_from_workflow(workflow_run_id)
        
        return {
            "status": "agents_released",
            "workflow_run_id": workflow_run_id,
            "message": "Agents released from workflow"
        }
    
    except Exception as e:
        logger.error("manual_agent_release_failed",
                    workflow_run_id=workflow_run_id,
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to release agents"
        )


@router.get("/stats/coordination", response_model=Dict[str, Any])
async def get_coordination_statistics(
    current_agent: CurrentAgent = None,
    coordinator: WorkflowCoordinator = Depends(get_workflow_coordinator)
) -> Dict[str, Any]:
    """
    Get workflow coordination statistics
    """
    try:
        stats = coordinator.get_coordination_statistics()
        
        logger.debug("coordination_statistics_requested",
                    by_agent=current_agent.agent_id if current_agent else "system")
        
        return stats
    
    except Exception as e:
        logger.error("coordination_statistics_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve coordination statistics"
        )


@router.get("/active-coordinations", response_model=List[Dict[str, Any]])
async def get_active_coordinations(
    agent_id_filter: Optional[str] = Query(None, description="Filter by agent ID"),
    status_filter: Optional[str] = Query(None, description="Filter by coordination status"),
    current_agent: CurrentAgent = None,
    coordinator: WorkflowCoordinator = Depends(get_workflow_coordinator)
) -> List[Dict[str, Any]]:
    """
    Get list of active agent-workflow coordinations
    """
    try:
        active_coordinations = []
        
        for coord_id, coordination in coordinator._active_coordinations.items():
            # Apply filters
            if agent_id_filter and coordination.agent_id != agent_id_filter:
                continue
            
            if status_filter and coordination.status != status_filter:
                continue
            
            active_coordinations.append({
                "coordination_id": coord_id,
                "workflow_run_id": coordination.workflow_run_id,
                "agent_id": coordination.agent_id,
                "step_id": coordination.step_id,
                "status": coordination.status,
                "assigned_at": coordination.assigned_at.isoformat(),
                "started_at": coordination.started_at.isoformat() if coordination.started_at else None,
                "completed_at": coordination.completed_at.isoformat() if coordination.completed_at else None,
                "has_result": coordination.result is not None,
                "has_error": coordination.error is not None
            })
        
        logger.debug("active_coordinations_requested",
                    by_agent=current_agent.agent_id if current_agent else "system",
                    returned_count=len(active_coordinations))
        
        return active_coordinations
    
    except Exception as e:
        logger.error("active_coordinations_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve active coordinations"
        )


# Admin endpoints
@router.get("/admin/all-coordinations", response_model=Dict[str, Any])
async def get_all_coordinations(
    limit: int = Query(100, ge=1, le=500, description="Maximum coordinations to return"),
    current_admin: CurrentAdmin = None,
    coordinator: WorkflowCoordinator = Depends(get_workflow_coordinator)
) -> Dict[str, Any]:
    """
    Get all coordinations (admin only)
    """
    try:
        all_coordinations = []
        
        for coord_id, coordination in list(coordinator._active_coordinations.items())[:limit]:
            all_coordinations.append({
                "coordination_id": coord_id,
                "workflow_run_id": coordination.workflow_run_id,
                "agent_id": coordination.agent_id,
                "step_id": coordination.step_id,
                "status": coordination.status,
                "assigned_at": coordination.assigned_at.isoformat(),
                "started_at": coordination.started_at.isoformat() if coordination.started_at else None,
                "completed_at": coordination.completed_at.isoformat() if coordination.completed_at else None,
                "result": coordination.result,
                "error": coordination.error
            })
        
        workflow_assignments = {
            wf_id: agents for wf_id, agents in coordinator._workflow_agent_assignments.items()
        }
        
        logger.info("all_coordinations_requested",
                   admin_id=current_admin.agent_id,
                   returned_count=len(all_coordinations))
        
        return {
            "coordinations": all_coordinations,
            "workflow_assignments": workflow_assignments,
            "total_active_workflows": len(workflow_assignments),
            "total_coordinations": len(all_coordinations)
        }
    
    except Exception as e:
        logger.error("get_all_coordinations_failed",
                    admin_id=current_admin.agent_id,
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve all coordinations"
        )


@router.delete("/admin/{workflow_run_id}/force-cleanup")
async def force_cleanup_workflow_coordination(
    workflow_run_id: str,
    current_admin: CurrentAdmin,
    coordinator: WorkflowCoordinator = Depends(get_workflow_coordinator)
) -> Dict[str, str]:
    """
    Force cleanup of workflow coordination (admin only)
    """
    logger.info("force_coordination_cleanup_request",
               workflow_run_id=workflow_run_id,
               admin_id=current_admin.agent_id)
    
    try:
        # Force release agents and cleanup coordination
        await coordinator._release_agents_from_workflow(workflow_run_id)
        
        logger.info("force_coordination_cleanup_completed",
                   workflow_run_id=workflow_run_id,
                   admin_id=current_admin.agent_id)
        
        return {
            "status": "force_cleanup_completed",
            "workflow_run_id": workflow_run_id,
            "message": "Workflow coordination forcefully cleaned up"
        }
    
    except Exception as e:
        logger.error("force_coordination_cleanup_failed",
                    workflow_run_id=workflow_run_id,
                    admin_id=current_admin.agent_id,
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Force cleanup failed"
        )