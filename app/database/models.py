"""
SQLAlchemy ORM models for all 16 OpenHub tables.
These models are used by Alembic for migration autogenerate.
The existing raw SQL Database class in connection.py remains unchanged.
"""
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, DateTime,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class AgentModel(Base):
    __tablename__ = "agents"
    id = Column(String, primary_key=True)
    agent_name = Column(String, nullable=False, unique=True)
    description = Column(Text)
    capabilities = Column(Text, default="[]")
    status = Column(String, default="offline")
    last_heartbeat = Column(DateTime)
    current_task = Column(String)
    labels = Column(Text, default="{}")
    metadata_ = Column("metadata", Text, default="{}")
    tasks_completed = Column(Integer, default=0)
    tasks_failed = Column(Integer, default=0)
    average_task_duration = Column(Float)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)


class TaskModel(Base):
    __tablename__ = "tasks"
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    task_type = Column(String, default="feature")
    priority = Column(Integer, default=50)
    status = Column(String, default="queued", nullable=False)
    required_capabilities = Column(Text, default="[]")
    owner_agent_id = Column(String)
    claimed_at = Column(DateTime)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    lease_until = Column(DateTime)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    last_error = Column(Text)
    deadline_at = Column(DateTime)
    idempotency_key = Column(String)
    labels = Column(Text, default="{}")
    metadata_ = Column("metadata", Text, default="{}")
    payload = Column(Text, default="{}")
    result_summary = Column(Text)
    output = Column(Text, default="{}")
    artifact_ids = Column(Text, default="[]")
    duration_seconds = Column(Float)
    created_by = Column(String)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)


class AcnNodeModel(Base):
    __tablename__ = "acn_nodes"
    id = Column(String, primary_key=True)
    node_name = Column(String, nullable=False, unique=True)
    node_url = Column(String, nullable=False)
    status = Column(String, default="offline", nullable=False)
    capabilities = Column(Text, default="[]")
    metadata_ = Column("metadata", Text, default="{}")
    labels = Column(Text, default="{}")
    last_heartbeat = Column(DateTime)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)


class RemoteAgentMappingModel(Base):
    __tablename__ = "remote_agent_mappings"
    id = Column(String, primary_key=True)
    local_agent_id = Column(String, nullable=False, unique=True)
    node_id = Column(String, nullable=False)
    remote_agent_name = Column(String, nullable=False)
    callback_url = Column(String)
    connection_metadata = Column(Text, default="{}")
    created_at = Column(DateTime)
    updated_at = Column(DateTime)


class ApiKeyModel(Base):
    __tablename__ = "api_keys"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    key_type = Column(String, nullable=False)
    key_hash = Column(String, nullable=False)
    salt = Column(String, nullable=False)
    scopes = Column(Text, default="[]")
    description = Column(Text)
    expires_at = Column(DateTime)
    created_by = Column(String)
    metadata_ = Column("metadata", Text, default="{}")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    last_used_at = Column(DateTime)
    revoked_at = Column(DateTime)
    revoked_by = Column(String)


class PendingApplicationModel(Base):
    __tablename__ = "pending_applications"
    id = Column(String, primary_key=True)
    agent_name = Column(String, nullable=False)
    data = Column(Text, nullable=False)
    client_ip = Column(String)
    status = Column(String, default="pending")
    api_key_value = Column(Text)
    reviewed_by = Column(String)
    reviewed_at = Column(DateTime)
    created_at = Column(DateTime)


class MessageModel(Base):
    __tablename__ = "messages"
    id = Column(String, primary_key=True)
    from_agent_id = Column(String, nullable=False)
    to_agent_id = Column(String)
    thread_id = Column(String)
    message_type = Column(String, default="text")
    content = Column(Text, nullable=False)
    metadata_ = Column("metadata", Text, default="{}")
    read_at = Column(DateTime)
    created_at = Column(DateTime)


class ThreadModel(Base):
    __tablename__ = "threads"
    id = Column(String, primary_key=True)
    title = Column(Text)
    thread_type = Column(String, default="conversation")
    task_id = Column(String)
    participants = Column(Text, default="[]")
    status = Column(String, default="open")
    created_by = Column(String)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)


class SharedMemoryModel(Base):
    __tablename__ = "shared_memory"
    id = Column(String, primary_key=True)
    key = Column(String, nullable=False)
    value = Column(Text, nullable=False)
    value_type = Column(String, default="text")
    tags = Column(Text, default="[]")
    created_by = Column(String)
    access_level = Column(String, default="public")
    ttl_seconds = Column(Integer)
    expires_at = Column(DateTime)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)


class WorkflowModel(Base):
    __tablename__ = "workflows"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    steps = Column(Text, nullable=False)
    status = Column(String, default="created")
    current_step = Column(Integer, default=0)
    results = Column(Text, default="{}")
    created_by = Column(String)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)


class ArtifactModel(Base):
    __tablename__ = "artifacts"
    id = Column(String, primary_key=True)
    filename = Column(String, nullable=False)
    content_type = Column(String)
    content = Column(Text)
    encoding = Column(String, default="text")
    size_bytes = Column(Integer)
    task_id = Column(String)
    description = Column(Text)
    tags = Column(Text, default="[]")
    uploaded_by = Column(String)
    created_at = Column(DateTime)


class ResourceLockModel(Base):
    __tablename__ = "resource_locks"
    id = Column(String, primary_key=True)
    resource = Column(String, nullable=False)
    locked_by = Column(String)
    reason = Column(Text)
    ttl_seconds = Column(Integer)
    expires_at = Column(DateTime)
    released_at = Column(DateTime)
    created_at = Column(DateTime)


class TraceEventModel(Base):
    __tablename__ = "trace_events"
    id = Column(String, primary_key=True)
    trace_id = Column(String, nullable=False)
    agent_id = Column(String)
    event_type = Column(String)
    name = Column(String, nullable=False)
    data = Column(Text, default="{}")
    task_id = Column(String)
    duration_ms = Column(Float)
    created_at = Column(DateTime)


class CostTrackingModel(Base):
    __tablename__ = "cost_tracking"
    id = Column(String, primary_key=True)
    agent_id = Column(String)
    task_id = Column(String)
    model = Column(String, nullable=False)
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    cost_usd = Column(Float)
    created_at = Column(DateTime)


class SharedToolModel(Base):
    __tablename__ = "shared_tools"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    tool_type = Column(String, default="mcp")
    endpoint = Column(String)
    config = Column(Text, default="{}")
    tags = Column(Text, default="[]")
    registered_by = Column(String)
    created_at = Column(DateTime)


class AgentTemplateModel(Base):
    __tablename__ = "agent_templates"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    capabilities = Column(Text, default="[]")
    skills = Column(Text, default="[]")
    mcp_servers = Column(Text, default="[]")
    model = Column(String)
    platform = Column(String)
    config = Column(Text, default="{}")
    created_by = Column(String)
    created_at = Column(DateTime)
