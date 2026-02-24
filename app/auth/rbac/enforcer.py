"""
Casbin enforcer for OpenHub RBAC system
"""
import asyncio
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List
import casbin

from ...config import get_settings
from ...logging import get_logger
from .policies import PolicyManager, load_default_policies
from .models import PermissionCheck, PermissionResult

logger = get_logger(__name__)
settings = get_settings()


class CasbinEnforcer:
    """Clean and thread-safe Casbin enforcer wrapper"""
    
    def __init__(self, policies_dir: Optional[Path] = None):
        self.policies_dir = policies_dir or Path(__file__).parent / "policies"
        self.policy_manager = PolicyManager(self.policies_dir)
        self._enforcer: Optional[casbin.Enforcer] = None
        self._lock = threading.Lock()
        
        # Initialize policies if not exist
        self._ensure_policies_exist()
        
    def _ensure_policies_exist(self) -> None:
        """Ensure policy files exist, create defaults if not"""
        
        model_file = self.policies_dir / "rbac_model.conf"
        policy_file = self.policies_dir / "rbac_policy.csv"
        
        if not model_file.exists() or not policy_file.exists():
            logger.info("creating_default_policies")
            load_default_policies()
    
    def _get_enforcer(self) -> casbin.Enforcer:
        """Get or create Casbin enforcer instance (thread-safe)"""
        
        if self._enforcer is None:
            with self._lock:
                if self._enforcer is None:
                    try:
                        model_file = self.policies_dir / "rbac_model.conf"
                        policy_file = self.policies_dir / "rbac_policy.csv"
                        
                        if not model_file.exists() or not policy_file.exists():
                            raise FileNotFoundError("Policy files not found")
                        
                        # Create Casbin enforcer
                        self._enforcer = casbin.Enforcer(str(model_file), str(policy_file))
                        
                        # Enable auto-save
                        self._enforcer.enable_auto_save(True)
                        
                        logger.info("casbin_enforcer_initialized", 
                                   model_file=str(model_file),
                                   policy_file=str(policy_file))
                    
                    except Exception as e:
                        logger.error("casbin_enforcer_initialization_failed", error=str(e))
                        raise
        
        return self._enforcer
    
    def check_permission(
        self, 
        subject: str, 
        resource: str, 
        action: str,
        context: Optional[Dict[str, Any]] = None
    ) -> PermissionResult:
        """
        Check if subject has permission to perform action on resource
        
        Args:
            subject: Agent ID, role name, or API key identifier
            resource: Resource being accessed (task, agent, artifact, etc.)
            action: Action being performed (read, create, update, etc.)
            context: Additional context for permission checking
            
        Returns:
            PermissionResult with decision and reasoning
        """
        
        try:
            enforcer = self._get_enforcer()
            
            # Simple permission check
            allowed = enforcer.enforce(subject, resource, action)
            
            # Get matching policies for explanation
            matched_policies = self._get_matching_policies(subject, resource, action)
            
            # Determine reason
            if allowed:
                reason = f"Access granted for {subject} to {action} {resource}"
                if matched_policies:
                    reason += f" (matched policies: {', '.join(matched_policies)})"
            else:
                reason = f"Access denied for {subject} to {action} {resource}"
                
                # Check if subject has any roles
                roles = enforcer.get_roles_for_user(subject)
                if roles:
                    reason += f" (roles: {', '.join(roles)})"
                else:
                    reason += " (no roles assigned)"
            
            result = PermissionResult(
                allowed=allowed,
                reason=reason,
                matched_policies=matched_policies,
                context=context or {}
            )
            
            logger.debug("permission_check_completed", 
                        subject=subject,
                        resource=resource, 
                        action=action,
                        allowed=allowed)
            
            return result
        
        except Exception as e:
            logger.error("permission_check_failed", 
                        subject=subject,
                        resource=resource,
                        action=action, 
                        error=str(e))
            
            # Fail closed - deny access on error
            return PermissionResult(
                allowed=False,
                reason=f"Permission check failed: {str(e)}",
                matched_policies=[],
                context=context or {}
            )
    
    def check_permission_bulk(
        self,
        checks: List[PermissionCheck]
    ) -> List[PermissionResult]:
        """Check multiple permissions efficiently"""
        
        results = []
        
        for check in checks:
            result = self.check_permission(
                check.subject,
                check.resource,
                check.action,
                check.context
            )
            results.append(result)
        
        return results
    
    def _get_matching_policies(
        self, 
        subject: str, 
        resource: str, 
        action: str
    ) -> List[str]:
        """Get list of policies that would match this request"""
        
        try:
            enforcer = self._get_enforcer()
            matched = []
            
            # Get all policies
            policies = enforcer.get_policy()
            
            for policy in policies:
                if len(policy) >= 3:
                    policy_subject, policy_resource, policy_action = policy[0], policy[1], policy[2]
                    
                    # Check if this policy matches
                    if (self._matches(subject, policy_subject, enforcer) and
                        self._pattern_matches(resource, policy_resource) and
                        self._pattern_matches(action, policy_action)):
                        
                        matched.append(f"{policy_subject}:{policy_resource}:{policy_action}")
            
            return matched
        
        except Exception as e:
            logger.error("policy_matching_failed", error=str(e))
            return []
    
    def _matches(self, subject: str, policy_subject: str, enforcer: casbin.Enforcer) -> bool:
        """Check if subject matches policy subject (including role inheritance)"""
        
        # Direct match
        if subject == policy_subject:
            return True
        
        # Wildcard match
        if policy_subject == "*":
            return True
        
        # Role inheritance check
        if enforcer.has_role_for_user(subject, policy_subject):
            return True
        
        return False
    
    def _pattern_matches(self, value: str, pattern: str) -> bool:
        """Check if value matches pattern (simple wildcard support)"""
        
        if value == pattern:
            return True
        
        if pattern == "*":
            return True
        
        # Could add more sophisticated pattern matching here
        return False
    
    def add_role_for_user(self, user: str, role: str) -> bool:
        """Add role for user"""
        
        try:
            enforcer = self._get_enforcer()
            success = enforcer.add_role_for_user(user, role)
            
            if success:
                logger.info("role_added_for_user", user=user, role=role)
            else:
                logger.warning("role_add_failed", user=user, role=role)
            
            return success
        
        except Exception as e:
            logger.error("role_add_error", user=user, role=role, error=str(e))
            return False
    
    def remove_role_for_user(self, user: str, role: str) -> bool:
        """Remove role from user"""
        
        try:
            enforcer = self._get_enforcer()
            success = enforcer.delete_role_for_user(user, role)
            
            if success:
                logger.info("role_removed_for_user", user=user, role=role)
            else:
                logger.warning("role_removal_failed", user=user, role=role)
            
            return success
        
        except Exception as e:
            logger.error("role_removal_error", user=user, role=role, error=str(e))
            return False
    
    def get_roles_for_user(self, user: str) -> List[str]:
        """Get all roles for user"""
        
        try:
            enforcer = self._get_enforcer()
            roles = enforcer.get_roles_for_user(user)
            
            logger.debug("roles_retrieved_for_user", user=user, roles=roles)
            return roles
        
        except Exception as e:
            logger.error("roles_retrieval_error", user=user, error=str(e))
            return []
    
    def get_users_for_role(self, role: str) -> List[str]:
        """Get all users with specific role"""
        
        try:
            enforcer = self._get_enforcer()
            users = enforcer.get_users_for_role(role)
            
            logger.debug("users_retrieved_for_role", role=role, users=users)
            return users
        
        except Exception as e:
            logger.error("users_retrieval_error", role=role, error=str(e))
            return []
    
    def add_policy(self, subject: str, resource: str, action: str, effect: str = "allow") -> bool:
        """Add new policy rule"""
        
        try:
            enforcer = self._get_enforcer()
            success = enforcer.add_policy(subject, resource, action, effect)
            
            if success:
                logger.info("policy_added", 
                           subject=subject,
                           resource=resource,
                           action=action,
                           effect=effect)
            else:
                logger.warning("policy_add_failed", 
                              subject=subject,
                              resource=resource,
                              action=action)
            
            return success
        
        except Exception as e:
            logger.error("policy_add_error", 
                        subject=subject,
                        resource=resource,
                        action=action,
                        error=str(e))
            return False
    
    def remove_policy(self, subject: str, resource: str, action: str) -> bool:
        """Remove policy rule"""
        
        try:
            enforcer = self._get_enforcer()
            success = enforcer.remove_policy(subject, resource, action)
            
            if success:
                logger.info("policy_removed", 
                           subject=subject,
                           resource=resource,
                           action=action)
            else:
                logger.warning("policy_removal_failed", 
                              subject=subject,
                              resource=resource,
                              action=action)
            
            return success
        
        except Exception as e:
            logger.error("policy_removal_error", 
                        subject=subject,
                        resource=resource,
                        action=action,
                        error=str(e))
            return False
    
    def reload_policies(self) -> bool:
        """Reload policies from file"""
        
        try:
            enforcer = self._get_enforcer()
            enforcer.load_policy()
            
            logger.info("policies_reloaded")
            return True
        
        except Exception as e:
            logger.error("policy_reload_error", error=str(e))
            return False
    
    def get_policy_summary(self) -> Dict[str, Any]:
        """Get summary of current policies and roles"""
        
        try:
            enforcer = self._get_enforcer()
            
            summary = {
                "total_policies": len(enforcer.get_policy()),
                "total_roles": len(enforcer.get_grouping_policy()),
                "policies": enforcer.get_policy(),
                "role_assignments": enforcer.get_grouping_policy()
            }
            
            return summary
        
        except Exception as e:
            logger.error("policy_summary_error", error=str(e))
            return {"error": str(e)}


# Global enforcer instance
_enforcer: Optional[CasbinEnforcer] = None
_enforcer_lock = threading.Lock()


def get_enforcer() -> CasbinEnforcer:
    """Get global Casbin enforcer instance"""
    
    global _enforcer
    
    if _enforcer is None:
        with _enforcer_lock:
            if _enforcer is None:
                _enforcer = CasbinEnforcer()
                logger.info("global_casbin_enforcer_initialized")
    
    return _enforcer