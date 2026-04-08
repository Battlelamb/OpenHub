"""Initial schema - baseline for all 16 tables.

Revision ID: 0001
Revises:
Create Date: 2026-04-08
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Using CREATE TABLE IF NOT EXISTS so this migration is safe to run
    # against an existing database that already has these tables.
    # New deployments will create all tables fresh.
    # Existing deployments will be stamped at this revision via: alembic stamp 0001
    op.execute("""
        CREATE TABLE IF NOT EXISTS agents (
            id TEXT PRIMARY KEY, agent_name TEXT NOT NULL UNIQUE, description TEXT,
            capabilities TEXT DEFAULT '[]', status TEXT DEFAULT 'offline',
            last_heartbeat TIMESTAMP, current_task TEXT,
            labels TEXT DEFAULT '{}', metadata TEXT DEFAULT '{}',
            tasks_completed INTEGER DEFAULT 0, tasks_failed INTEGER DEFAULT 0,
            average_task_duration REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT,
            task_type TEXT NOT NULL DEFAULT 'feature', priority INTEGER DEFAULT 50,
            status TEXT NOT NULL DEFAULT 'queued',
            required_capabilities TEXT DEFAULT '[]', owner_agent_id TEXT,
            claimed_at TIMESTAMP, started_at TIMESTAMP, completed_at TIMESTAMP,
            lease_until TIMESTAMP, retry_count INTEGER DEFAULT 0,
            max_retries INTEGER DEFAULT 3, last_error TEXT,
            deadline_at TIMESTAMP, idempotency_key TEXT,
            labels TEXT DEFAULT '{}', metadata TEXT DEFAULT '{}',
            payload TEXT DEFAULT '{}', result_summary TEXT,
            output TEXT DEFAULT '{}', artifact_ids TEXT DEFAULT '[]',
            duration_seconds REAL, created_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS acn_nodes (
            id TEXT PRIMARY KEY, node_name TEXT NOT NULL UNIQUE, node_url TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'offline', capabilities TEXT DEFAULT '[]',
            metadata TEXT DEFAULT '{}', labels TEXT DEFAULT '{}',
            last_heartbeat TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS remote_agent_mappings (
            id TEXT PRIMARY KEY, local_agent_id TEXT NOT NULL UNIQUE,
            node_id TEXT NOT NULL, remote_agent_name TEXT NOT NULL,
            callback_url TEXT, connection_metadata TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, key_type TEXT NOT NULL,
            key_hash TEXT NOT NULL, salt TEXT NOT NULL, scopes TEXT DEFAULT '[]',
            description TEXT, expires_at TIMESTAMP, created_by TEXT,
            metadata TEXT DEFAULT '{}', is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used_at TIMESTAMP, revoked_at TIMESTAMP, revoked_by TEXT)
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS pending_applications (
            id TEXT PRIMARY KEY, agent_name TEXT NOT NULL,
            data TEXT NOT NULL, client_ip TEXT,
            status TEXT DEFAULT 'pending',
            api_key_value TEXT,
            reviewed_by TEXT, reviewed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            from_agent_id TEXT NOT NULL,
            to_agent_id TEXT,
            thread_id TEXT,
            message_type TEXT DEFAULT 'text',
            content TEXT NOT NULL,
            metadata TEXT DEFAULT '{}',
            read_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS threads (
            id TEXT PRIMARY KEY,
            title TEXT,
            thread_type TEXT DEFAULT 'conversation',
            task_id TEXT,
            participants TEXT DEFAULT '[]',
            status TEXT DEFAULT 'open',
            created_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS shared_memory (
            id TEXT PRIMARY KEY,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            value_type TEXT DEFAULT 'text',
            tags TEXT DEFAULT '[]',
            created_by TEXT,
            access_level TEXT DEFAULT 'public',
            ttl_seconds INTEGER,
            expires_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS workflows (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            steps TEXT NOT NULL,
            status TEXT DEFAULT 'created',
            current_step INTEGER DEFAULT 0,
            results TEXT DEFAULT '{}',
            created_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS artifacts (
            id TEXT PRIMARY KEY, filename TEXT NOT NULL, content_type TEXT,
            content TEXT, encoding TEXT DEFAULT 'text', size_bytes INTEGER,
            task_id TEXT, description TEXT, tags TEXT DEFAULT '[]',
            uploaded_by TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS resource_locks (
            id TEXT PRIMARY KEY, resource TEXT NOT NULL, locked_by TEXT,
            reason TEXT, ttl_seconds INTEGER, expires_at TIMESTAMP,
            released_at TIMESTAMP, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS trace_events (
            id TEXT PRIMARY KEY, trace_id TEXT NOT NULL, agent_id TEXT,
            event_type TEXT, name TEXT NOT NULL, data TEXT DEFAULT '{}',
            task_id TEXT, duration_ms REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS cost_tracking (
            id TEXT PRIMARY KEY, agent_id TEXT, task_id TEXT,
            model TEXT NOT NULL, input_tokens INTEGER, output_tokens INTEGER,
            cost_usd REAL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS shared_tools (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT,
            tool_type TEXT DEFAULT 'mcp', endpoint TEXT,
            config TEXT DEFAULT '{}', tags TEXT DEFAULT '[]',
            registered_by TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS agent_templates (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT,
            capabilities TEXT DEFAULT '[]', skills TEXT DEFAULT '[]',
            mcp_servers TEXT DEFAULT '[]', model TEXT, platform TEXT,
            config TEXT DEFAULT '{}', created_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
    """)


def downgrade() -> None:
    for table in [
        "agent_templates", "shared_tools", "cost_tracking", "trace_events",
        "resource_locks", "artifacts", "workflows", "shared_memory",
        "threads", "messages", "pending_applications", "api_keys",
        "remote_agent_mappings", "acn_nodes", "tasks", "agents",
    ]:
        op.execute(f"DROP TABLE IF EXISTS {table}")
