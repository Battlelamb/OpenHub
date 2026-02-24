-- Migration 001: Initial database schema
-- Version: 0.1.0
-- Description: Create all core tables for Agent Hub

-- Enable SQLite optimizations
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA cache_size = 10000;
PRAGMA temp_store = MEMORY;

-- Schema version tracking
CREATE TABLE schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT NOT NULL
);

INSERT INTO schema_migrations (version, description) 
VALUES (1, 'Initial schema - agents, tasks, events, artifacts, locks, communication');

-- =============================================================================
-- CORE TABLES
-- =============================================================================

-- Agents registry
CREATE TABLE agents (
    id TEXT PRIMARY KEY,
    agent_name TEXT NOT NULL UNIQUE,
    description TEXT,
    capabilities TEXT NOT NULL, -- JSON array
    status TEXT NOT NULL DEFAULT 'offline',
    labels TEXT DEFAULT '{}', -- JSON object
    metadata TEXT DEFAULT '{}', -- JSON object
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_heartbeat TIMESTAMP,
    tasks_completed INTEGER DEFAULT 0,
    tasks_failed INTEGER DEFAULT 0,
    average_task_duration REAL,
    current_task TEXT,
    
    FOREIGN KEY (current_task) REFERENCES tasks(id) ON DELETE SET NULL
);

-- Tasks management
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    task_type TEXT NOT NULL DEFAULT 'feature',
    status TEXT NOT NULL DEFAULT 'queued',
    priority INTEGER NOT NULL DEFAULT 50,
    required_capabilities TEXT NOT NULL, -- JSON array
    payload TEXT DEFAULT '{}', -- JSON object
    labels TEXT DEFAULT '{}', -- JSON object
    owner_agent_id TEXT,
    claimed_at TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    lease_until TIMESTAMP,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 2,
    last_error TEXT,
    deadline_at TIMESTAMP,
    idempotency_key TEXT,
    result_summary TEXT,
    output TEXT DEFAULT '{}', -- JSON object
    artifact_ids TEXT DEFAULT '[]', -- JSON array
    duration_seconds REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (owner_agent_id) REFERENCES agents(id) ON DELETE SET NULL
);

-- Task execution attempts
CREATE TABLE task_attempts (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    attempt_number INTEGER NOT NULL,
    status TEXT NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds REAL,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE,
    UNIQUE(task_id, attempt_number)
);

-- System events and audit trail
CREATE TABLE events (
    id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'info',
    title TEXT NOT NULL,
    description TEXT,
    source_agent_id TEXT,
    related_task_id TEXT,
    related_artifact_id TEXT,
    data TEXT DEFAULT '{}', -- JSON object
    labels TEXT DEFAULT '{}', -- JSON object
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_by TEXT,
    acknowledged_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (source_agent_id) REFERENCES agents(id) ON DELETE SET NULL,
    FOREIGN KEY (related_task_id) REFERENCES tasks(id) ON DELETE SET NULL
);

-- File artifacts metadata
CREATE TABLE artifacts (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    content_type TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    checksum TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    created_by_agent TEXT,
    related_task_id TEXT,
    labels TEXT DEFAULT '{}', -- JSON object
    metadata TEXT DEFAULT '{}', -- JSON object
    is_public BOOLEAN DEFAULT FALSE,
    access_permissions TEXT DEFAULT '{}', -- JSON object
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    
    FOREIGN KEY (created_by_agent) REFERENCES agents(id) ON DELETE SET NULL,
    FOREIGN KEY (related_task_id) REFERENCES tasks(id) ON DELETE SET NULL
);

-- Resource locking system
CREATE TABLE resource_locks (
    id TEXT PRIMARY KEY,
    resource_type TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    lock_type TEXT NOT NULL DEFAULT 'exclusive',
    owner_agent_id TEXT NOT NULL,
    owner_task_id TEXT,
    acquired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    renewed_count INTEGER DEFAULT 0,
    purpose TEXT,
    metadata TEXT DEFAULT '{}', -- JSON object
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (owner_agent_id) REFERENCES agents(id) ON DELETE CASCADE,
    FOREIGN KEY (owner_task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    UNIQUE(resource_type, resource_id, lock_type)
);

-- Communication threads
CREATE TABLE threads (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    thread_type TEXT NOT NULL DEFAULT 'discussion',
    status TEXT NOT NULL DEFAULT 'active',
    participants TEXT NOT NULL, -- JSON array of agent IDs
    created_by_agent TEXT NOT NULL,
    labels TEXT DEFAULT '{}', -- JSON object
    metadata TEXT DEFAULT '{}', -- JSON object
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (created_by_agent) REFERENCES agents(id) ON DELETE CASCADE
);

-- Messages within threads
CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL,
    sender_agent_id TEXT NOT NULL,
    message_type TEXT NOT NULL DEFAULT 'text',
    content TEXT NOT NULL,
    attachments TEXT DEFAULT '[]', -- JSON array of artifact IDs
    reply_to_message_id TEXT,
    is_system_message BOOLEAN DEFAULT FALSE,
    priority TEXT DEFAULT 'normal',
    metadata TEXT DEFAULT '{}', -- JSON object
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (thread_id) REFERENCES threads(id) ON DELETE CASCADE,
    FOREIGN KEY (sender_agent_id) REFERENCES agents(id) ON DELETE CASCADE,
    FOREIGN KEY (reply_to_message_id) REFERENCES messages(id) ON DELETE SET NULL
);

-- Approval workflow
CREATE TABLE approvals (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    approval_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    requested_by_agent TEXT NOT NULL,
    approval_reason TEXT NOT NULL,
    approval_context TEXT DEFAULT '{}', -- JSON object
    approved_by TEXT,
    approval_response TEXT,
    approved_at TIMESTAMP,
    expires_at TIMESTAMP,
    auto_approve_after TIMESTAMP,
    metadata TEXT DEFAULT '{}', -- JSON object
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (requested_by_agent) REFERENCES agents(id) ON DELETE CASCADE
);

-- System configuration
CREATE TABLE system_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    value_type TEXT NOT NULL DEFAULT 'string',
    description TEXT,
    is_sensitive BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- INDEXES
-- =============================================================================

-- Agent indexes
CREATE INDEX idx_agents_status ON agents(status);
CREATE INDEX idx_agents_name ON agents(agent_name);
CREATE INDEX idx_agents_heartbeat ON agents(last_heartbeat);

-- Task indexes
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_priority ON tasks(priority);
CREATE INDEX idx_tasks_owner ON tasks(owner_agent_id);
CREATE INDEX idx_tasks_created ON tasks(created_at);
CREATE INDEX idx_tasks_deadline ON tasks(deadline_at);
CREATE INDEX idx_tasks_lease ON tasks(lease_until);
CREATE INDEX idx_tasks_idempotency ON tasks(idempotency_key);
CREATE INDEX idx_tasks_type ON tasks(task_type);

-- Task attempt indexes
CREATE INDEX idx_attempts_task ON task_attempts(task_id);
CREATE INDEX idx_attempts_agent ON task_attempts(agent_id);

-- Event indexes
CREATE INDEX idx_events_type ON events(event_type);
CREATE INDEX idx_events_severity ON events(severity);
CREATE INDEX idx_events_source ON events(source_agent_id);
CREATE INDEX idx_events_task ON events(related_task_id);
CREATE INDEX idx_events_created ON events(created_at);
CREATE INDEX idx_events_acknowledged ON events(acknowledged);

-- Artifact indexes
CREATE INDEX idx_artifacts_filename ON artifacts(filename);
CREATE INDEX idx_artifacts_creator ON artifacts(created_by_agent);
CREATE INDEX idx_artifacts_task ON artifacts(related_task_id);
CREATE INDEX idx_artifacts_created ON artifacts(created_at);
CREATE INDEX idx_artifacts_expires ON artifacts(expires_at);

-- Lock indexes
CREATE INDEX idx_locks_resource ON resource_locks(resource_type, resource_id);
CREATE INDEX idx_locks_owner ON resource_locks(owner_agent_id);
CREATE INDEX idx_locks_expires ON resource_locks(expires_at);
CREATE INDEX idx_locks_task ON resource_locks(owner_task_id);

-- Communication indexes
CREATE INDEX idx_threads_type ON threads(thread_type);
CREATE INDEX idx_threads_status ON threads(status);
CREATE INDEX idx_threads_creator ON threads(created_by_agent);
CREATE INDEX idx_threads_activity ON threads(last_activity_at);

CREATE INDEX idx_messages_thread ON messages(thread_id);
CREATE INDEX idx_messages_sender ON messages(sender_agent_id);
CREATE INDEX idx_messages_created ON messages(created_at);
CREATE INDEX idx_messages_reply ON messages(reply_to_message_id);

-- Approval indexes
CREATE INDEX idx_approvals_task ON approvals(task_id);
CREATE INDEX idx_approvals_status ON approvals(status);
CREATE INDEX idx_approvals_requester ON approvals(requested_by_agent);
CREATE INDEX idx_approvals_expires ON approvals(expires_at);

-- =============================================================================
-- DEFAULT DATA
-- =============================================================================

INSERT INTO system_settings (key, value, value_type, description) VALUES
('max_agents', '100', 'integer', 'Maximum number of concurrent agents'),
('max_concurrent_tasks', '50', 'integer', 'Maximum concurrent tasks'),
('task_lease_ttl_sec', '300', 'integer', 'Task lease TTL in seconds'),
('artifact_retention_days', '30', 'integer', 'Artifact retention period'),
('event_retention_days', '90', 'integer', 'Event retention period'),
('lock_max_duration_sec', '3600', 'integer', 'Maximum lock duration in seconds'),
('heartbeat_timeout_sec', '120', 'integer', 'Agent heartbeat timeout'),
('auto_cleanup_enabled', 'true', 'boolean', 'Enable automatic cleanup jobs');

-- =============================================================================
-- TRIGGERS
-- =============================================================================

CREATE TRIGGER update_agents_timestamp
    AFTER UPDATE ON agents
    FOR EACH ROW
BEGIN
    UPDATE agents SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER update_tasks_timestamp
    AFTER UPDATE ON tasks
    FOR EACH ROW
BEGIN
    UPDATE tasks SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER update_events_timestamp
    AFTER UPDATE ON events
    FOR EACH ROW
BEGIN
    UPDATE events SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER update_thread_activity
    AFTER INSERT ON messages
    FOR EACH ROW
BEGIN
    UPDATE threads SET 
        last_activity_at = CURRENT_TIMESTAMP,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.thread_id;
END;