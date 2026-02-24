"""
Workflow orchestration endpoints with Hatchet integration - clean and simple
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from ..config import get_settings
from ..logging import get_logger
from ..database.connection import get_database
from ..services.hatchet_service import HatchetService, AgentWorkflowStep, AgentWorkflowTemplates
from ..auth.dependencies import CurrentAgent, CurrentAdmin

logger = get_logger(__name__)
settings = get_settings()

router = APIRouter(prefix="/v1/workflows", tags=["workflows"])


def get_hatchet_service() -> HatchetService:
    """Get Hatchet service instance"""
    database = get_database()
    return HatchetService(database)


# Pydantic models for API
class WorkflowStepCreate(BaseModel):
    """Model for creating workflow step"""
    step_name: str = Field(..., min_length=1, max_length=200, description="Step name")
    agent_id: str = Field(..., description="Agent ID to execute this step")
    task_type: str = Field(..., description="Type of task for this step")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="Step input data")
    depends_on: Optional[List[str]] = Field(default=None, description="Previous step IDs this depends on")
    timeout_seconds: int = Field(default=300, ge=10, le=3600, description="Step timeout in seconds")
    retry_count: int = Field(default=2, ge=0, le=5, description="Number of retries")


class WorkflowCreate(BaseModel):
    """Model for creating workflow"""
    workflow_name: str = Field(..., min_length=1, max_length=200, description="Workflow name")
    steps: List[WorkflowStepCreate] = Field(..., min_items=1, description="Workflow steps")
    input_data: Optional[Dict[str, Any]] = Field(default=None, description="Initial workflow data")
    description: Optional[str] = Field(default=None, max_length=1000, description="Workflow description")


class WorkflowTemplateRequest(BaseModel):
    """Model for creating workflow from template"""
    template_name: str = Field(..., description="Template name (code_review, data_processing, research)")
    template_params: Dict[str, Any] = Field(..., description="Template parameters")
    workflow_name: Optional[str] = Field(default=None, description="Custom workflow name")


class WorkflowResponse(BaseModel):
    """Workflow response model"""
    run_id: str = Field(..., description="Workflow run ID")
    name: str = Field(..., description="Workflow name")
    status: str = Field(..., description="Workflow status")
    created_at: str = Field(..., description="Creation timestamp")
    created_by: Optional[str] = Field(default=None, description="Creator")
    progress: Dict[str, Any] = Field(..., description="Progress information")
    input_data: Dict[str, Any] = Field(..., description="Input data")


@router.post("/", response_model=Dict[str, str])
async def create_workflow(
    workflow_data: WorkflowCreate,
    current_agent: CurrentAgent = None,
    hatchet_service: HatchetService = Depends(get_hatchet_service)
) -> Dict[str, str]:
    """
    Create and start a new agent workflow
    """
    logger.info("workflow_creation_request",
               workflow_name=workflow_data.workflow_name,
               steps_count=len(workflow_data.steps),
               by_agent=current_agent.agent_id if current_agent else "system")
    
    try:
        # Convert Pydantic models to workflow steps
        steps = []
        for i, step_data in enumerate(workflow_data.steps):
            step = AgentWorkflowStep(
                step_id=f"step_{i+1}_{step_data.step_name.lower().replace(' ', '_')}",
                step_name=step_data.step_name,
                agent_id=step_data.agent_id,
                task_type=step_data.task_type,
                input_data=step_data.input_data,
                depends_on=step_data.depends_on or [],
                timeout_seconds=step_data.timeout_seconds,
                retry_count=step_data.retry_count
            )
            steps.append(step)
        
        # Create workflow
        workflow_run_id = await hatchet_service.create_agent_workflow(
            workflow_name=workflow_data.workflow_name,
            steps=steps,
            input_data=workflow_data.input_data,
            created_by=current_agent.agent_id if current_agent else None
        )
        
        return {
            "status": "created",
            "workflow_run_id": workflow_run_id,
            "message": f"Workflow '{workflow_data.workflow_name}' created and started"
        }
    
    except ValueError as e:
        logger.warning("workflow_creation_validation_failed",
                      workflow_name=workflow_data.workflow_name,
                      error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    except Exception as e:
        logger.error("workflow_creation_failed",
                    workflow_name=workflow_data.workflow_name,
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Workflow creation failed"
        )


@router.post("/from-template", response_model=Dict[str, str])
async def create_workflow_from_template(
    template_request: WorkflowTemplateRequest,
    current_agent: CurrentAgent = None,
    hatchet_service: HatchetService = Depends(get_hatchet_service)
) -> Dict[str, str]:
    """
    Create workflow from predefined template
    """
    logger.info("workflow_template_creation_request",
               template_name=template_request.template_name,
               by_agent=current_agent.agent_id if current_agent else "system")
    
    try:
        # Get workflow steps from template
        steps = []
        template_name = template_request.template_name.lower()
        params = template_request.template_params
        
        if template_name == "code_review":
            required_params = ["code_agent_id", "review_agent_id", "test_agent_id", "code_input"]
            if not all(param in params for param in required_params):
                raise ValueError(f"Missing required parameters for code_review template: {required_params}")
            
            steps = AgentWorkflowTemplates.create_code_review_workflow(
                code_agent_id=params["code_agent_id"],
                review_agent_id=params["review_agent_id"],
                test_agent_id=params["test_agent_id"],
                code_input=params["code_input"]
            )
            
        elif template_name == "data_processing":
            required_params = ["extract_agent_id", "transform_agent_id", "load_agent_id", "data_source"]
            if not all(param in params for param in required_params):
                raise ValueError(f"Missing required parameters for data_processing template: {required_params}")
            
            steps = AgentWorkflowTemplates.create_data_processing_workflow(
                extract_agent_id=params["extract_agent_id"],
                transform_agent_id=params["transform_agent_id"],
                load_agent_id=params["load_agent_id"],
                data_source=params["data_source"]
            )
            
        elif template_name == "research":
            required_params = ["research_agent_id", "analysis_agent_id", "report_agent_id", "research_topic"]
            if not all(param in params for param in required_params):
                raise ValueError(f"Missing required parameters for research template: {required_params}")
            
            steps = AgentWorkflowTemplates.create_research_workflow(
                research_agent_id=params["research_agent_id"],
                analysis_agent_id=params["analysis_agent_id"],
                report_agent_id=params["report_agent_id"],
                research_topic=params["research_topic"]
            )
            
        else:
            raise ValueError(f"Unknown template: {template_name}. Available: code_review, data_processing, research")
        
        # Generate workflow name
        workflow_name = template_request.workflow_name or f"{template_name.title()} Workflow"
        
        # Create workflow
        workflow_run_id = await hatchet_service.create_agent_workflow(
            workflow_name=workflow_name,
            steps=steps,
            input_data=params,
            created_by=current_agent.agent_id if current_agent else None
        )
        
        return {
            "status": "created",
            "workflow_run_id": workflow_run_id,
            "template_used": template_name,
            "message": f"Workflow created from {template_name} template"
        }
    
    except ValueError as e:
        logger.warning("workflow_template_validation_failed",
                      template_name=template_request.template_name,
                      error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    except Exception as e:
        logger.error("workflow_template_creation_failed",
                    template_name=template_request.template_name,
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Workflow template creation failed"
        )


@router.get("/{workflow_run_id}", response_model=WorkflowResponse)
async def get_workflow_status(
    workflow_run_id: str,
    current_agent: CurrentAgent = None,
    hatchet_service: HatchetService = Depends(get_hatchet_service)
) -> WorkflowResponse:
    """
    Get workflow status and progress
    """
    workflow_status = await hatchet_service.get_workflow_status(workflow_run_id)
    
    if not workflow_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow '{workflow_run_id}' not found"
        )
    
    return WorkflowResponse(**workflow_status)


@router.post("/{workflow_run_id}/cancel")
async def cancel_workflow(
    workflow_run_id: str,
    reason: Optional[str] = Query(None, description="Cancellation reason"),
    current_agent: CurrentAgent = None,
    hatchet_service: HatchetService = Depends(get_hatchet_service)
) -> Dict[str, str]:
    """
    Cancel a running workflow
    """
    logger.info("workflow_cancellation_request",
               workflow_run_id=workflow_run_id,
               by_agent=current_agent.agent_id if current_agent else "system",
               reason=reason)
    
    success = await hatchet_service.cancel_workflow(workflow_run_id, reason)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to cancel workflow - may not exist or already finished"
        )
    
    return {
        "status": "cancelled",
        "workflow_run_id": workflow_run_id,
        "message": "Workflow cancelled successfully"
    }


@router.get("/templates/available", response_model=List[Dict[str, Any]])
async def get_available_templates(
    current_agent: CurrentAgent = None
) -> List[Dict[str, Any]]:
    """
    Get list of available workflow templates
    """
    templates = [
        {
            "name": "code_review",
            "display_name": "Code Review Workflow",
            "description": "Three-step workflow: code analysis → review → testing",
            "required_params": [
                "code_agent_id", "review_agent_id", "test_agent_id", "code_input"
            ],
            "estimated_duration": "15-30 minutes",
            "steps": [
                {"name": "Analyze Code Quality", "agent_role": "code_agent_id"},
                {"name": "Review Code Changes", "agent_role": "review_agent_id"},
                {"name": "Run Automated Tests", "agent_role": "test_agent_id"}
            ]
        },
        {
            "name": "data_processing",
            "display_name": "Data Processing (ETL) Workflow", 
            "description": "Extract → Transform → Load data pipeline",
            "required_params": [
                "extract_agent_id", "transform_agent_id", "load_agent_id", "data_source"
            ],
            "estimated_duration": "30-90 minutes",
            "steps": [
                {"name": "Extract Data from Source", "agent_role": "extract_agent_id"},
                {"name": "Transform and Clean Data", "agent_role": "transform_agent_id"},
                {"name": "Load Data to Destination", "agent_role": "load_agent_id"}
            ]
        },
        {
            "name": "research",
            "display_name": "Research Workflow",
            "description": "Comprehensive research: gather → analyze → report",
            "required_params": [
                "research_agent_id", "analysis_agent_id", "report_agent_id", "research_topic"
            ],
            "estimated_duration": "20-45 minutes", 
            "steps": [
                {"name": "Gather Research Information", "agent_role": "research_agent_id"},
                {"name": "Analyze Research Findings", "agent_role": "analysis_agent_id"},
                {"name": "Generate Final Report", "agent_role": "report_agent_id"}
            ]
        }
    ]
    
    logger.debug("workflow_templates_requested",
                by_agent=current_agent.agent_id if current_agent else "system")
    
    return templates


@router.get("/stats/overview", response_model=Dict[str, Any])
async def get_workflow_statistics(
    current_agent: CurrentAgent = None,
    hatchet_service: HatchetService = Depends(get_hatchet_service)
) -> Dict[str, Any]:
    """
    Get workflow execution statistics
    """
    try:
        stats = hatchet_service.get_workflow_statistics()
        
        logger.debug("workflow_statistics_requested",
                    by_agent=current_agent.agent_id if current_agent else "system")
        
        return stats
    
    except Exception as e:
        logger.error("workflow_statistics_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve workflow statistics"
        )


# Admin endpoints
@router.get("/admin/all", response_model=List[WorkflowResponse])
async def get_all_workflows(
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=200, description="Number of workflows to return"),
    current_admin: CurrentAdmin = None,
    hatchet_service: HatchetService = Depends(get_hatchet_service)
) -> List[WorkflowResponse]:
    """
    Get all workflows (admin only)
    """
    try:
        # In production, would query Hatchet for all workflows
        # For now, return from in-memory storage
        all_workflows = []
        
        for workflow_run_id in list(hatchet_service._running_workflows.keys())[:limit]:
            workflow_status = await hatchet_service.get_workflow_status(workflow_run_id)
            if workflow_status:
                if not status_filter or workflow_status["status"] == status_filter:
                    all_workflows.append(WorkflowResponse(**workflow_status))
        
        logger.debug("all_workflows_requested",
                    admin_id=current_admin.agent_id,
                    status_filter=status_filter,
                    returned_count=len(all_workflows))
        
        return all_workflows
    
    except Exception as e:
        logger.error("get_all_workflows_failed",
                    admin_id=current_admin.agent_id,
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve workflows"
        )


@router.delete("/{workflow_run_id}")
async def delete_workflow(
    workflow_run_id: str,
    current_admin: CurrentAdmin,
    hatchet_service: HatchetService = Depends(get_hatchet_service)
) -> Dict[str, str]:
    """
    Delete workflow history (admin only)
    """
    logger.info("workflow_deletion_request",
               workflow_run_id=workflow_run_id,
               admin_id=current_admin.agent_id)
    
    # Check if workflow exists
    workflow_status = await hatchet_service.get_workflow_status(workflow_run_id)
    if not workflow_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow '{workflow_run_id}' not found"
        )
    
    # Remove from storage (in production, would delete from Hatchet)
    if workflow_run_id in hatchet_service._running_workflows:
        del hatchet_service._running_workflows[workflow_run_id]
    
    logger.info("workflow_deleted_by_admin",
               workflow_run_id=workflow_run_id,
               admin_id=current_admin.agent_id)
    
    return {
        "status": "deleted",
        "workflow_run_id": workflow_run_id,
        "message": "Workflow deleted successfully"
    }