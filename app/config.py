"""
Configuration management for Agent Hub
"""
from pydantic import Field
from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Server Configuration
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=7788, description="Server port")
    debug: bool = Field(default=False, description="Debug mode")
    
    # Database Configuration
    db_path: str = Field(default="./data/state/agenthub.db", description="SQLite database path")
    
    # Storage Configuration  
    artifact_dir: str = Field(default="./data/artifacts", description="Artifact storage directory")
    zvec_path: str = Field(default="./data/zvec", description="Zvec data directory")
    
    # Cache Configuration
    redis_url: str = Field(default="redis://localhost:6379", description="Redis connection URL")
    
    # Security Configuration
    secret_key: str = Field(default="your-secret-key-change-in-production", description="Secret key for tokens")
    api_keys_file: str = Field(default="./data/state/api_keys.json", description="API keys file path")
    
    # Logging Configuration
    log_level: str = Field(default="INFO", description="Log level")
    log_file: Optional[str] = Field(default=None, description="Log file path")
    
    # Task Configuration
    task_lease_ttl_sec: int = Field(default=300, description="Task lease TTL in seconds")
    max_agents: int = Field(default=100, description="Maximum concurrent agents")
    max_concurrent_tasks: int = Field(default=50, description="Maximum concurrent tasks")
    
    # Vector Search Configuration
    vector_batch_size: int = Field(default=1000, description="Vector operation batch size")
    embedding_model: str = Field(default="sentence-transformers/all-MiniLM-L6-v2", description="Embedding model")
    
    # Cleanup Configuration
    event_retention_days: int = Field(default=30, description="Event retention in days")
    message_retention_days: int = Field(default=90, description="Message retention in days")
    
    # CORS Configuration
    cors_origins: List[str] = Field(default=["*"], description="CORS allowed origins")
    cors_methods: List[str] = Field(default=["*"], description="CORS allowed methods")
    cors_headers: List[str] = Field(default=["*"], description="CORS allowed headers")
    
    # JWT Authentication Configuration
    jwt_secret_key: str = Field(default="your-super-secret-jwt-key-change-in-production", description="JWT secret key")
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_access_token_expire_minutes: int = Field(default=30, description="Access token expiration in minutes")
    jwt_refresh_token_expire_days: int = Field(default=7, description="Refresh token expiration in days")
    
    # API Key Configuration
    api_key_header: str = Field(default="X-API-Key", description="API key header name")
    api_key_max_length: int = Field(default=64, description="Maximum API key length")
    
    # Redis Configuration for Auth Caching
    redis_token_prefix: str = Field(default="openhub:tokens:", description="Redis token key prefix")
    redis_blacklist_prefix: str = Field(default="openhub:blacklist:", description="Redis blacklist key prefix")
    
    # Security Configuration
    password_min_length: int = Field(default=8, description="Minimum password length")
    max_login_attempts: int = Field(default=5, description="Maximum login attempts before lockout")
    lockout_duration_minutes: int = Field(default=15, description="Account lockout duration")
    
    # Rate Limiting Configuration
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_requests_per_minute: int = Field(default=60, description="Requests per minute limit")
    rate_limit_burst: int = Field(default=10, description="Burst limit for rate limiting")
    
    # Agent Heartbeat Configuration
    heartbeat_timeout_sec: int = Field(default=120, description="Agent heartbeat timeout in seconds")
    heartbeat_check_interval_sec: int = Field(default=30, description="Heartbeat check interval in seconds")
    agent_offline_threshold_sec: int = Field(default=300, description="Consider agent offline after this timeout")
    
    # Hatchet Workflow Configuration
    hatchet_server_url: str = Field(default="http://localhost:8080", description="Hatchet server URL")
    hatchet_api_key: Optional[str] = Field(default=None, description="Hatchet API key")
    hatchet_tenant_id: str = Field(default="default", description="Hatchet tenant ID")
    workflow_default_timeout_sec: int = Field(default=1800, description="Default workflow timeout in seconds")
    workflow_step_default_timeout_sec: int = Field(default=300, description="Default workflow step timeout in seconds")
    workflow_max_retries: int = Field(default=3, description="Maximum workflow retries")

    class Config:
        env_prefix = "AGENTHUB_"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get current settings instance"""
    return settings


def update_settings(**kwargs) -> None:
    """Update settings dynamically"""
    global settings
    for key, value in kwargs.items():
        if hasattr(settings, key):
            setattr(settings, key, value)