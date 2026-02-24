"""
Production-grade API Key management system for OpenHub
"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from enum import Enum

from ..config import get_settings
from ..logging import get_logger
from ..database.connection import Database

logger = get_logger(__name__)
settings = get_settings()


class APIKeyType(str, Enum):
    """API Key types for different use cases"""
    AGENT = "agent"           # For agent-to-hub communication
    SERVICE = "service"       # For service-to-service integration
    ADMIN = "admin"          # For administrative operations
    READONLY = "readonly"     # For read-only access
    WEBHOOK = "webhook"      # For webhook integrations


class APIKeyScope(str, Enum):
    """Predefined scopes for API keys"""
    # Agent scopes
    AGENT_REGISTER = "agent:register"
    AGENT_HEARTBEAT = "agent:heartbeat"
    
    # Task scopes
    TASK_READ = "task:read"
    TASK_CREATE = "task:create"
    TASK_UPDATE = "task:update"
    TASK_DELETE = "task:delete"
    
    # Artifact scopes
    ARTIFACT_READ = "artifact:read"
    ARTIFACT_UPLOAD = "artifact:upload"
    ARTIFACT_DELETE = "artifact:delete"
    
    # System scopes
    SYSTEM_MONITOR = "system:monitor"
    SYSTEM_ADMIN = "system:admin"
    
    # Webhook scopes
    WEBHOOK_RECEIVE = "webhook:receive"
    WEBHOOK_SEND = "webhook:send"


class APIKeyManager:
    """Clean and secure API Key management"""
    
    def __init__(self, database: Database):
        self.database = database
        self.key_prefix = "oh_"  # OpenHub prefix
        self.key_length = 32
        self.hash_algorithm = "sha256"
        self.salt_length = 16
    
    def _generate_key(self) -> str:
        """Generate cryptographically secure API key"""
        # Generate random bytes and encode as hex
        random_part = secrets.token_hex(self.key_length // 2)
        return f"{self.key_prefix}{random_part}"
    
    def _generate_salt(self) -> str:
        """Generate salt for key hashing"""
        return secrets.token_hex(self.salt_length)
    
    def _hash_key(self, api_key: str, salt: str) -> str:
        """Hash API key with salt for secure storage"""
        combined = f"{api_key}{salt}{settings.jwt_secret_key}"
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def _validate_scopes(self, scopes: List[str], key_type: APIKeyType) -> List[str]:
        """Validate and filter scopes based on key type"""
        valid_scopes = []
        type_scope_mapping = {
            APIKeyType.AGENT: [
                APIKeyScope.AGENT_REGISTER, APIKeyScope.AGENT_HEARTBEAT,
                APIKeyScope.TASK_READ, APIKeyScope.TASK_CREATE, APIKeyScope.TASK_UPDATE,
                APIKeyScope.ARTIFACT_READ, APIKeyScope.ARTIFACT_UPLOAD
            ],
            APIKeyType.SERVICE: [
                APIKeyScope.TASK_READ, APIKeyScope.TASK_CREATE,
                APIKeyScope.ARTIFACT_READ, APIKeyScope.SYSTEM_MONITOR
            ],
            APIKeyType.ADMIN: list(APIKeyScope),  # All scopes
            APIKeyType.READONLY: [
                APIKeyScope.TASK_READ, APIKeyScope.ARTIFACT_READ, APIKeyScope.SYSTEM_MONITOR
            ],
            APIKeyType.WEBHOOK: [
                APIKeyScope.WEBHOOK_RECEIVE, APIKeyScope.WEBHOOK_SEND,
                APIKeyScope.TASK_CREATE
            ]
        }
        
        allowed_scopes = type_scope_mapping.get(key_type, [])
        
        for scope in scopes:
            if scope in [s.value for s in allowed_scopes]:
                valid_scopes.append(scope)
            else:
                logger.warning("invalid_scope_for_key_type", 
                             scope=scope, 
                             key_type=key_type.value)
        
        return valid_scopes
    
    def create_api_key(
        self,
        name: str,
        key_type: APIKeyType,
        scopes: List[str],
        description: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        created_by: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new API key with clean validation
        
        Returns:
            Dict with 'api_key' (only returned once) and key metadata
        """
        logger.info("api_key_creation_started", 
                   name=name, 
                   key_type=key_type.value,
                   scopes=scopes)
        
        try:
            # Validate and clean scopes
            validated_scopes = self._validate_scopes(scopes, key_type)
            if not validated_scopes:
                raise ValueError("No valid scopes provided for key type")
            
            # Generate API key and security components
            api_key = self._generate_key()
            salt = self._generate_salt()
            key_hash = self._hash_key(api_key, salt)
            
            # Generate unique key ID
            from uuid import uuid4
            key_id = str(uuid4())
            
            # Set default expiration (1 year for most keys)
            if expires_at is None and key_type != APIKeyType.ADMIN:
                expires_at = datetime.now(timezone.utc) + timedelta(days=365)
            
            # Store in database
            self.database.execute("""
                INSERT INTO api_keys (
                    id, name, key_type, key_hash, salt, scopes,
                    description, expires_at, created_by, metadata,
                    is_active, created_at, updated_at
                ) VALUES (
                    :id, :name, :key_type, :key_hash, :salt, :scopes,
                    :description, :expires_at, :created_by, :metadata,
                    :is_active, :created_at, :updated_at
                )
            """, {
                "id": key_id,
                "name": name,
                "key_type": key_type.value,
                "key_hash": key_hash,
                "salt": salt,
                "scopes": str(validated_scopes),  # JSON string
                "description": description,
                "expires_at": expires_at,
                "created_by": created_by,
                "metadata": str(metadata or {}),
                "is_active": True,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            })
            
            logger.info("api_key_created_successfully", 
                       key_id=key_id,
                       name=name,
                       scopes=validated_scopes)
            
            # Return key details (API key only returned once!)
            return {
                "key_id": key_id,
                "api_key": api_key,  # ⚠️ Only returned here!
                "name": name,
                "key_type": key_type.value,
                "scopes": validated_scopes,
                "description": description,
                "expires_at": expires_at.isoformat() if expires_at else None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "is_active": True
            }
        
        except Exception as e:
            logger.error("api_key_creation_failed", 
                        name=name,
                        error=str(e))
            raise
    
    def validate_api_key(
        self, 
        api_key: str,
        required_scope: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Validate API key and return key information
        
        Returns None if invalid, key info dict if valid
        """
        if not api_key or not api_key.startswith(self.key_prefix):
            return None
        
        try:
            # Get all active keys and check against each one
            # This approach prevents timing attacks
            active_keys = self.database.fetch_all("""
                SELECT * FROM api_keys 
                WHERE is_active = true 
                AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
            """)
            
            for key_row in active_keys:
                key_data = dict(key_row)
                
                # Hash provided key with stored salt
                computed_hash = self._hash_key(api_key, key_data["salt"])
                
                # Constant-time comparison
                if secrets.compare_digest(computed_hash, key_data["key_hash"]):
                    # Key found! Validate scope if required
                    if required_scope:
                        import json
                        key_scopes = json.loads(key_data["scopes"])
                        if required_scope not in key_scopes:
                            logger.warning("api_key_insufficient_scope", 
                                         key_id=key_data["id"],
                                         required_scope=required_scope,
                                         available_scopes=key_scopes)
                            return None
                    
                    # Update last used timestamp
                    self.database.execute(
                        "UPDATE api_keys SET last_used_at = CURRENT_TIMESTAMP WHERE id = :id",
                        {"id": key_data["id"]}
                    )
                    
                    logger.debug("api_key_validated", 
                               key_id=key_data["id"],
                               name=key_data["name"])
                    
                    # Return sanitized key info
                    import json
                    return {
                        "key_id": key_data["id"],
                        "name": key_data["name"],
                        "key_type": key_data["key_type"],
                        "scopes": json.loads(key_data["scopes"]),
                        "created_by": key_data["created_by"],
                        "last_used_at": key_data.get("last_used_at")
                    }
            
            # Key not found
            logger.warning("api_key_validation_failed", 
                         key_prefix=api_key[:10] + "...")
            return None
        
        except Exception as e:
            logger.error("api_key_validation_error", error=str(e))
            return None
    
    def revoke_api_key(self, key_id: str, revoked_by: Optional[str] = None) -> bool:
        """Revoke an API key (soft delete)"""
        try:
            cursor = self.database.execute("""
                UPDATE api_keys 
                SET is_active = false, 
                    revoked_at = CURRENT_TIMESTAMP,
                    revoked_by = :revoked_by,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :key_id AND is_active = true
            """, {
                "key_id": key_id,
                "revoked_by": revoked_by
            })
            
            success = cursor.rowcount > 0
            
            if success:
                logger.info("api_key_revoked", 
                           key_id=key_id,
                           revoked_by=revoked_by)
            else:
                logger.warning("api_key_revocation_failed", key_id=key_id)
            
            return success
        
        except Exception as e:
            logger.error("api_key_revocation_error", 
                        key_id=key_id, 
                        error=str(e))
            return False
    
    def list_api_keys(
        self, 
        created_by: Optional[str] = None,
        key_type: Optional[APIKeyType] = None,
        include_inactive: bool = False
    ) -> List[Dict[str, Any]]:
        """List API keys with filtering options"""
        
        query = "SELECT * FROM api_keys WHERE 1=1"
        params = {}
        
        if not include_inactive:
            query += " AND is_active = true"
        
        if created_by:
            query += " AND created_by = :created_by"
            params["created_by"] = created_by
        
        if key_type:
            query += " AND key_type = :key_type"
            params["key_type"] = key_type.value
        
        query += " ORDER BY created_at DESC"
        
        try:
            rows = self.database.fetch_all(query, params)
            
            keys = []
            for row in rows:
                key_data = dict(row)
                import json
                
                # Never return the actual key or hash!
                keys.append({
                    "key_id": key_data["id"],
                    "name": key_data["name"],
                    "key_type": key_data["key_type"],
                    "scopes": json.loads(key_data["scopes"]),
                    "description": key_data["description"],
                    "created_at": key_data["created_at"],
                    "expires_at": key_data["expires_at"],
                    "last_used_at": key_data.get("last_used_at"),
                    "is_active": key_data["is_active"],
                    "created_by": key_data["created_by"]
                })
            
            return keys
        
        except Exception as e:
            logger.error("api_key_list_error", error=str(e))
            return []


# Global API key manager instance
_api_key_manager = None

def get_api_key_manager(database: Optional[Database] = None) -> APIKeyManager:
    """Get global API key manager instance"""
    global _api_key_manager
    
    if _api_key_manager is None:
        from ..database.connection import get_database
        db = database or get_database()
        _api_key_manager = APIKeyManager(db)
    
    return _api_key_manager