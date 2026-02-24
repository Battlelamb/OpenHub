"""
JWT authentication system for OpenHub agents
"""
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Union
from passlib.context import CryptContext

from ..config import get_settings
from ..logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class JWTManager:
    """JWT token management for agent authentication"""
    
    def __init__(self):
        self.secret_key = settings.jwt_secret_key
        self.algorithm = settings.jwt_algorithm
        self.access_token_expire_minutes = settings.jwt_access_token_expire_minutes
        self.refresh_token_expire_days = settings.jwt_refresh_token_expire_days
    
    def create_access_token(
        self,
        subject: Union[str, Any],
        expires_delta: Optional[timedelta] = None,
        claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create JWT access token for agent"""
        
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=self.access_token_expire_minutes)
        
        # Standard JWT claims
        payload = {
            "sub": str(subject),  # Subject (agent_id)
            "exp": expire,        # Expiration
            "iat": datetime.now(timezone.utc),  # Issued at
            "type": "access"      # Token type
        }
        
        # Add custom claims
        if claims:
            payload.update(claims)
        
        try:
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            
            logger.info("access_token_created", 
                       subject=str(subject),
                       expires_at=expire.isoformat(),
                       claims=list(claims.keys()) if claims else [])
            
            return token
        
        except Exception as e:
            logger.error("access_token_creation_failed", 
                        subject=str(subject), 
                        error=str(e))
            raise
    
    def create_refresh_token(
        self,
        subject: Union[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT refresh token for token renewal"""
        
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(days=self.refresh_token_expire_days)
        
        payload = {
            "sub": str(subject),
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "refresh"
        }
        
        try:
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            
            logger.info("refresh_token_created", 
                       subject=str(subject),
                       expires_at=expire.isoformat())
            
            return token
        
        except Exception as e:
            logger.error("refresh_token_creation_failed", 
                        subject=str(subject), 
                        error=str(e))
            raise
    
    def verify_token(
        self,
        token: str,
        expected_type: str = "access"
    ) -> Dict[str, Any]:
        """Verify and decode JWT token"""
        
        try:
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm],
                options={"verify_signature": True, "verify_exp": True}
            )
            
            # Verify token type
            token_type = payload.get("type")
            if token_type != expected_type:
                raise jwt.InvalidTokenError(f"Invalid token type: expected {expected_type}, got {token_type}")
            
            # Verify required claims
            if "sub" not in payload:
                raise jwt.InvalidTokenError("Missing subject claim")
            
            logger.debug("token_verified_successfully", 
                        subject=payload.get("sub"),
                        token_type=token_type)
            
            return payload
        
        except jwt.ExpiredSignatureError:
            logger.warning("token_expired", token_preview=token[:20] + "...")
            raise
        
        except jwt.InvalidTokenError as e:
            logger.warning("token_invalid", 
                          error=str(e),
                          token_preview=token[:20] + "...")
            raise
        
        except Exception as e:
            logger.error("token_verification_failed", 
                        error=str(e),
                        token_preview=token[:20] + "...")
            raise
    
    def decode_token_without_verification(self, token: str) -> Dict[str, Any]:
        """Decode token without signature verification (for inspection)"""
        try:
            return jwt.decode(token, options={"verify_signature": False})
        except Exception as e:
            logger.error("token_decode_failed", error=str(e))
            return {}
    
    def is_token_expired(self, token: str) -> bool:
        """Check if token is expired without throwing exception"""
        try:
            payload = self.decode_token_without_verification(token)
            exp = payload.get("exp")
            if exp:
                return datetime.fromtimestamp(exp, timezone.utc) < datetime.now(timezone.utc)
            return True
        except Exception:
            return True
    
    def get_token_remaining_time(self, token: str) -> Optional[timedelta]:
        """Get remaining time before token expiration"""
        try:
            payload = self.decode_token_without_verification(token)
            exp = payload.get("exp")
            if exp:
                expire_time = datetime.fromtimestamp(exp, timezone.utc)
                remaining = expire_time - datetime.now(timezone.utc)
                return remaining if remaining.total_seconds() > 0 else timedelta(0)
            return None
        except Exception:
            return None


# Global JWT manager instance
jwt_manager = JWTManager()


def create_access_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None,
    claims: Optional[Dict[str, Any]] = None
) -> str:
    """Convenience function to create access token"""
    return jwt_manager.create_access_token(subject, expires_delta, claims)


def create_refresh_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """Convenience function to create refresh token"""
    return jwt_manager.create_refresh_token(subject, expires_delta)


def verify_token(token: str, expected_type: str = "access") -> Dict[str, Any]:
    """Convenience function to verify token"""
    return jwt_manager.verify_token(token, expected_type)


def hash_password(password: str) -> str:
    """Hash password for admin users"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)


def create_agent_tokens(agent_id: str, agent_name: str, role: str = "agent") -> Dict[str, str]:
    """Create both access and refresh tokens for an agent"""
    
    # Claims for agent context
    claims = {
        "agent_name": agent_name,
        "role": role,
        "permissions": get_role_permissions(role)
    }
    
    access_token = create_access_token(subject=agent_id, claims=claims)
    refresh_token = create_refresh_token(subject=agent_id)
    
    logger.info("agent_tokens_created", 
               agent_id=agent_id, 
               agent_name=agent_name,
               role=role)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


def get_role_permissions(role: str) -> list[str]:
    """Get permissions list for a role"""
    permissions = {
        "agent": [
            "tasks:claim",
            "tasks:update_progress", 
            "tasks:complete",
            "artifacts:upload",
            "artifacts:download_own",
            "events:create",
            "events:read_own",
            "communication:send_message",
            "communication:join_thread"
        ],
        "admin": [
            "agents:register",
            "agents:deactivate", 
            "agents:view_all",
            "tasks:create",
            "tasks:cancel",
            "tasks:reassign",
            "tasks:view_all",
            "system:configure",
            "system:monitor",
            "system:backup",
            "approvals:approve",
            "approvals:reject",
            "approvals:override",
            "*"  # Wildcard for admin
        ],
        "readonly": [
            "tasks:read",
            "agents:read", 
            "events:read",
            "artifacts:read"
        ]
    }
    
    return permissions.get(role, [])