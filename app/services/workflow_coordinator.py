"""
Agent-Workflow Coordination Service - clean bridge between agents and Hatchet workflows
"""
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from enum import Enum

from ..logging import get_logger
from ..config import get_settings
from ..database.connection import Database
from ..database.repositories.tasks import TaskRepository
from ..database.repositories.agents import AgentRepository
from ..services.hatchet_service import HatchetService, AgentWorkflowStep
from ..services.capability_matcher import CapabilityMatcher
from ..models.tasks import TaskStatus, TaskType
from ..models.agents import AgentStatus

logger = get_logger(__name__)
settings = get_settings()


class WorkflowPriority(str, Enum):
    """Workflow execution priorities"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class AgentWorkflowCoordination:
    """Coordination details between agent and workflow"""
    coordination_id: str
    workflow_run_id: str
    agent_id: str
    step_id: str
    status: str  # "assigned", "executing", "completed", "failed"
    assigned_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class WorkflowExecutionPlan:
    """Execution plan for workflow with agent assignments"""
    workflow_name: str
    total_steps: int
    estimated_duration_minutes: int
    required_agents: List[str]
    capability_requirements: Dict[str, List[str]]
    step_dependencies: Dict[str, List[str]]
    resource_requirements: Dict[str, Any]


class WorkflowCoordinator:
    """Clean coordination layer between agents and workflows"""
    
    def __init__(self, database: Database):
        self.db = database
        self.task_repo = TaskRepository(database)
        self.agent_repo = AgentRepository(database)
        self.hatchet_service = HatchetService(database)
        self.capability_matcher = CapabilityMatcher(database)
        
        # Active coordinations tracking
        self._active_coordinations: Dict[str, AgentWorkflowCoordination] = {}
        self._workflow_agent_assignments: Dict[str, List[str]] = {}  # workflow_id -> agent_ids
        
        logger.info("workflow_coordinator_initialized")
    
    async def plan_workflow_execution(self, 
                                     workflow_name: str,
                                     steps: List[AgentWorkflowStep],
                                     priority: WorkflowPriority = WorkflowPriority.NORMAL) -> WorkflowExecutionPlan:
        """
        Create execution plan by finding optimal agent assignments
        
        Args:
            workflow_name: Name of the workflow
            steps: Workflow steps to plan
            priority: Execution priority
            
        Returns:
            Detailed execution plan with agent assignments
        """
        
        logger.info("workflow_planning_started",
                   workflow_name=workflow_name,
                   steps_count=len(steps),
                   priority=priority.value)
        
        try:
            # Analyze capability requirements
            capability_requirements = {}
            required_agents = []
            
            for step in steps:
                # For each step, find required capabilities
                agent = self.agent_repo.get_by_id(step.agent_id)
                if agent:
                    capability_requirements[step.step_id] = agent.capabilities
                    if step.agent_id not in required_agents:
                        required_agents.append(step.agent_id)
                else:
                    # Try to find suitable agent by capabilities
                    suitable_agent = await self._find_suitable_agent_for_step(step)
                    if suitable_agent:
                        capability_requirements[step.step_id] = suitable_agent.capabilities
                        required_agents.append(suitable_agent.id)
                        # Update step with found agent
                        step.agent_id = suitable_agent.id
                    else:
                        raise ValueError(f"No suitable agent found for step '{step.step_name}'")
            
            # Build dependency map
            step_dependencies = {}
            for step in steps:
                step_dependencies[step.step_id] = step.depends_on or []
            
            # Estimate duration
            total_timeout = sum(step.timeout_seconds for step in steps)
            estimated_duration_minutes = max(15, total_timeout // 60)  # Minimum 15 minutes
            
            # Calculate resource requirements
            resource_requirements = {
                "total_agents": len(required_agents),
                "parallel_execution": len([s for s in steps if not s.depends_on]),
                "max_concurrent_steps": self._calculate_max_concurrent_steps(steps),
                "priority": priority.value
            }
            
            plan = WorkflowExecutionPlan(
                workflow_name=workflow_name,
                total_steps=len(steps),
                estimated_duration_minutes=estimated_duration_minutes,
                required_agents=required_agents,
                capability_requirements=capability_requirements,
                step_dependencies=step_dependencies,
                resource_requirements=resource_requirements
            )
            
            logger.info("workflow_planning_completed",
                       workflow_name=workflow_name,
                       required_agents=len(required_agents),
                       estimated_duration=estimated_duration_minutes)
            
            return plan
        
        except Exception as e:
            logger.error("workflow_planning_failed",
                        workflow_name=workflow_name,
                        error=str(e))
            raise
    
    async def coordinate_workflow_execution(self,
                                          execution_plan: WorkflowExecutionPlan,
                                          steps: List[AgentWorkflowStep],
                                          input_data: Optional[Dict[str, Any]] = None,
                                          created_by: Optional[str] = None) -> str:
        """
        Coordinate workflow execution with smart agent management
        
        Args:
            execution_plan: Pre-computed execution plan
            steps: Workflow steps to execute
            input_data: Initial workflow data
            created_by: User/agent creating the workflow
            
        Returns:
            Workflow run ID
        """
        
        logger.info("workflow_coordination_started",
                   workflow_name=execution_plan.workflow_name,
                   required_agents=len(execution_plan.required_agents))
        
        try:
            # Pre-check agent availability
            await self._ensure_agents_available(execution_plan.required_agents)
            
            # Reserve agents for this workflow
            workflow_run_id = await self._reserve_agents_for_workflow(
                execution_plan.required_agents,
                execution_plan.workflow_name
            )
            
            # Create coordinations for each step
            coordinations = []
            for step in steps:
                coordination = AgentWorkflowCoordination(
                    coordination_id=str(uuid.uuid4()),
                    workflow_run_id=workflow_run_id,
                    agent_id=step.agent_id,
                    step_id=step.step_id,
                    status="assigned",
                    assigned_at=datetime.utcnow()
                )
                coordinations.append(coordination)
                self._active_coordinations[coordination.coordination_id] = coordination
            
            # Store workflow-agent assignments
            self._workflow_agent_assignments[workflow_run_id] = execution_plan.required_agents
            
            # Start workflow with Hatchet
            actual_workflow_run_id = await self.hatchet_service.create_agent_workflow(
                workflow_name=execution_plan.workflow_name,
                steps=steps,
                input_data=input_data,
                created_by=created_by
            )
            
            # Update coordination tracking
            for coordination in coordinations:
                coordination.workflow_run_id = actual_workflow_run_id
                self._active_coordinations[coordination.coordination_id] = coordination
            
            # Start monitoring workflow execution
            asyncio.create_task(self._monitor_workflow_coordination(actual_workflow_run_id))
            
            logger.info("workflow_coordination_successful",
                       workflow_name=execution_plan.workflow_name,
                       workflow_run_id=actual_workflow_run_id,
                       coordinations=len(coordinations))
            
            return actual_workflow_run_id
        
        except Exception as e:
            logger.error("workflow_coordination_failed",
                        workflow_name=execution_plan.workflow_name,
                        error=str(e))
            # Cleanup any reserved agents
            if 'workflow_run_id' in locals():
                await self._release_agents_from_workflow(workflow_run_id)
            raise
    
    async def get_coordination_status(self, workflow_run_id: str) -> Dict[str, Any]:
        """Get detailed coordination status for workflow"""
        
        try:
            # Get workflow status from Hatchet
            workflow_status = await self.hatchet_service.get_workflow_status(workflow_run_id)
            
            if not workflow_status:
                return {"error": "Workflow not found"}
            
            # Get coordination details
            coordinations = [
                coord for coord in self._active_coordinations.values()
                if coord.workflow_run_id == workflow_run_id
            ]
            
            # Get agent statuses
            agent_details = []
            assigned_agents = self._workflow_agent_assignments.get(workflow_run_id, [])
            
            for agent_id in assigned_agents:
                agent = self.agent_repo.get_by_id(agent_id)
                if agent:
                    # Find coordination for this agent
                    agent_coordination = next(
                        (coord for coord in coordinations if coord.agent_id == agent_id),
                        None
                    )
                    
                    agent_details.append({
                        "agent_id": agent_id,
                        "agent_name": agent.agent_name,
                        "agent_status": agent.status.value,
                        "coordination_status": agent_coordination.status if agent_coordination else "unknown",
                        "current_step": agent_coordination.step_id if agent_coordination else None,
                        "assigned_at": agent_coordination.assigned_at.isoformat() if agent_coordination else None,
                        "started_at": agent_coordination.started_at.isoformat() if agent_coordination and agent_coordination.started_at else None
                    })
            
            return {
                "workflow_status": workflow_status,
                "coordination_details": {
                    "total_coordinations": len(coordinations),
                    "active_coordinations": len([c for c in coordinations if c.status in ["assigned", "executing"]]),
                    "completed_coordinations": len([c for c in coordinations if c.status == "completed"]),
                    "failed_coordinations": len([c for c in coordinations if c.status == "failed"]),
                    "agent_assignments": agent_details
                }
            }
        
        except Exception as e:
            logger.error("coordination_status_failed",
                        workflow_run_id=workflow_run_id,
                        error=str(e))
            return {"error": str(e)}
    
    async def _find_suitable_agent_for_step(self, step: AgentWorkflowStep) -> Optional[Any]:
        """Find suitable agent for workflow step based on requirements"""
        
        try:
            # If step specifies agent ID, validate it
            if step.agent_id and step.agent_id != "auto":
                agent = self.agent_repo.get_by_id(step.agent_id)
                if agent and agent.status.value in ["online", "idle"]:
                    return agent
                else:
                    logger.warning("specified_agent_not_available",
                                 step_id=step.step_id,
                                 agent_id=step.agent_id)
            
            # Find agent by task type capabilities
            required_capabilities = self._infer_capabilities_from_task_type(step.task_type)
            
            if required_capabilities:
                best_match = self.capability_matcher.find_best_agent(
                    required_capabilities=required_capabilities,
                    min_score=0.6  # Higher threshold for workflows
                )
                
                if best_match:
                    logger.info("suitable_agent_found_for_step",
                               step_id=step.step_id,
                               agent_id=best_match.agent.id,
                               match_score=best_match.match_score)
                    return best_match.agent
            
            logger.warning("no_suitable_agent_found",
                          step_id=step.step_id,
                          task_type=step.task_type)
            return None
        
        except Exception as e:
            logger.error("find_suitable_agent_failed",
                        step_id=step.step_id,
                        error=str(e))
            return None
    
    def _infer_capabilities_from_task_type(self, task_type: str) -> List[str]:
        """Infer required capabilities from task type"""
        
        capability_mapping = {
            "code_analysis": ["python", "code_review", "static_analysis"],
            "code_review": ["code_review", "python", "javascript"],
            "testing": ["testing", "pytest", "automation"],
            "data_extraction": ["data_processing", "etl", "python"],
            "data_transformation": ["data_processing", "pandas", "python"],
            "data_loading": ["database", "data_processing", "sql"],
            "research": ["web_search", "research", "analysis"],
            "analysis": ["data_analysis", "research", "reporting"],
            "documentation": ["writing", "documentation", "markdown"]
        }
        
        return capability_mapping.get(task_type, [task_type])
    
    def _calculate_max_concurrent_steps(self, steps: List[AgentWorkflowStep]) -> int:
        """Calculate maximum concurrent steps in workflow"""
        
        # Simple calculation: count steps with no dependencies
        independent_steps = len([step for step in steps if not step.depends_on])
        
        # Add some steps that can run after first level
        second_level_steps = 0
        for step in steps:
            if step.depends_on and len(step.depends_on) == 1:
                second_level_steps += 1
        
        return max(independent_steps, min(second_level_steps, 3))  # Max 3 concurrent
    
    async def _ensure_agents_available(self, required_agent_ids: List[str]) -> None:
        """Ensure all required agents are available for workflow"""
        
        unavailable_agents = []
        
        for agent_id in required_agent_ids:
            agent = self.agent_repo.get_by_id(agent_id)
            
            if not agent:
                unavailable_agents.append(f"Agent {agent_id} not found")
                continue
            
            if agent.status.value not in ["online", "idle"]:
                unavailable_agents.append(f"Agent {agent_id} not available (status: {agent.status.value})")
                continue
            
            # Check if agent is already assigned to another workflow
            active_coordination = next(
                (coord for coord in self._active_coordinations.values()
                 if coord.agent_id == agent_id and coord.status in ["assigned", "executing"]),
                None
            )
            
            if active_coordination:
                unavailable_agents.append(f"Agent {agent_id} already assigned to workflow {active_coordination.workflow_run_id}")
        
        if unavailable_agents:
            raise ValueError(f"Required agents not available: {', '.join(unavailable_agents)}")
    
    async def _reserve_agents_for_workflow(self, agent_ids: List[str], workflow_name: str) -> str:
        """Reserve agents for workflow execution"""
        
        workflow_run_id = str(uuid.uuid4())
        
        try:
            for agent_id in agent_ids:
                # Update agent status to busy and assign to workflow
                success = self.agent_repo.update(agent_id, {
                    "status": AgentStatus.BUSY.value,
                    "current_task": f"workflow_{workflow_run_id}"
                })
                
                if not success:
                    raise Exception(f"Failed to reserve agent {agent_id}")
            
            logger.info("agents_reserved_for_workflow",
                       workflow_run_id=workflow_run_id,
                       workflow_name=workflow_name,
                       agent_count=len(agent_ids))
            
            return workflow_run_id
        
        except Exception as e:
            # Rollback any reservations
            await self._release_agents_from_workflow(workflow_run_id)
            raise
    
    async def _release_agents_from_workflow(self, workflow_run_id: str) -> None:
        """Release agents from workflow assignment"""
        
        try:
            assigned_agents = self._workflow_agent_assignments.get(workflow_run_id, [])
            
            for agent_id in assigned_agents:
                # Set agent back to idle
                self.agent_repo.update(agent_id, {
                    "status": AgentStatus.IDLE.value,
                    "current_task": None
                })
            
            # Clean up tracking
            if workflow_run_id in self._workflow_agent_assignments:
                del self._workflow_agent_assignments[workflow_run_id]
            
            # Remove coordinations
            coordinations_to_remove = [
                coord_id for coord_id, coord in self._active_coordinations.items()
                if coord.workflow_run_id == workflow_run_id
            ]
            
            for coord_id in coordinations_to_remove:
                del self._active_coordinations[coord_id]
            
            logger.info("agents_released_from_workflow",
                       workflow_run_id=workflow_run_id,
                       released_count=len(assigned_agents))
        
        except Exception as e:
            logger.error("agent_release_failed",
                        workflow_run_id=workflow_run_id,
                        error=str(e))
    
    async def _monitor_workflow_coordination(self, workflow_run_id: str) -> None:
        """Monitor workflow execution and update coordination status"""
        
        logger.info("workflow_monitoring_started", workflow_run_id=workflow_run_id)
        
        try:
            while True:
                workflow_status = await self.hatchet_service.get_workflow_status(workflow_run_id)
                
                if not workflow_status:
                    break
                
                status = workflow_status["status"]
                
                if status in ["completed", "failed", "cancelled"]:
                    # Workflow finished - release agents
                    await self._release_agents_from_workflow(workflow_run_id)
                    
                    logger.info("workflow_monitoring_completed",
                               workflow_run_id=workflow_run_id,
                               final_status=status)
                    break
                
                # Update coordination statuses based on workflow progress
                await self._update_coordination_statuses(workflow_run_id, workflow_status)
                
                # Wait before next check
                await asyncio.sleep(10)
        
        except Exception as e:
            logger.error("workflow_monitoring_failed",
                        workflow_run_id=workflow_run_id,
                        error=str(e))
    
    async def _update_coordination_statuses(self, workflow_run_id: str, workflow_status: Dict[str, Any]) -> None:
        """Update coordination statuses based on workflow progress"""
        
        try:
            step_results = workflow_status.get("progress", {}).get("step_results", {})
            
            for coord in self._active_coordinations.values():
                if coord.workflow_run_id != workflow_run_id:
                    continue
                
                step_result = step_results.get(coord.step_id)
                
                if step_result:
                    if step_result.get("status") == "completed":
                        coord.status = "completed"
                        coord.completed_at = datetime.utcnow()
                        coord.result = step_result.get("result")
                    elif step_result.get("status") == "failed":
                        coord.status = "failed"
                        coord.completed_at = datetime.utcnow()
                        coord.error = step_result.get("error")
                elif coord.status == "assigned":
                    # If step hasn't started yet but coordination exists, mark as executing
                    coord.status = "executing"
                    coord.started_at = datetime.utcnow()
        
        except Exception as e:
            logger.error("coordination_status_update_failed",
                        workflow_run_id=workflow_run_id,
                        error=str(e))
    
    async def _find_agents_for_template(self, 
                                       template_name: str, 
                                       params: Dict[str, Any],
                                       preferred_agents: Optional[List[str]] = None,
                                       exclude_agents: Optional[List[str]] = None) -> Dict[str, str]:
        """Find suitable agents for workflow template"""
        
        try:
            agents = {}
            
            if template_name == "code_review":
                # Find agents for code review workflow
                if not params.get("code_agent_id"):
                    code_agent = self.capability_matcher.find_best_agent(["python", "code_analysis"])
                    if code_agent:
                        agents["code_agent_id"] = code_agent.agent.id
                
                if not params.get("review_agent_id"):
                    review_agent = self.capability_matcher.find_best_agent(["code_review", "python"])
                    if review_agent:
                        agents["review_agent_id"] = review_agent.agent.id
                
                if not params.get("test_agent_id"):
                    test_agent = self.capability_matcher.find_best_agent(["testing", "pytest"])
                    if test_agent:
                        agents["test_agent_id"] = test_agent.agent.id
            
            elif template_name == "data_processing":
                # Find agents for ETL workflow
                if not params.get("extract_agent_id"):
                    extract_agent = self.capability_matcher.find_best_agent(["data_processing", "etl"])
                    if extract_agent:
                        agents["extract_agent_id"] = extract_agent.agent.id
                
                if not params.get("transform_agent_id"):
                    transform_agent = self.capability_matcher.find_best_agent(["data_processing", "pandas"])
                    if transform_agent:
                        agents["transform_agent_id"] = transform_agent.agent.id
                
                if not params.get("load_agent_id"):
                    load_agent = self.capability_matcher.find_best_agent(["database", "sql"])
                    if load_agent:
                        agents["load_agent_id"] = load_agent.agent.id
            
            elif template_name == "research":
                # Find agents for research workflow
                if not params.get("research_agent_id"):
                    research_agent = self.capability_matcher.find_best_agent(["research", "web_search"])
                    if research_agent:
                        agents["research_agent_id"] = research_agent.agent.id
                
                if not params.get("analysis_agent_id"):
                    analysis_agent = self.capability_matcher.find_best_agent(["analysis", "data_analysis"])
                    if analysis_agent:
                        agents["analysis_agent_id"] = analysis_agent.agent.id
                
                if not params.get("report_agent_id"):
                    report_agent = self.capability_matcher.find_best_agent(["documentation", "writing"])
                    if report_agent:
                        agents["report_agent_id"] = report_agent.agent.id
            
            logger.debug("agents_found_for_template",
                        template_name=template_name,
                        found_agents=list(agents.keys()))
            
            return agents
        
        except Exception as e:
            logger.error("find_agents_for_template_failed",
                        template_name=template_name,
                        error=str(e))
            return {}
    
    async def _rebuild_steps_from_plan(self, execution_plan_response, original_request) -> List[AgentWorkflowStep]:
        """Rebuild workflow steps from execution plan for execution"""
        
        steps = []
        
        if original_request.workflow_type == "custom" and original_request.custom_steps:
            for i, step_data in enumerate(original_request.custom_steps):
                step = AgentWorkflowStep(
                    step_id=f"custom_step_{i+1}",
                    step_name=step_data.get("step_name", f"Step {i+1}"),
                    agent_id=execution_plan_response.required_agents[i] if i < len(execution_plan_response.required_agents) else "auto",
                    task_type=step_data.get("task_type", "general"),
                    input_data=step_data.get("input_data", {}),
                    depends_on=step_data.get("depends_on", []),
                    timeout_seconds=step_data.get("timeout_seconds", 300),
                    retry_count=step_data.get("retry_count", 2)
                )
                steps.append(step)
        
        elif original_request.workflow_type == "code_review":
            params = original_request.template_params or {}
            from ..services.hatchet_service import AgentWorkflowTemplates
            steps = AgentWorkflowTemplates.create_code_review_workflow(
                code_agent_id=execution_plan_response.required_agents[0] if len(execution_plan_response.required_agents) > 0 else "auto",
                review_agent_id=execution_plan_response.required_agents[1] if len(execution_plan_response.required_agents) > 1 else "auto",
                test_agent_id=execution_plan_response.required_agents[2] if len(execution_plan_response.required_agents) > 2 else "auto",
                code_input=params.get("code_input", {})
            )
        
        elif original_request.workflow_type == "data_processing":
            params = original_request.template_params or {}
            from ..services.hatchet_service import AgentWorkflowTemplates
            steps = AgentWorkflowTemplates.create_data_processing_workflow(
                extract_agent_id=execution_plan_response.required_agents[0] if len(execution_plan_response.required_agents) > 0 else "auto",
                transform_agent_id=execution_plan_response.required_agents[1] if len(execution_plan_response.required_agents) > 1 else "auto",
                load_agent_id=execution_plan_response.required_agents[2] if len(execution_plan_response.required_agents) > 2 else "auto",
                data_source=params.get("data_source", {})
            )
        
        elif original_request.workflow_type == "research":
            params = original_request.template_params or {}
            from ..services.hatchet_service import AgentWorkflowTemplates
            steps = AgentWorkflowTemplates.create_research_workflow(
                research_agent_id=execution_plan_response.required_agents[0] if len(execution_plan_response.required_agents) > 0 else "auto",
                analysis_agent_id=execution_plan_response.required_agents[1] if len(execution_plan_response.required_agents) > 1 else "auto",
                report_agent_id=execution_plan_response.required_agents[2] if len(execution_plan_response.required_agents) > 2 else "auto",
                research_topic=params.get("research_topic", "")
            )
        
        return steps
    
    def get_coordination_statistics(self) -> Dict[str, Any]:
        """Get workflow coordination statistics"""
        
        try:
            total_coordinations = len(self._active_coordinations)
            active_workflows = len(self._workflow_agent_assignments)
            
            status_counts = {
                "assigned": 0,
                "executing": 0,
                "completed": 0,
                "failed": 0
            }
            
            for coordination in self._active_coordinations.values():
                status_counts[coordination.status] = status_counts.get(coordination.status, 0) + 1
            
            return {
                "total_coordinations": total_coordinations,
                "active_workflows": active_workflows,
                "coordination_status": status_counts,
                "success_rate": (status_counts["completed"] / max(total_coordinations, 1)) * 100
            }
        
        except Exception as e:
            logger.error("coordination_statistics_failed", error=str(e))
            return {"error": str(e)}