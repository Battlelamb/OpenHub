"""
Agent heartbeat and status monitoring service - clean and simple
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from asyncio import Task

from ..logging import get_logger
from ..config import get_settings
from ..database.connection import Database
from ..database.repositories.agents import AgentRepository
from ..models.agents import Agent, AgentStatus

logger = get_logger(__name__)
settings = get_settings()


class HeartbeatService:
    """Simple heartbeat monitoring for agents"""
    
    def __init__(self, database: Database):
        self.db = database
        self.agent_repo = AgentRepository(database)
        self.heartbeat_timeout = settings.heartbeat_timeout_sec
        self._monitor_task: Optional[Task] = None
        self._running = False
    
    async def start_monitoring(self) -> None:
        """Start heartbeat monitoring task"""
        
        if self._running:
            logger.warning("heartbeat_monitoring_already_running")
            return
        
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        
        logger.info("heartbeat_monitoring_started", 
                   timeout_sec=self.heartbeat_timeout)
    
    async def stop_monitoring(self) -> None:
        """Stop heartbeat monitoring"""
        
        self._running = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("heartbeat_monitoring_stopped")
    
    async def _monitor_loop(self) -> None:
        """Main monitoring loop - runs every 30 seconds"""
        
        while self._running:
            try:
                await self._check_agent_heartbeats()
                await asyncio.sleep(30)  # Check every 30 seconds
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("heartbeat_monitoring_error", error=str(e))
                await asyncio.sleep(30)  # Continue after error
    
    async def _check_agent_heartbeats(self) -> None:
        """Check all agent heartbeats and update status"""
        
        try:
            # Get all agents that should be online
            agents = self.agent_repo.find_by({"status": AgentStatus.ONLINE.value})
            
            if not agents:
                return
            
            timeout_threshold = datetime.utcnow() - timedelta(seconds=self.heartbeat_timeout)
            expired_agents = []
            
            for agent in agents:
                if agent.last_heartbeat and agent.last_heartbeat < timeout_threshold:
                    expired_agents.append(agent)
            
            if expired_agents:
                logger.info("expired_agents_detected", count=len(expired_agents))
                
                for agent in expired_agents:
                    await self._handle_expired_agent(agent)
        
        except Exception as e:
            logger.error("heartbeat_check_failed", error=str(e))
    
    async def _handle_expired_agent(self, agent: Agent) -> None:
        """Handle agent with expired heartbeat"""
        
        try:
            # Set agent to offline
            success = self.agent_repo.set_agent_status(agent.id, AgentStatus.OFFLINE)
            
            if success:
                logger.warning("agent_marked_offline_due_to_timeout", 
                              agent_id=agent.id,
                              agent_name=agent.agent_name,
                              last_heartbeat=agent.last_heartbeat)
                
                # TODO: Could emit event here for notification system
                # await self._emit_agent_offline_event(agent)
            
        except Exception as e:
            logger.error("failed_to_handle_expired_agent", 
                        agent_id=agent.id,
                        error=str(e))
    
    def get_heartbeat_stats(self) -> Dict[str, int]:
        """Get heartbeat monitoring statistics"""
        
        try:
            stats = {}
            
            # Count by status
            for status in AgentStatus:
                count = self.agent_repo.count(
                    where_clause="status = :status",
                    params={"status": status.value}
                )
                stats[f"{status.value}_agents"] = count
            
            # Count recently active (last 5 minutes)
            recent_threshold = datetime.utcnow() - timedelta(minutes=5)
            recent_count = self.agent_repo.count(
                where_clause="last_heartbeat > :threshold",
                params={"threshold": recent_threshold}
            )
            stats["recently_active"] = recent_count
            
            return stats
        
        except Exception as e:
            logger.error("heartbeat_stats_failed", error=str(e))
            return {"error": str(e)}


class AgentStatusManager:
    """Manage agent status transitions cleanly"""
    
    def __init__(self, database: Database):
        self.db = database
        self.agent_repo = AgentRepository(database)
    
    async def update_agent_status(
        self,
        agent_id: str,
        new_status: AgentStatus,
        reason: Optional[str] = None
    ) -> bool:
        """Update agent status with logging"""
        
        try:
            # Get current agent
            agent = self.agent_repo.get_by_id(agent_id)
            if not agent:
                logger.warning("status_update_agent_not_found", agent_id=agent_id)
                return False
            
            old_status = agent.status
            
            # Update status
            success = self.agent_repo.set_agent_status(agent_id, new_status)
            
            if success:
                logger.info("agent_status_updated", 
                           agent_id=agent_id,
                           agent_name=agent.agent_name,
                           old_status=old_status.value,
                           new_status=new_status.value,
                           reason=reason)
                
                # Could emit status change event here
                # await self._emit_status_change_event(agent, old_status, new_status, reason)
            
            return success
        
        except Exception as e:
            logger.error("agent_status_update_failed", 
                        agent_id=agent_id,
                        new_status=new_status.value,
                        error=str(e))
            return False
    
    async def set_agent_busy(self, agent_id: str, task_id: str) -> bool:
        """Set agent to busy status with current task"""
        
        try:
            updated = self.agent_repo.update(agent_id, {
                "status": AgentStatus.BUSY.value,
                "current_task": task_id
            })
            
            if updated:
                logger.info("agent_set_to_busy", 
                           agent_id=agent_id,
                           task_id=task_id)
            
            return updated is not None
        
        except Exception as e:
            logger.error("agent_busy_update_failed", 
                        agent_id=agent_id,
                        task_id=task_id,
                        error=str(e))
            return False
    
    async def set_agent_idle(self, agent_id: str) -> bool:
        """Set agent to idle status (available for work)"""
        
        try:
            updated = self.agent_repo.update(agent_id, {
                "status": AgentStatus.IDLE.value,
                "current_task": None
            })
            
            if updated:
                logger.info("agent_set_to_idle", agent_id=agent_id)
            
            return updated is not None
        
        except Exception as e:
            logger.error("agent_idle_update_failed", 
                        agent_id=agent_id,
                        error=str(e))
            return False
    
    def get_agent_status_summary(self) -> Dict[str, any]:
        """Get summary of all agent statuses"""
        
        try:
            summary = {"total_agents": 0, "by_status": {}}
            
            for status in AgentStatus:
                count = self.agent_repo.count(
                    where_clause="status = :status",
                    params={"status": status.value}
                )
                summary["by_status"][status.value] = count
                summary["total_agents"] += count
            
            return summary
        
        except Exception as e:
            logger.error("status_summary_failed", error=str(e))
            return {"error": str(e)}