"""
Task service for OpenHub - clean business logic
"""
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from ..logging import get_logger
from ..config import get_settings
from ..database.connection import Database
from ..database.repositories.tasks import TaskRepository
from ..database.repositories.agents import AgentRepository
from ..models.tasks import (
    Task, TaskCreate, TaskUpdate, TaskClaim, TaskComplete, TaskFail, 
    TaskStatus, TaskPriority, TaskType, TaskProgress
)
from ..models.agents import AgentStatus
from ..services.capability_matcher import CapabilityMatcher

logger = get_logger(__name__)
settings = get_settings()


class TaskService:
    """Clean task management service"""
    
    def __init__(self, database: Database):
        self.db = database
        self.task_repo = TaskRepository(database)
        self.agent_repo = AgentRepository(database)
        self.capability_matcher = CapabilityMatcher(database)
    
    def create_task(self, task_data: TaskCreate, created_by: Optional[str] = None) -> Task:
        """
        Create a new task with automatic agent matching
        """
        logger.info("task_creation_started", 
                   title=task_data.title, 
                   task_type=task_data.task_type,
                   required_capabilities=task_data.required_capabilities)
        
        try:
            # Generate task ID
            task_id = str(uuid.uuid4())
            
            # Create task record
            new_task = self.task_repo.create({
                "id": task_id,
                "title": task_data.title,
                "description": task_data.description,
                "task_type": task_data.task_type.value,
                "priority": task_data.priority,
                "status": TaskStatus.QUEUED.value,
                "required_capabilities": task_data.required_capabilities,
                "payload": task_data.payload,
                "deadline_at": task_data.deadline_at,
                "max_retries": task_data.max_retries,
                "idempotency_key": task_data.idempotency_key,
                "labels": task_data.labels,
                "created_by": created_by
            })
            
            if not new_task:
                raise Exception("Failed to create task in database")
            
            logger.info("task_created_successfully", 
                       task_id=task_id,
                       title=task_data.title)
            
            # Try automatic agent assignment
            self._attempt_auto_assignment(new_task)
            
            return new_task
        
        except Exception as e:
            logger.error("task_creation_failed", 
                        title=task_data.title,
                        error=str(e))
            raise
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID"""
        return self.task_repo.get_by_id(task_id)
    
    def update_task(self, task_id: str, updates: TaskUpdate) -> Optional[Task]:
        """Update task details"""
        logger.info("task_update_started", task_id=task_id)
        
        try:
            # Get current task
            current_task = self.task_repo.get_by_id(task_id)
            if not current_task:
                logger.warning("task_update_not_found", task_id=task_id)
                return None
            
            # Prepare update data
            update_data = {}
            if updates.title is not None:
                update_data["title"] = updates.title
            if updates.description is not None:
                update_data["description"] = updates.description
            if updates.priority is not None:
                update_data["priority"] = updates.priority
            if updates.deadline_at is not None:
                update_data["deadline_at"] = updates.deadline_at
            if updates.labels is not None:
                update_data["labels"] = updates.labels
            
            if not update_data:
                return current_task  # No updates provided
            
            # Update task
            updated_task = self.task_repo.update(task_id, update_data)
            
            if updated_task:
                logger.info("task_updated_successfully", 
                           task_id=task_id,
                           updates=list(update_data.keys()))
            
            return updated_task
        
        except Exception as e:
            logger.error("task_update_failed", 
                        task_id=task_id,
                        error=str(e))
            raise
    
    def claim_task(self, task_id: str, claim_data: TaskClaim) -> bool:
        """Claim task for an agent"""
        logger.info("task_claim_started", 
                   task_id=task_id,
                   agent_id=claim_data.agent_id)
        
        try:
            # Check if task exists and is available
            task = self.task_repo.get_by_id(task_id)
            if not task:
                logger.warning("task_claim_not_found", task_id=task_id)
                return False
            
            if task.status != TaskStatus.QUEUED:
                logger.warning("task_claim_invalid_status", 
                              task_id=task_id,
                              current_status=task.status)
                return False
            
            # Check if agent exists and is available
            agent = self.agent_repo.get_by_id(claim_data.agent_id)
            if not agent:
                logger.warning("task_claim_agent_not_found", agent_id=claim_data.agent_id)
                return False
            
            if agent.status not in [AgentStatus.ONLINE, AgentStatus.IDLE]:
                logger.warning("task_claim_agent_not_available", 
                              agent_id=claim_data.agent_id,
                              agent_status=agent.status)
                return False
            
            # Calculate lease expiration
            lease_duration = settings.task_lease_ttl_sec
            lease_until = datetime.utcnow() + timedelta(seconds=lease_duration)
            
            # Update task status
            update_data = {
                "status": TaskStatus.CLAIMED.value,
                "owner_agent_id": claim_data.agent_id,
                "claimed_at": datetime.utcnow(),
                "lease_until": lease_until
            }
            
            updated_task = self.task_repo.update(task_id, update_data)
            if not updated_task:
                return False
            
            # Update agent status
            self.agent_repo.update(claim_data.agent_id, {
                "status": AgentStatus.BUSY.value,
                "current_task": task_id
            })
            
            logger.info("task_claimed_successfully", 
                       task_id=task_id,
                       agent_id=claim_data.agent_id,
                       lease_until=lease_until)
            
            return True
        
        except Exception as e:
            logger.error("task_claim_failed", 
                        task_id=task_id,
                        agent_id=claim_data.agent_id,
                        error=str(e))
            return False
    
    def start_task(self, task_id: str, agent_id: str) -> bool:
        """Start task execution"""
        logger.info("task_start_requested", task_id=task_id, agent_id=agent_id)
        
        try:
            # Verify task is claimed by this agent
            task = self.task_repo.get_by_id(task_id)
            if not task or task.owner_agent_id != agent_id:
                logger.warning("task_start_unauthorized", 
                              task_id=task_id, 
                              agent_id=agent_id)
                return False
            
            if task.status != TaskStatus.CLAIMED:
                logger.warning("task_start_invalid_status", 
                              task_id=task_id,
                              current_status=task.status)
                return False
            
            # Update task to running
            updated_task = self.task_repo.update(task_id, {
                "status": TaskStatus.RUNNING.value,
                "started_at": datetime.utcnow()
            })
            
            if updated_task:
                logger.info("task_started_successfully", 
                           task_id=task_id,
                           agent_id=agent_id)
                return True
            
            return False
        
        except Exception as e:
            logger.error("task_start_failed", 
                        task_id=task_id,
                        agent_id=agent_id,
                        error=str(e))
            return False
    
    def update_progress(self, task_id: str, agent_id: str, progress: TaskProgress) -> bool:
        """Update task progress"""
        logger.debug("task_progress_update", 
                    task_id=task_id,
                    agent_id=agent_id,
                    progress_percent=progress.progress_percent)
        
        try:
            # Verify agent owns the task
            task = self.task_repo.get_by_id(task_id)
            if not task or task.owner_agent_id != agent_id:
                return False
            
            if task.status != TaskStatus.RUNNING:
                return False
            
            # Update progress (stored in payload for now)
            current_payload = task.payload or {}
            current_payload["progress"] = {
                "percent": progress.progress_percent,
                "note": progress.note,
                "metrics": progress.metrics,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            updated_task = self.task_repo.update(task_id, {
                "payload": current_payload
            })
            
            return updated_task is not None
        
        except Exception as e:
            logger.error("task_progress_update_failed", 
                        task_id=task_id,
                        error=str(e))
            return False
    
    def complete_task(self, task_id: str, agent_id: str, completion: TaskComplete) -> bool:
        """Complete a task"""
        logger.info("task_completion_started", 
                   task_id=task_id,
                   agent_id=agent_id)
        
        try:
            # Verify agent owns the task
            task = self.task_repo.get_by_id(task_id)
            if not task or task.owner_agent_id != agent_id:
                logger.warning("task_completion_unauthorized", 
                              task_id=task_id,
                              agent_id=agent_id)
                return False
            
            if task.status not in [TaskStatus.RUNNING, TaskStatus.WAITING_APPROVAL]:
                logger.warning("task_completion_invalid_status", 
                              task_id=task_id,
                              current_status=task.status)
                return False
            
            # Calculate duration
            duration = None
            if task.started_at:
                duration = (datetime.utcnow() - task.started_at).total_seconds()
            
            # Update task
            update_data = {
                "status": TaskStatus.COMPLETED.value,
                "completed_at": datetime.utcnow(),
                "result_summary": completion.result_summary,
                "output": completion.output,
                "artifact_ids": completion.artifact_ids,
                "duration_seconds": duration
            }
            
            # Add completion metrics to payload
            if completion.metrics:
                current_payload = task.payload or {}
                current_payload["completion_metrics"] = completion.metrics
                update_data["payload"] = current_payload
            
            updated_task = self.task_repo.update(task_id, update_data)
            if not updated_task:
                return False
            
            # Free up the agent
            self.agent_repo.update(agent_id, {
                "status": AgentStatus.IDLE.value,
                "current_task": None
            })
            
            logger.info("task_completed_successfully", 
                       task_id=task_id,
                       agent_id=agent_id,
                       duration_seconds=duration)
            
            return True
        
        except Exception as e:
            logger.error("task_completion_failed", 
                        task_id=task_id,
                        agent_id=agent_id,
                        error=str(e))
            return False
    
    def fail_task(self, task_id: str, agent_id: str, failure: TaskFail) -> bool:
        """Fail a task with optional retry"""
        logger.info("task_failure_started", 
                   task_id=task_id,
                   agent_id=agent_id,
                   retryable=failure.retryable)
        
        try:
            # Verify agent owns the task
            task = self.task_repo.get_by_id(task_id)
            if not task or task.owner_agent_id != agent_id:
                return False
            
            # Check if task can be retried
            can_retry = (failure.retryable and 
                        task.retry_count < task.max_retries)
            
            if can_retry:
                # Retry the task
                update_data = {
                    "status": TaskStatus.QUEUED.value,
                    "owner_agent_id": None,
                    "claimed_at": None,
                    "started_at": None,
                    "lease_until": None,
                    "retry_count": task.retry_count + 1,
                    "last_error": failure.error_message
                }
                
                logger.info("task_queued_for_retry", 
                           task_id=task_id,
                           retry_count=task.retry_count + 1)
                
                # Try auto-assignment for retry
                updated_task = self.task_repo.update(task_id, update_data)
                if updated_task:
                    self._attempt_auto_assignment(updated_task)
            else:
                # Permanently fail the task
                update_data = {
                    "status": TaskStatus.FAILED.value,
                    "completed_at": datetime.utcnow(),
                    "last_error": failure.error_message
                }
                
                # Store error details in payload
                current_payload = task.payload or {}
                current_payload["error_details"] = {
                    "error_code": failure.error_code,
                    "error_message": failure.error_message,
                    "error_details": failure.error_details,
                    "failed_at": datetime.utcnow().isoformat()
                }
                update_data["payload"] = current_payload
                
                self.task_repo.update(task_id, update_data)
                
                logger.warning("task_failed_permanently", 
                              task_id=task_id,
                              retry_count=task.retry_count,
                              max_retries=task.max_retries)
            
            # Free up the agent
            self.agent_repo.update(agent_id, {
                "status": AgentStatus.IDLE.value,
                "current_task": None
            })
            
            return True
        
        except Exception as e:
            logger.error("task_failure_processing_failed", 
                        task_id=task_id,
                        error=str(e))
            return False
    
    def cancel_task(self, task_id: str, reason: Optional[str] = None) -> bool:
        """Cancel a pending or running task"""
        logger.info("task_cancellation_started", task_id=task_id)
        
        try:
            task = self.task_repo.get_by_id(task_id)
            if not task:
                return False
            
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                logger.warning("task_already_finished", 
                              task_id=task_id,
                              current_status=task.status)
                return False
            
            # Update task status
            update_data = {
                "status": TaskStatus.CANCELLED.value,
                "completed_at": datetime.utcnow()
            }
            
            if reason:
                current_payload = task.payload or {}
                current_payload["cancellation_reason"] = reason
                update_data["payload"] = current_payload
            
            updated_task = self.task_repo.update(task_id, update_data)
            
            # Free up agent if assigned
            if task.owner_agent_id:
                self.agent_repo.update(task.owner_agent_id, {
                    "status": AgentStatus.IDLE.value,
                    "current_task": None
                })
            
            if updated_task:
                logger.info("task_cancelled_successfully", 
                           task_id=task_id,
                           reason=reason)
                return True
            
            return False
        
        except Exception as e:
            logger.error("task_cancellation_failed", 
                        task_id=task_id,
                        error=str(e))
            return False
    
    def _attempt_auto_assignment(self, task: Task) -> None:
        """Attempt automatic task assignment to best available agent"""
        try:
            # Find best agent for this task
            best_match = self.capability_matcher.find_best_agent(
                required_capabilities=task.required_capabilities,
                min_score=0.5  # Minimum 50% capability match
            )
            
            if best_match and best_match.agent.status in [AgentStatus.ONLINE, AgentStatus.IDLE]:
                # Auto-assign task
                claim_data = TaskClaim(agent_id=best_match.agent.id)
                success = self.claim_task(task.id, claim_data)
                
                if success:
                    logger.info("task_auto_assigned", 
                               task_id=task.id,
                               agent_id=best_match.agent.id,
                               match_score=best_match.match_score)
                else:
                    logger.warning("task_auto_assignment_failed", 
                                  task_id=task.id,
                                  agent_id=best_match.agent.id)
            else:
                logger.info("no_suitable_agent_found", 
                           task_id=task.id,
                           required_capabilities=task.required_capabilities)
        
        except Exception as e:
            logger.error("auto_assignment_error", 
                        task_id=task.id,
                        error=str(e))
    
    def get_agent_tasks(self, agent_id: str, status_filter: Optional[List[TaskStatus]] = None) -> List[Task]:
        """Get tasks assigned to specific agent"""
        try:
            filter_conditions = {"owner_agent_id": agent_id}
            
            if status_filter:
                filter_conditions["status__in"] = [s.value for s in status_filter]
            
            return self.task_repo.find_by(filter_conditions)
        
        except Exception as e:
            logger.error("get_agent_tasks_failed", 
                        agent_id=agent_id,
                        error=str(e))
            return []
    
    def get_available_tasks(self, agent_id: str, limit: int = 10) -> List[Task]:
        """Get tasks available for claiming by an agent"""
        try:
            # Get agent to check capabilities
            agent = self.agent_repo.get_by_id(agent_id)
            if not agent:
                return []
            
            # Find queued tasks that match agent capabilities
            queued_tasks = self.task_repo.find_by({
                "status": TaskStatus.QUEUED.value
            })
            
            suitable_tasks = []
            for task in queued_tasks:
                # Check capability match
                match = self.capability_matcher._score_agent(agent, task.required_capabilities)
                if match and match.match_score >= 0.3:  # 30% minimum match
                    suitable_tasks.append(task)
            
            # Sort by priority and creation time
            suitable_tasks.sort(key=lambda t: (t.priority, t.created_at))
            
            return suitable_tasks[:limit]
        
        except Exception as e:
            logger.error("get_available_tasks_failed", 
                        agent_id=agent_id,
                        error=str(e))
            return []