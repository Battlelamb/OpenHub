"""
Policy management for Casbin RBAC system
"""
from pathlib import Path
from typing import List, Dict, Any, Optional
import csv
import io

from ...config import get_settings
from ...logging import get_logger
from .models import (
    PolicyRule, RoleDefinition, DEFAULT_ROLES, PERMISSION_PATTERNS,
    Subject, Resource, Action
)

logger = get_logger(__name__)
settings = get_settings()


class PolicyManager:
    """Clean and elegant policy management"""
    
    def __init__(self, policies_dir: Optional[Path] = None):
        self.policies_dir = policies_dir or Path(__file__).parent / "policies"
        self.policies_dir.mkdir(exist_ok=True)
        
        # Policy file paths
        self.rbac_policy_file = self.policies_dir / "rbac_policy.csv"
        self.role_inheritance_file = self.policies_dir / "role_inheritance.csv"
        
        logger.info("policy_manager_initialized", policies_dir=str(self.policies_dir))
    
    def generate_default_policies(self) -> List[PolicyRule]:
        """Generate clean default RBAC policies"""
        
        policies = []
        
        # Agent policies - task execution focus
        agent_policies = [
            # Task permissions
            PolicyRule(subject="agent", resource="task", action="read"),
            PolicyRule(subject="agent", resource="task", action="claim"), 
            PolicyRule(subject="agent", resource="task", action="update"),
            PolicyRule(subject="agent", resource="task", action="complete"),
            
            # Artifact permissions
            PolicyRule(subject="agent", resource="artifact", action="read"),
            PolicyRule(subject="agent", resource="artifact", action="upload"),
            PolicyRule(subject="agent", resource="artifact", action="download"),
            
            # Communication permissions
            PolicyRule(subject="agent", resource="thread", action="read"),
            PolicyRule(subject="agent", resource="message", action="send"),
            PolicyRule(subject="agent", resource="message", action="read"),
            
            # Event permissions
            PolicyRule(subject="agent", resource="event", action="create"),
            PolicyRule(subject="agent", resource="event", action="read"),
            
            # Self-management
            PolicyRule(subject="agent", resource="agent", action="read"),
            PolicyRule(subject="agent", resource="agent", action="update", conditions={"owner": "self"}),
        ]
        policies.extend(agent_policies)
        
        # Admin policies - full system control
        admin_policies = [
            # Wildcard admin access
            PolicyRule(subject="admin", resource="*", action="*"),
            
            # Explicit admin permissions (for clarity)
            PolicyRule(subject="admin", resource="task", action="create"),
            PolicyRule(subject="admin", resource="task", action="cancel"),
            PolicyRule(subject="admin", resource="task", action="assign"),
            PolicyRule(subject="admin", resource="agent", action="create"),
            PolicyRule(subject="admin", resource="agent", action="delete"),
            PolicyRule(subject="admin", resource="system", action="configure"),
            PolicyRule(subject="admin", resource="system", action="backup"),
            PolicyRule(subject="admin", resource="api_key", action="create"),
            PolicyRule(subject="admin", resource="api_key", action="delete"),
        ]
        policies.extend(admin_policies)
        
        # Service policies - automated integrations
        service_policies = [
            PolicyRule(subject="service", resource="task", action="create"),
            PolicyRule(subject="service", resource="task", action="read"),
            PolicyRule(subject="service", resource="task", action="update"),
            PolicyRule(subject="service", resource="artifact", action="upload"),
            PolicyRule(subject="service", resource="artifact", action="read"),
            PolicyRule(subject="service", resource="event", action="create"),
            PolicyRule(subject="service", resource="system", action="monitor"),
            PolicyRule(subject="service", resource="webhook", action="send"),
        ]
        policies.extend(service_policies)
        
        # Readonly policies - monitoring and reporting
        readonly_policies = [
            PolicyRule(subject="readonly", resource="task", action="read"),
            PolicyRule(subject="readonly", resource="agent", action="read"),
            PolicyRule(subject="readonly", resource="artifact", action="read"),
            PolicyRule(subject="readonly", resource="event", action="read"),
            PolicyRule(subject="readonly", resource="system", action="monitor"),
            PolicyRule(subject="readonly", resource="thread", action="read"),
            PolicyRule(subject="readonly", resource="message", action="read"),
        ]
        policies.extend(readonly_policies)
        
        # Webhook policies - limited task creation
        webhook_policies = [
            PolicyRule(subject="webhook", resource="task", action="create"),
            PolicyRule(subject="webhook", resource="event", action="create"),
            PolicyRule(subject="webhook", resource="webhook", action="receive"),
        ]
        policies.extend(webhook_policies)
        
        logger.info("default_policies_generated", count=len(policies))
        return policies
    
    def save_policies_to_csv(self, policies: List[PolicyRule]) -> None:
        """Save policies to CSV file for Casbin"""
        
        try:
            with open(self.rbac_policy_file, 'w', newline='', encoding='utf-8') as csvfile:
                # Casbin RBAC format: p, subject, resource, action, effect
                writer = csv.writer(csvfile)
                
                # Write header comment
                writer.writerow(['# Policy Type', 'Subject', 'Resource', 'Action', 'Effect'])
                
                for policy in policies:
                    writer.writerow([
                        'p',  # Policy type
                        policy.subject,
                        policy.resource,
                        policy.action,
                        policy.effect
                    ])
            
            logger.info("policies_saved_to_csv", 
                       file=str(self.rbac_policy_file),
                       count=len(policies))
        
        except Exception as e:
            logger.error("policy_save_failed", error=str(e))
            raise
    
    def save_role_inheritance_to_csv(self, roles: Dict[str, RoleDefinition]) -> None:
        """Save role inheritance to CSV file"""
        
        try:
            with open(self.role_inheritance_file, 'w', newline='', encoding='utf-8') as csvfile:
                # Casbin role inheritance format: g, user, role
                writer = csv.writer(csvfile)
                
                # Write header comment
                writer.writerow(['# Inheritance Type', 'Child Role', 'Parent Role'])
                
                for role_name, role_def in roles.items():
                    for parent_role in role_def.inherits_from:
                        writer.writerow([
                            'g',  # Grouping policy type
                            role_name,
                            parent_role
                        ])
                
                # Add some example user-role assignments
                example_assignments = [
                    ('agent:claude-code-001', 'agent'),
                    ('agent:cursor-002', 'agent'), 
                    ('service:github-actions', 'service'),
                    ('admin:system', 'admin'),
                    ('monitor:prometheus', 'readonly')
                ]
                
                for user, role in example_assignments:
                    writer.writerow(['g', user, role])
            
            logger.info("role_inheritance_saved", 
                       file=str(self.role_inheritance_file))
        
        except Exception as e:
            logger.error("role_inheritance_save_failed", error=str(e))
            raise
    
    def load_policies_from_csv(self) -> List[PolicyRule]:
        """Load policies from CSV file"""
        
        policies = []
        
        try:
            if not self.rbac_policy_file.exists():
                logger.warning("policy_file_not_found", file=str(self.rbac_policy_file))
                return []
            
            with open(self.rbac_policy_file, 'r', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                
                for row in reader:
                    # Skip comments and empty rows
                    if not row or row[0].startswith('#'):
                        continue
                    
                    if len(row) >= 5 and row[0] == 'p':
                        policy = PolicyRule(
                            subject=row[1],
                            resource=row[2], 
                            action=row[3],
                            effect=row[4] if len(row) > 4 else "allow"
                        )
                        policies.append(policy)
            
            logger.info("policies_loaded_from_csv", 
                       count=len(policies),
                       file=str(self.rbac_policy_file))
            return policies
        
        except Exception as e:
            logger.error("policy_load_failed", error=str(e))
            return []
    
    def create_casbin_model_conf(self) -> str:
        """Create Casbin model configuration"""
        
        model_conf = """
[request_definition]
r = sub, obj, act

[policy_definition]  
p = sub, obj, act, eft

[role_definition]
g = _, _

[policy_effect]
e = some(where (p.eft == allow)) && !some(where (p.eft == deny))

[matchers]
m = g(r.sub, p.sub) && r.obj == p.obj && r.act == p.act
"""
        
        model_file = self.policies_dir / "rbac_model.conf"
        
        try:
            with open(model_file, 'w', encoding='utf-8') as f:
                f.write(model_conf.strip())
            
            logger.info("casbin_model_created", file=str(model_file))
            return str(model_file)
        
        except Exception as e:
            logger.error("casbin_model_creation_failed", error=str(e))
            raise
    
    def validate_policies(self, policies: List[PolicyRule]) -> List[str]:
        """Validate policy rules and return any issues"""
        
        issues = []
        
        valid_subjects = {s.value for s in Subject} | {"*"}
        valid_resources = {r.value for r in Resource} | {"*"}  
        valid_actions = {a.value for a in Action} | {"*"}
        
        for i, policy in enumerate(policies):
            # Check subject validity
            if policy.subject not in valid_subjects and not policy.subject.startswith(('agent:', 'service:', 'admin:')):
                issues.append(f"Policy {i}: Invalid subject '{policy.subject}'")
            
            # Check resource validity
            if policy.resource not in valid_resources:
                issues.append(f"Policy {i}: Invalid resource '{policy.resource}'")
            
            # Check action validity
            if policy.action not in valid_actions:
                issues.append(f"Policy {i}: Invalid action '{policy.action}'")
            
            # Check effect validity
            if policy.effect not in ["allow", "deny"]:
                issues.append(f"Policy {i}: Invalid effect '{policy.effect}'")
        
        if issues:
            logger.warning("policy_validation_issues", issues=issues)
        else:
            logger.info("policy_validation_passed", count=len(policies))
        
        return issues
    
    def get_policies_summary(self) -> Dict[str, Any]:
        """Get summary of current policies"""
        
        policies = self.load_policies_from_csv()
        
        summary = {
            "total_policies": len(policies),
            "by_subject": {},
            "by_resource": {},
            "by_action": {},
            "by_effect": {}
        }
        
        for policy in policies:
            # Count by subject
            summary["by_subject"][policy.subject] = summary["by_subject"].get(policy.subject, 0) + 1
            
            # Count by resource
            summary["by_resource"][policy.resource] = summary["by_resource"].get(policy.resource, 0) + 1
            
            # Count by action
            summary["by_action"][policy.action] = summary["by_action"].get(policy.action, 0) + 1
            
            # Count by effect
            summary["by_effect"][policy.effect] = summary["by_effect"].get(policy.effect, 0) + 1
        
        return summary


def load_default_policies() -> None:
    """Load default policies and save to files"""
    
    policy_manager = PolicyManager()
    
    # Generate and save policies
    policies = policy_manager.generate_default_policies()
    policy_manager.save_policies_to_csv(policies)
    
    # Save role inheritance
    policy_manager.save_role_inheritance_to_csv(DEFAULT_ROLES)
    
    # Create Casbin model
    policy_manager.create_casbin_model_conf()
    
    logger.info("default_policies_loaded_successfully")