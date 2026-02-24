-- Agent Hub Database Schema
-- SQLite database for multi-agent coordination system
-- Version: 0.1.0

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA cache_size = 10000;
PRAGMA temp_store = MEMORY;

-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

-- Insert initial migration
INSERT OR IGNORE INTO schema_migrations (version, description) 
VALUES (1, 'Initial schema creation');

-- =============================================================================
-- AGENT MANAGEMENT TABLES
-- =============================================================================

-- Agents table - Registry of all agents in the system
CREATE TABLE IF NOT EXISTS agents (
    id TEXT PRIMARY KEY,                    -- UUID v4
    agent_name TEXT NOT NULL UNIQUE,        -- Human-readable agent name
    description TEXT,                       -- Optional agent description
    capabilities TEXT NOT NULL,             -- JSON array of capability strings
    status TEXT NOT NULL DEFAULT 'offline', -- online|offline|busy|idle|error
    labels TEXT DEFAULT '{}',               -- JSON object for key-value labels
    metadata TEXT DEFAULT '{}',             -- JSON object for additional metadata
    
    -- Lifecycle timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_heartbeat TIMESTAMP,               -- Last heartbeat from agent
    
    -- Performance metrics
    tasks_completed INTEGER DEFAULT 0,
    tasks_failed INTEGER DEFAULT 0,
    average_task_duration REAL,             -- Average duration in seconds
    
    -- Current state
    current_task TEXT,                      -- Current task ID (FK to tasks.id)
    
    FOREIGN KEY (current_task) REFERENCES tasks(id) ON DELETE SET NULL
);

-- Index for agent queries
CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status);
CREATE INDEX IF NOT EXISTS idx_agents_name ON agents(agent_name);
CREATE INDEX IF NOT EXISTS idx_agents_heartbeat ON agents(last_heartbeat);

-- =============================================================================
-- TASK MANAGEMENT TABLES
-- =============================================================================

-- Tasks table - Central task queue and state management
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,                    -- UUID v4
    title TEXT NOT NULL,                    -- Task title
    description TEXT NOT NULL,              -- Task description
    task_type TEXT NOT NULL DEFAULT 'feature', -- Task type enum
    status TEXT NOT NULL DEFAULT 'queued', -- queued|claimed|running|waiting_approval|completed|failed|dead_letter|cancelled
    priority INTEGER NOT NULL DEFAULT 50,   -- Priority (0-100, lower = higher priority)
    
    -- Requirements and configuration
    required_capabilities TEXT NOT NULL,    -- JSON array of required capabilities
    payload TEXT DEFAULT '{}',              -- JSON object with task-specific data
    labels TEXT DEFAULT '{}',               -- JSON object for key-value labels
    
    -- Assignment and execution
    owner_agent_id TEXT,                    -- Agent currently assigned to task
    claimed_at TIMESTAMP,                   -- When task was claimed
    started_at TIMESTAMP,                   -- When task execution started
    completed_at TIMESTAMP,                 -- When task was completed
    lease_until TIMESTAMP,                  -- Lease expiration time
    
    -- Retry and failure handling
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 2,
    last_error TEXT,                        -- Last error message
    
    -- Deadline and metadata
    deadline_at TIMESTAMP,                  -- Optional task deadline
    idempotency_key TEXT,                   -- For duplicate prevention
    
    -- Results
    result_summary TEXT,                    -- Task completion summary
    output TEXT DEFAULT '{}',               -- JSON object with task output
    artifact_ids TEXT DEFAULT '[]',         -- JSON array of artifact IDs
    
    -- Performance metrics
    duration_seconds REAL,                  -- Total execution duration
    
    -- Lifecycle timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (owner_agent_id) REFERENCES agents(id) ON DELETE SET NULL
);

-- Indexes for task queries
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority);
CREATE INDEX IF NOT EXISTS idx_tasks_owner ON tasks(owner_agent_id);
CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks(created_at);
CREATE INDEX IF NOT EXISTS idx_tasks_deadline ON tasks(deadline_at);
CREATE INDEX IF NOT EXISTS idx_tasks_lease ON tasks(lease_until);
CREATE INDEX IF NOT EXISTS idx_tasks_idempotency ON tasks(idempotency_key);
CREATE INDEX IF NOT EXISTS idx_tasks_type ON tasks(task_type);

-- Task attempts table - Track individual execution attempts
CREATE TABLE IF NOT EXISTS task_attempts (
    id TEXT PRIMARY KEY,                    -- UUID v4
    task_id TEXT NOT NULL,                  -- FK to tasks.id
    agent_id TEXT NOT NULL,                 -- FK to agents.id
    attempt_number INTEGER NOT NULL,        -- 1, 2, 3, etc.
    status TEXT NOT NULL,                   -- running|completed|failed
    
    -- Timing
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds REAL,
    
    -- Error handling
    error_message TEXT,
    
    -- Lifecycle
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE,
    
    UNIQUE(task_id, attempt_number)
);

CREATE INDEX IF NOT EXISTS idx_attempts_task ON task_attempts(task_id);
CREATE INDEX IF NOT EXISTS idx_attempts_agent ON task_attempts(agent_id);

-- =============================================================================
-- EVENT AND AUDIT TABLES
-- =============================================================================

-- Events table - System events and audit trail
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,                    -- UUID v4
    event_type TEXT NOT NULL,               -- Event type enum
    severity TEXT NOT NULL DEFAULT 'info', -- debug|info|warning|error|critical
    title TEXT NOT NULL,                    -- Event title
    description TEXT,                       -- Optional description
    
    -- Relationships
    source_agent_id TEXT,                   -- Agent that triggered event
    related_task_id TEXT,                   -- Related task ID
    related_artifact_id TEXT,               -- Related artifact ID
    
    -- Event data
    data TEXT DEFAULT '{}',                 -- JSON object with event data
    labels TEXT DEFAULT '{}',               -- JSON object for labels
    
    -- Acknowledgment
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_by TEXT,                   -- Agent that acknowledged
    acknowledged_at TIMESTAMP,
    
    -- Lifecycle
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (source_agent_id) REFERENCES agents(id) ON DELETE SET NULL,
    FOREIGN KEY (related_task_id) REFERENCES tasks(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_severity ON events(severity);
CREATE INDEX IF NOT EXISTS idx_events_source ON events(source_agent_id);
CREATE INDEX IF NOT EXISTS idx_events_task ON events(related_task_id);
CREATE INDEX IF NOT EXISTS idx_events_created ON events(created_at);
CREATE INDEX IF NOT EXISTS idx_events_acknowledged ON events(acknowledged);

-- =============================================================================
-- ARTIFACT MANAGEMENT TABLES
-- =============================================================================

-- Artifacts table - File storage metadata
CREATE TABLE IF NOT EXISTS artifacts (
    id TEXT PRIMARY KEY,                    -- UUID v4
    filename TEXT NOT NULL,                 -- Original filename
    content_type TEXT NOT NULL,             -- MIME type
    size_bytes INTEGER NOT NULL,            -- File size in bytes
    checksum TEXT NOT NULL,                 -- SHA-256 checksum
    storage_path TEXT NOT NULL,             -- Relative path in storage
    
    -- Relationships
    created_by_agent TEXT,                  -- Agent that created artifact
    related_task_id TEXT,                   -- Task that generated artifact
    
    -- Metadata
    labels TEXT DEFAULT '{}',               -- JSON object for labels
    metadata TEXT DEFAULT '{}',             -- JSON object for additional metadata
    
    -- Access control
    is_public BOOLEAN DEFAULT FALSE,
    access_permissions TEXT DEFAULT '{}',   -- JSON object with permissions
    
    -- Lifecycle
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,                   -- Optional expiration
    
    FOREIGN KEY (created_by_agent) REFERENCES agents(id) ON DELETE SET NULL,
    FOREIGN KEY (related_task_id) REFERENCES tasks(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_artifacts_filename ON artifacts(filename);
CREATE INDEX IF NOT EXISTS idx_artifacts_creator ON artifacts(created_by_agent);
CREATE INDEX IF NOT EXISTS idx_artifacts_task ON artifacts(related_task_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_created ON artifacts(created_at);
CREATE INDEX IF NOT EXISTS idx_artifacts_expires ON artifacts(expires_at);

-- =============================================================================
-- RESOURCE LOCKING TABLES
-- =============================================================================

-- Resource locks table - Prevent conflicts between agents
CREATE TABLE IF NOT EXISTS resource_locks (
    id TEXT PRIMARY KEY,                    -- UUID v4
    resource_type TEXT NOT NULL,            -- Type of resource (file, directory, etc.)
    resource_id TEXT NOT NULL,              -- Resource identifier
    lock_type TEXT NOT NULL DEFAULT 'exclusive', -- exclusive|shared
    
    -- Ownership
    owner_agent_id TEXT NOT NULL,           -- Agent holding the lock
    owner_task_id TEXT,                     -- Task that requested the lock
    
    -- Lock management
    acquired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,         -- Lock expiration time
    renewed_count INTEGER DEFAULT 0,       -- Number of times renewed
    
    -- Metadata
    purpose TEXT,                           -- Purpose of the lock
    metadata TEXT DEFAULT '{}',             -- JSON object for additional data
    
    -- Lifecycle
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (owner_agent_id) REFERENCES agents(id) ON DELETE CASCADE,
    FOREIGN KEY (owner_task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    
    UNIQUE(resource_type, resource_id, lock_type)
);

CREATE INDEX IF NOT EXISTS idx_locks_resource ON resource_locks(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_locks_owner ON resource_locks(owner_agent_id);
CREATE INDEX IF NOT EXISTS idx_locks_expires ON resource_locks(expires_at);
CREATE INDEX IF NOT EXISTS idx_locks_task ON resource_locks(owner_task_id);

-- =============================================================================
-- COMMUNICATION TABLES
-- =============================================================================

-- Threads table - Communication threads between agents
CREATE TABLE IF NOT EXISTS threads (
    id TEXT PRIMARY KEY,                    -- UUID v4
    title TEXT NOT NULL,                    -- Thread title
    thread_type TEXT NOT NULL DEFAULT 'discussion', -- discussion|notification|coordination
    status TEXT NOT NULL DEFAULT 'active', -- active|archived|closed
    
    -- Participants
    participants TEXT NOT NULL,             -- JSON array of agent IDs
    created_by_agent TEXT NOT NULL,         -- Agent that created thread
    
    -- Metadata
    labels TEXT DEFAULT '{}',               -- JSON object for labels
    metadata TEXT DEFAULT '{}',             -- JSON object for additional data
    
    -- Lifecycle
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (created_by_agent) REFERENCES agents(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_threads_type ON threads(thread_type);
CREATE INDEX IF NOT EXISTS idx_threads_status ON threads(status);
CREATE INDEX IF NOT EXISTS idx_threads_creator ON threads(created_by_agent);
CREATE INDEX IF NOT EXISTS idx_threads_activity ON threads(last_activity_at);

-- Messages table - Individual messages within threads
CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,                    -- UUID v4
    thread_id TEXT NOT NULL,                -- FK to threads.id
    sender_agent_id TEXT NOT NULL,          -- FK to agents.id
    message_type TEXT NOT NULL DEFAULT 'text', -- text|file|system|command
    content TEXT NOT NULL,                  -- Message content
    
    -- Attachments
    attachments TEXT DEFAULT '[]',          -- JSON array of artifact IDs
    
    -- Message metadata
    reply_to_message_id TEXT,               -- FK to messages.id for replies
    is_system_message BOOLEAN DEFAULT FALSE,
    priority TEXT DEFAULT 'normal',         -- low|normal|high|urgent
    
    -- Metadata
    metadata TEXT DEFAULT '{}',             -- JSON object for additional data
    
    -- Lifecycle
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (thread_id) REFERENCES threads(id) ON DELETE CASCADE,
    FOREIGN KEY (sender_agent_id) REFERENCES agents(id) ON DELETE CASCADE,
    FOREIGN KEY (reply_to_message_id) REFERENCES messages(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_thread ON messages(thread_id);
CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender_agent_id);
CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at);
CREATE INDEX IF NOT EXISTS idx_messages_reply ON messages(reply_to_message_id);

-- =============================================================================
-- APPROVAL WORKFLOW TABLES
-- =============================================================================

-- Approvals table - Human-in-the-loop workflow
CREATE TABLE IF NOT EXISTS approvals (
    id TEXT PRIMARY KEY,                    -- UUID v4
    task_id TEXT NOT NULL,                  -- FK to tasks.id
    approval_type TEXT NOT NULL,            -- manual|automatic|conditional
    status TEXT NOT NULL DEFAULT 'pending', -- pending|approved|rejected|expired
    
    -- Request details
    requested_by_agent TEXT NOT NULL,       -- Agent requesting approval
    approval_reason TEXT NOT NULL,          -- Reason for approval request
    approval_context TEXT DEFAULT '{}',     -- JSON context data
    
    -- Response details
    approved_by TEXT,                       -- Who approved/rejected
    approval_response TEXT,                 -- Response message
    approved_at TIMESTAMP,
    
    -- Configuration
    expires_at TIMESTAMP,                   -- Approval expiration
    auto_approve_after TIMESTAMP,           -- Auto-approve deadline
    
    -- Metadata
    metadata TEXT DEFAULT '{}',             -- JSON object for additional data
    
    -- Lifecycle
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (requested_by_agent) REFERENCES agents(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_approvals_task ON approvals(task_id);
CREATE INDEX IF NOT EXISTS idx_approvals_status ON approvals(status);
CREATE INDEX IF NOT EXISTS idx_approvals_requester ON approvals(requested_by_agent);
CREATE INDEX IF NOT EXISTS idx_approvals_expires ON approvals(expires_at);

-- =============================================================================
-- SYSTEM CONFIGURATION TABLES
-- =============================================================================

-- System settings table
CREATE TABLE IF NOT EXISTS system_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    value_type TEXT NOT NULL DEFAULT 'string', -- string|integer|float|boolean|json
    description TEXT,
    is_sensitive BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default settings
INSERT OR IGNORE INTO system_settings (key, value, value_type, description) VALUES
('max_agents', '100', 'integer', 'Maximum number of concurrent agents'),
('max_concurrent_tasks', '50', 'integer', 'Maximum concurrent tasks'),
('task_lease_ttl_sec', '300', 'integer', 'Task lease TTL in seconds'),
('artifact_retention_days', '30', 'integer', 'Artifact retention period'),
('event_retention_days', '90', 'integer', 'Event retention period'),
('lock_max_duration_sec', '3600', 'integer', 'Maximum lock duration in seconds'),
('heartbeat_timeout_sec', '120', 'integer', 'Agent heartbeat timeout'),
('auto_cleanup_enabled', 'true', 'boolean', 'Enable automatic cleanup jobs');

-- =============================================================================
-- VIEWS FOR COMMON QUERIES
-- =============================================================================

-- Active agents view
CREATE VIEW IF NOT EXISTS active_agents AS
SELECT 
    a.*,
    t.title as current_task_title,
    t.status as current_task_status
FROM agents a
LEFT JOIN tasks t ON a.current_task = t.id
WHERE a.status IN ('online', 'busy', 'idle');

-- Pending tasks view
CREATE VIEW IF NOT EXISTS pending_tasks AS
SELECT 
    t.*,
    a.agent_name as owner_agent_name
FROM tasks t
LEFT JOIN agents a ON t.owner_agent_id = a.id
WHERE t.status IN ('queued', 'claimed', 'running')
ORDER BY t.priority ASC, t.created_at ASC;

-- Recent events view
CREATE VIEW IF NOT EXISTS recent_events AS
SELECT 
    e.*,
    a.agent_name as source_agent_name,
    t.title as related_task_title
FROM events e
LEFT JOIN agents a ON e.source_agent_id = a.id
LEFT JOIN tasks t ON e.related_task_id = t.id
WHERE e.created_at >= datetime('now', '-24 hours')
ORDER BY e.created_at DESC;

-- Task performance view
CREATE VIEW IF NOT EXISTS task_performance AS
SELECT 
    task_type,
    COUNT(*) as total_tasks,
    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_tasks,
    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_tasks,
    AVG(duration_seconds) as avg_duration,
    MIN(duration_seconds) as min_duration,
    MAX(duration_seconds) as max_duration
FROM tasks 
WHERE status IN ('completed', 'failed')
GROUP BY task_type;

-- =============================================================================
-- TRIGGERS FOR MAINTENANCE
-- =============================================================================

-- Update timestamps trigger for agents
CREATE TRIGGER IF NOT EXISTS update_agents_timestamp
    AFTER UPDATE ON agents
    FOR EACH ROW
BEGIN
    UPDATE agents SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Update timestamps trigger for tasks
CREATE TRIGGER IF NOT EXISTS update_tasks_timestamp
    AFTER UPDATE ON tasks
    FOR EACH ROW
BEGIN
    UPDATE tasks SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Update timestamps trigger for events
CREATE TRIGGER IF NOT EXISTS update_events_timestamp
    AFTER UPDATE ON events
    FOR EACH ROW
BEGIN
    UPDATE events SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Update thread activity trigger
CREATE TRIGGER IF NOT EXISTS update_thread_activity
    AFTER INSERT ON messages
    FOR EACH ROW
BEGIN
    UPDATE threads SET 
        last_activity_at = CURRENT_TIMESTAMP,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.thread_id;
END;