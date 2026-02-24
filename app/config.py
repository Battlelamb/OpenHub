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