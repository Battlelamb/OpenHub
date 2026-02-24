"""
Hatchet workflow orchestration integration for OpenHub - clean and simple
"""
import uuid
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass

from ..logging import get_logger
from ..config import get_settings
from ..database.connection import Database
from ..database.repositories.tasks import TaskRepository
from ..database.repositories.agents import AgentRepository
from ..models.tasks import Task, TaskStatus

logger = get_logger(__name__)
settings = get_settings()


@dataclass
class HatchetWorkflowResult:
    """Result from Hatchet workflow execution"""
    workflow_id: str
    run_id: str
    status: str  # "completed", "failed", "running"
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_seconds: Optional[float] = None


@dataclass
class AgentWorkflowStep:
    """Single step in an agent workflow"""
    step_id: str
    step_name: str
    agent_id: str
    task_type: str
    input_data: Dict[str, Any]
    depends_on: List[str] = None  # Previous step IDs
    timeout_seconds: int = 300
    retry_count: int = 2


class HatchetService:
    """Clean Hatchet integration for AI agent workflows"""
    
    def __init__(self, database: Database):
        self.db = database
        self.task_repo = TaskRepository(database)
        self.agent_repo = AgentRepository(database)
        
        # Hatchet client (would be initialized in production)
        self._hatchet_client = None
        self._workflows: Dict[str, Callable] = {}
        
        # For now, simulate Hatchet workflows
        self._running_workflows: Dict[str, Dict[str, Any]] = {}
        
        logger.info("hatchet_service_initialized")
    
    async def create_agent_workflow(self, 
                                   workflow_name: str,
                                   steps: List[AgentWorkflowStep],
                                   input_data: Optional[Dict[str, Any]] = None,
                                   created_by: Optional[str] = None) -> str:
        """
        Create a multi-agent workflow with Hatchet orchestration
        
        Args:
            workflow_name: Human-readable workflow name
            steps: List of workflow steps with agent assignments
            input_data: Initial workflow input data
            created_by: User/agent creating the workflow
            
        Returns:
            Workflow run ID for tracking
        """
        
        workflow_run_id = str(uuid.uuid4())
        
        logger.info("agent_workflow_creation_started",
                   workflow_name=workflow_name,
                   workflow_run_id=workflow_run_id,
                   steps_count=len(steps),
                   created_by=created_by)
        
        try:
            # Validate agents exist and have required capabilities
            await self._validate_workflow_agents(steps)
            
            # In production, this would register with Hatchet
            # For now, simulate workflow creation
            workflow_data = {
                "run_id": workflow_run_id,
                "name": workflow_name,
                "status": "running",
                "steps": steps,
                "input_data": input_data or {},
                "created_at": datetime.utcnow(),
                "created_by": created_by,
                "current_step": 0,
                "completed_steps": [],
                "step_results": {}
            }
            
            self._running_workflows[workflow_run_id] = workflow_data
            
            # Start workflow execution
            asyncio.create_task(self._execute_workflow(workflow_run_id))
            
            logger.info("agent_workflow_created_successfully",
                       workflow_name=workflow_name,
                       workflow_run_id=workflow_run_id)
            
            return workflow_run_id
        
        except Exception as e:
            logger.error("agent_workflow_creation_failed",
                        workflow_name=workflow_name,
                        error=str(e))
            raise
    
    async def get_workflow_status(self, workflow_run_id: str) -> Optional[Dict[str, Any]]:
        """Get current workflow status and progress"""
        
        if workflow_run_id not in self._running_workflows:
            logger.warning("workflow_status_not_found", 
                          workflow_run_id=workflow_run_id)
            return None
        
        workflow = self._running_workflows[workflow_run_id]
        
        return {
            "run_id": workflow_run_id,
            "name": workflow["name"],
            "status": workflow["status"],
            "created_at": workflow["created_at"].isoformat(),
            "created_by": workflow.get("created_by"),
            "progress": {
                "current_step": workflow["current_step"],
                "total_steps": len(workflow["steps"]),
                "completed_steps": len(workflow["completed_steps"]),
                "step_results": workflow["step_results"]
            },
            "input_data": workflow["input_data"]
        }
    
    async def cancel_workflow(self, workflow_run_id: str, reason: Optional[str] = None) -> bool:
        """Cancel a running workflow"""
        
        logger.info("workflow_cancellation_requested",
                   workflow_run_id=workflow_run_id,
                   reason=reason)
        
        if workflow_run_id not in self._running_workflows:
            return False
        
        workflow = self._running_workflows[workflow_run_id]
        
        if workflow["status"] in ["completed", "failed", "cancelled"]:
            logger.warning("workflow_already_finished",
                          workflow_run_id=workflow_run_id,
                          current_status=workflow["status"])
            return False
        
        # Update workflow status
        workflow["status"] = "cancelled"
        workflow["cancelled_at"] = datetime.utcnow()
        workflow["cancellation_reason"] = reason
        
        # Cancel any running tasks in this workflow
        # In production, would cancel via Hatchet
        
        logger.info("workflow_cancelled_successfully",
                   workflow_run_id=workflow_run_id)
        
        return True
    
    async def _validate_workflow_agents(self, steps: List[AgentWorkflowStep]) -> None:
        """Validate that all agents exist and can handle their assigned steps"""
        
        agent_ids = {step.agent_id for step in steps}
        
        for agent_id in agent_ids:
            agent = self.agent_repo.get_by_id(agent_id)
            
            if not agent:
                raise ValueError(f"Agent '{agent_id}' not found")
            
            if agent.status.value not in ["online", "idle"]:
                raise ValueError(f"Agent '{agent_id}' not available (status: {agent.status.value})")
        
        logger.debug("workflow_agents_validated", 
                    agent_count=len(agent_ids),
                    agents=list(agent_ids))
    
    async def _execute_workflow(self, workflow_run_id: str) -> None:
        """Execute workflow steps sequentially (simplified implementation)"""
        
        try:
            workflow = self._running_workflows[workflow_run_id]
            steps = workflow["steps"]
            
            logger.info("workflow_execution_started",
                       workflow_run_id=workflow_run_id,
                       steps_count=len(steps))
            
            for i, step in enumerate(steps):
                workflow["current_step"] = i
                
                logger.info("workflow_step_started",
                           workflow_run_id=workflow_run_id,
                           step_id=step.step_id,
                           step_name=step.step_name,
                           agent_id=step.agent_id)
                
                try:
                    # Execute step (create task for agent)
                    step_result = await self._execute_workflow_step(workflow_run_id, step)
                    
                    # Store step result
                    workflow["step_results"][step.step_id] = step_result
                    workflow["completed_steps"].append(step.step_id)
                    
                    logger.info("workflow_step_completed",
                               workflow_run_id=workflow_run_id,
                               step_id=step.step_id,
                               result=step_result)
                
                except Exception as step_error:
                    logger.error("workflow_step_failed",
                                workflow_run_id=workflow_run_id,
                                step_id=step.step_id,
                                error=str(step_error))
                    
                    # Handle step failure
                    workflow["status"] = "failed"
                    workflow["error"] = f"Step '{step.step_name}' failed: {str(step_error)}"
                    workflow["failed_at"] = datetime.utcnow()
                    return
                
                # Check if workflow was cancelled
                if workflow["status"] == "cancelled":
                    logger.info("workflow_execution_cancelled",
                               workflow_run_id=workflow_run_id)
                    return
            
            # All steps completed successfully
            workflow["status"] = "completed"
            workflow["completed_at"] = datetime.utcnow()
            
            logger.info("workflow_execution_completed",
                       workflow_run_id=workflow_run_id,
                       total_steps=len(steps))
        
        except Exception as e:
            logger.error("workflow_execution_error",
                        workflow_run_id=workflow_run_id,
                        error=str(e))
            
            workflow = self._running_workflows.get(workflow_run_id)
            if workflow:
                workflow["status"] = "failed"
                workflow["error"] = str(e)
                workflow["failed_at"] = datetime.utcnow()
    
    async def _execute_workflow_step(self, 
                                    workflow_run_id: str, 
                                    step: AgentWorkflowStep) -> Dict[str, Any]:
        """Execute a single workflow step by creating task for agent"""
        
        try:
            # Create task for this step
            task_data = {
                "id": str(uuid.uuid4()),
                "title": f"Workflow Step: {step.step_name}",
                "description": f"Step {step.step_id} in workflow {workflow_run_id}",
                "task_type": step.task_type,
                "status": TaskStatus.QUEUED.value,
                "priority": 25,  # High priority for workflow steps
                "required_capabilities": [],  # Would derive from step
                "payload": step.input_data,
                "max_retries": step.retry_count,
                "workflow_run_id": workflow_run_id,
                "workflow_step_id": step.step_id,
                "deadline_at": datetime.utcnow().timestamp() + step.timeout_seconds
            }
            
            # Create task in database
            task = self.task_repo.create_task(task_data)
            
            if not task:
                raise Exception("Failed to create task for workflow step")
            
            # Assign task to specific agent
            success = self.task_repo.update_task_status(
                task.id,
                TaskStatus.CLAIMED,
                additional_updates={
                    "owner_agent_id": step.agent_id,
                    "claimed_at": datetime.utcnow()
                }
            )
            
            if not success:
                raise Exception("Failed to assign task to agent")
            
            # Wait for task completion (simplified - in production would use Hatchet's durable execution)
            result = await self._wait_for_task_completion(task.id, step.timeout_seconds)
            
            return {
                "task_id": task.id,
                "status": "completed",
                "result": result,
                "agent_id": step.agent_id,
                "executed_at": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error("workflow_step_execution_failed",
                        workflow_run_id=workflow_run_id,
                        step_id=step.step_id,
                        error=str(e))
            
            return {
                "status": "failed",
                "error": str(e),
                "agent_id": step.agent_id,
                "failed_at": datetime.utcnow().isoformat()
            }
    
    async def _wait_for_task_completion(self, task_id: str, timeout_seconds: int) -> Dict[str, Any]:
        """Wait for task to complete with timeout (simplified implementation)"""
        
        start_time = datetime.utcnow()
        
        while True:
            task = self.task_repo.get_by_id(task_id)
            
            if not task:
                raise Exception(f"Task {task_id} not found")
            
            if task.status in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value]:
                if task.status == TaskStatus.COMPLETED.value:
                    return task.output or {"status": "completed"}
                else:
                    raise Exception(f"Task failed: {task.last_error}")
            
            # Check timeout
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            if elapsed > timeout_seconds:
                raise Exception(f"Task timeout after {elapsed} seconds")
            
            # Wait before checking again
            await asyncio.sleep(2)
    
    def get_workflow_statistics(self) -> Dict[str, Any]:
        """Get workflow execution statistics"""
        
        try:
            total_workflows = len(self._running_workflows)
            
            status_counts = {
                "running": 0,
                "completed": 0,
                "failed": 0,
                "cancelled": 0
            }
            
            for workflow in self._running_workflows.values():
                status = workflow["status"]
                status_counts[status] = status_counts.get(status, 0) + 1
            
            return {
                "total_workflows": total_workflows,
                "by_status": status_counts,
                "active_workflows": status_counts["running"],
                "success_rate": (status_counts["completed"] / max(total_workflows, 1)) * 100
            }
        
        except Exception as e:
            logger.error("workflow_statistics_failed", error=str(e))
            return {"error": str(e)}


# Predefined workflow templates for common agent patterns
class AgentWorkflowTemplates:
    """Common workflow patterns for AI agents"""
    
    @staticmethod
    def create_code_review_workflow(
        code_agent_id: str,
        review_agent_id: str,
        test_agent_id: str,
        code_input: Dict[str, Any]
    ) -> List[AgentWorkflowStep]:
        """Create a code review workflow: code analysis → review → testing"""
        
        return [
            AgentWorkflowStep(
                step_id="analyze_code",
                step_name="Analyze Code Quality",
                agent_id=code_agent_id,
                task_type="code_analysis",
                input_data=code_input,
                timeout_seconds=300
            ),
            AgentWorkflowStep(
                step_id="review_changes", 
                step_name="Review Code Changes",
                agent_id=review_agent_id,
                task_type="code_review",
                input_data={"depends_on_step": "analyze_code"},
                depends_on=["analyze_code"],
                timeout_seconds=600
            ),
            AgentWorkflowStep(
                step_id="run_tests",
                step_name="Run Automated Tests",
                agent_id=test_agent_id,
                task_type="testing",
                input_data={"test_type": "unit_and_integration"},
                depends_on=["review_changes"],
                timeout_seconds=900
            )
        ]
    
    @staticmethod
    def create_data_processing_workflow(
        extract_agent_id: str,
        transform_agent_id: str,
        load_agent_id: str,
        data_source: Dict[str, Any]
    ) -> List[AgentWorkflowStep]:
        """Create ETL workflow: extract → transform → load"""
        
        return [
            AgentWorkflowStep(
                step_id="extract_data",
                step_name="Extract Data from Source",
                agent_id=extract_agent_id,
                task_type="data_extraction",
                input_data=data_source,
                timeout_seconds=1800  # 30 minutes
            ),
            AgentWorkflowStep(
                step_id="transform_data",
                step_name="Transform and Clean Data", 
                agent_id=transform_agent_id,
                task_type="data_transformation",
                input_data={"depends_on_step": "extract_data"},
                depends_on=["extract_data"],
                timeout_seconds=3600  # 1 hour
            ),
            AgentWorkflowStep(
                step_id="load_data",
                step_name="Load Data to Destination",
                agent_id=load_agent_id,
                task_type="data_loading",
                input_data={"depends_on_step": "transform_data"},
                depends_on=["transform_data"],
                timeout_seconds=1800
            )
        ]
    
    @staticmethod
    def create_research_workflow(
        research_agent_id: str,
        analysis_agent_id: str,
        report_agent_id: str,
        research_topic: str
    ) -> List[AgentWorkflowStep]:
        """Create research workflow: gather → analyze → report"""
        
        return [
            AgentWorkflowStep(
                step_id="gather_information",
                step_name="Gather Research Information",
                agent_id=research_agent_id,
                task_type="research",
                input_data={"topic": research_topic, "depth": "comprehensive"},
                timeout_seconds=1200  # 20 minutes
            ),
            AgentWorkflowStep(
                step_id="analyze_findings",
                step_name="Analyze Research Findings",
                agent_id=analysis_agent_id,
                task_type="analysis",
                input_data={"depends_on_step": "gather_information"},
                depends_on=["gather_information"],
                timeout_seconds=900  # 15 minutes
            ),
            AgentWorkflowStep(
                step_id="generate_report",
                step_name="Generate Final Report",
                agent_id=report_agent_id,
                task_type="documentation",
                input_data={"depends_on_step": "analyze_findings", "format": "markdown"},
                depends_on=["analyze_findings"],
                timeout_seconds=600  # 10 minutes
            )
        ]