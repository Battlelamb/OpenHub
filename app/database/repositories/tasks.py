"""
Task repository for database operations - clean and simple
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import and_, or_, desc, asc, func

from ...logging import get_logger
from ..base import BaseRepository
from ...models.tasks import Task, TaskStatus

logger = get_logger(__name__)


class TaskRepository(BaseRepository[Task]):
    """Repository for task database operations"""
    
    def __init__(self, database):
        super().__init__(database, Task)
    
    def create_task(self, task_data: Dict[str, Any]) -> Optional[Task]:
        """Create a new task"""
        try:
            with self.db.get_session() as session:
                task = Task(**task_data)
                session.add(task)
                session.commit()
                session.refresh(task)
                
                logger.info("task_created_in_db", task_id=task.id)
                return task
        
        except Exception as e:
            logger.error("task_creation_failed_in_db", 
                        task_id=task_data.get("id"),
                        error=str(e))
            return None
    
    def find_by_status(self, status: TaskStatus) -> List[Task]:
        """Find tasks by status"""
        try:
            with self.db.get_session() as session:
                tasks = session.query(Task).filter(
                    Task.status == status.value
                ).all()
                
                return tasks
        
        except Exception as e:
            logger.error("find_by_status_failed", 
                        status=status.value,
                        error=str(e))
            return []
    
    def find_by_agent(self, agent_id: str, status_filter: Optional[List[str]] = None) -> List[Task]:
        """Find tasks assigned to specific agent"""
        try:
            with self.db.get_session() as session:
                query = session.query(Task).filter(Task.owner_agent_id == agent_id)
                
                if status_filter:
                    query = query.filter(Task.status.in_(status_filter))
                
                tasks = query.order_by(desc(Task.created_at)).all()
                
                return tasks
        
        except Exception as e:
            logger.error("find_by_agent_failed", 
                        agent_id=agent_id,
                        error=str(e))
            return []
    
    def find_expired_leases(self) -> List[Task]:
        """Find tasks with expired leases"""
        try:
            with self.db.get_session() as session:
                now = datetime.utcnow()
                
                expired_tasks = session.query(Task).filter(
                    and_(
                        Task.status == TaskStatus.CLAIMED.value,
                        Task.lease_until < now
                    )
                ).all()
                
                return expired_tasks
        
        except Exception as e:
            logger.error("find_expired_leases_failed", error=str(e))
            return []
    
    def find_overdue_tasks(self) -> List[Task]:
        """Find tasks past their deadline"""
        try:
            with self.db.get_session() as session:
                now = datetime.utcnow()
                
                overdue_tasks = session.query(Task).filter(
                    and_(
                        Task.deadline_at.isnot(None),
                        Task.deadline_at < now,
                        Task.status.in_([
                            TaskStatus.QUEUED.value,
                            TaskStatus.CLAIMED.value,
                            TaskStatus.RUNNING.value
                        ])
                    )
                ).all()
                
                return overdue_tasks
        
        except Exception as e:
            logger.error("find_overdue_tasks_failed", error=str(e))
            return []
    
    def find_available_for_agent(self, agent_capabilities: List[str], limit: int = 10) -> List[Task]:
        """Find tasks available for agents with specific capabilities"""
        try:
            with self.db.get_session() as session:
                # For now, simple implementation - in real scenario would need JSON capability matching
                available_tasks = session.query(Task).filter(
                    Task.status == TaskStatus.QUEUED.value
                ).order_by(
                    asc(Task.priority),
                    desc(Task.created_at)
                ).limit(limit).all()
                
                return available_tasks
        
        except Exception as e:
            logger.error("find_available_for_agent_failed", 
                        capabilities=agent_capabilities,
                        error=str(e))
            return []
    
    def get_task_with_agent(self, task_id: str) -> Optional[Task]:
        """Get task with associated agent information"""
        try:
            with self.db.get_session() as session:
                task = session.query(Task).options(
                    selectinload(Task.assigned_agent)
                ).filter(Task.id == task_id).first()
                
                return task
        
        except Exception as e:
            logger.error("get_task_with_agent_failed", 
                        task_id=task_id,
                        error=str(e))
            return None
    
    def update_task_status(self, task_id: str, new_status: TaskStatus, 
                          additional_updates: Optional[Dict[str, Any]] = None) -> bool:
        """Update task status with optional additional fields"""
        try:
            with self.db.get_session() as session:
                update_data = {"status": new_status.value}
                
                if additional_updates:
                    update_data.update(additional_updates)
                
                result = session.query(Task).filter(Task.id == task_id).update(update_data)
                session.commit()
                
                if result > 0:
                    logger.info("task_status_updated", 
                               task_id=task_id,
                               new_status=new_status.value)
                    return True
                
                return False
        
        except Exception as e:
            logger.error("task_status_update_failed", 
                        task_id=task_id,
                        new_status=new_status.value,
                        error=str(e))
            return False
    
    def get_task_statistics(self) -> Dict[str, Any]:
        """Get comprehensive task statistics"""
        try:
            with self.db.get_session() as session:
                # Total tasks
                total_tasks = session.query(func.count(Task.id)).scalar()
                
                # Tasks by status
                status_counts = {}
                for status in TaskStatus:
                    count = session.query(func.count(Task.id)).filter(
                        Task.status == status.value
                    ).scalar()
                    status_counts[status.value] = count
                
                # Tasks by priority
                priority_counts = {}
                priority_query = session.query(
                    Task.priority, 
                    func.count(Task.id)
                ).group_by(Task.priority).all()
                
                for priority, count in priority_query:
                    priority_counts[str(priority)] = count
                
                # Tasks by type
                type_counts = {}
                type_query = session.query(
                    Task.task_type,
                    func.count(Task.id)
                ).group_by(Task.task_type).all()
                
                for task_type, count in type_query:
                    type_counts[task_type] = count
                
                # Assignment statistics
                assigned_count = session.query(func.count(Task.id)).filter(
                    Task.owner_agent_id.isnot(None)
                ).scalar()
                
                unassigned_count = total_tasks - assigned_count
                
                # Timing statistics
                completed_tasks = session.query(Task).filter(
                    and_(
                        Task.status == TaskStatus.COMPLETED.value,
                        Task.duration_seconds.isnot(None)
                    )
                ).all()
                
                avg_completion_time = None
                if completed_tasks:
                    total_duration = sum(task.duration_seconds for task in completed_tasks)
                    avg_completion_time = total_duration / len(completed_tasks) / 60  # minutes
                
                # Overdue tasks
                now = datetime.utcnow()
                overdue_count = session.query(func.count(Task.id)).filter(
                    and_(
                        Task.deadline_at.isnot(None),
                        Task.deadline_at < now,
                        Task.status.in_([
                            TaskStatus.QUEUED.value,
                            TaskStatus.CLAIMED.value,
                            TaskStatus.RUNNING.value
                        ])
                    )
                ).scalar()
                
                # Success rate
                completed_count = status_counts.get(TaskStatus.COMPLETED.value, 0)
                failed_count = status_counts.get(TaskStatus.FAILED.value, 0)
                finished_count = completed_count + failed_count
                
                success_rate = 0.0
                if finished_count > 0:
                    success_rate = completed_count / finished_count
                
                # Retry rate
                retry_count = session.query(func.count(Task.id)).filter(
                    Task.retry_count > 0
                ).scalar()
                
                retry_rate = 0.0
                if total_tasks > 0:
                    retry_rate = retry_count / total_tasks
                
                return {
                    "total_tasks": total_tasks,
                    "by_status": status_counts,
                    "by_priority": priority_counts,
                    "by_type": type_counts,
                    "assigned_tasks": assigned_count,
                    "unassigned_tasks": unassigned_count,
                    "avg_completion_time_minutes": avg_completion_time,
                    "overdue_tasks": overdue_count,
                    "success_rate": success_rate,
                    "retry_rate": retry_rate
                }
        
        except Exception as e:
            logger.error("get_task_statistics_failed", error=str(e))
            return {
                "error": str(e),
                "total_tasks": 0,
                "by_status": {},
                "by_priority": {},
                "by_type": {}
            }
    
    def search_tasks(self, 
                     search_query: Optional[str] = None,
                     status_filter: Optional[List[str]] = None,
                     priority_filter: Optional[List[int]] = None,
                     type_filter: Optional[List[str]] = None,
                     agent_filter: Optional[str] = None,
                     created_after: Optional[datetime] = None,
                     created_before: Optional[datetime] = None,
                     page: int = 1,
                     limit: int = 20,
                     sort_by: str = "created_at",
                     sort_order: str = "desc") -> Dict[str, Any]:
        """Advanced task search with filtering and pagination"""
        try:
            with self.db.get_session() as session:
                query = session.query(Task)
                
                # Text search
                if search_query:
                    search_term = f"%{search_query}%"
                    query = query.filter(
                        or_(
                            Task.title.ilike(search_term),
                            Task.description.ilike(search_term)
                        )
                    )
                
                # Status filter
                if status_filter:
                    query = query.filter(Task.status.in_(status_filter))
                
                # Priority filter
                if priority_filter:
                    query = query.filter(Task.priority.in_(priority_filter))
                
                # Type filter
                if type_filter:
                    query = query.filter(Task.task_type.in_(type_filter))
                
                # Agent filter
                if agent_filter:
                    query = query.filter(Task.owner_agent_id == agent_filter)
                
                # Date filters
                if created_after:
                    query = query.filter(Task.created_at >= created_after)
                
                if created_before:
                    query = query.filter(Task.created_at <= created_before)
                
                # Get total count before pagination
                total_count = query.count()
                
                # Sorting
                sort_column = getattr(Task, sort_by, Task.created_at)
                if sort_order.lower() == "desc":
                    query = query.order_by(desc(sort_column))
                else:
                    query = query.order_by(asc(sort_column))
                
                # Pagination
                offset = (page - 1) * limit
                tasks = query.offset(offset).limit(limit).all()
                
                return {
                    "tasks": tasks,
                    "total": total_count,
                    "page": page,
                    "limit": limit,
                    "total_pages": (total_count + limit - 1) // limit
                }
        
        except Exception as e:
            logger.error("search_tasks_failed", 
                        search_query=search_query,
                        error=str(e))
            return {
                "tasks": [],
                "total": 0,
                "page": page,
                "limit": limit,
                "total_pages": 0,
                "error": str(e)
            }
    
    def cleanup_expired_leases(self) -> int:
        """Clean up tasks with expired leases and return count"""
        try:
            with self.db.get_session() as session:
                now = datetime.utcnow()
                
                # Find and update expired tasks
                updated_count = session.query(Task).filter(
                    and_(
                        Task.status == TaskStatus.CLAIMED.value,
                        Task.lease_until < now
                    )
                ).update({
                    "status": TaskStatus.QUEUED.value,
                    "owner_agent_id": None,
                    "claimed_at": None,
                    "lease_until": None,
                    "last_error": "Lease expired - returned to queue"
                })
                
                session.commit()
                
                if updated_count > 0:
                    logger.info("expired_leases_cleaned_up", count=updated_count)
                
                return updated_count
        
        except Exception as e:
            logger.error("cleanup_expired_leases_failed", error=str(e))
            return 0