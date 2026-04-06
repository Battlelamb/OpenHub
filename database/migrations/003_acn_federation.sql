-- ACN (Agent Collaboration Network) Federation Tables

CREATE TABLE IF NOT EXISTS acn_nodes (
    id TEXT PRIMARY KEY,
    node_name TEXT NOT NULL UNIQUE,
    node_url TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'offline',
    capabilities TEXT DEFAULT '[]',
    metadata TEXT DEFAULT '{}',
    labels TEXT DEFAULT '{}',
    last_heartbeat TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS remote_agent_mappings (
    id TEXT PRIMARY KEY,
    local_agent_id TEXT NOT NULL UNIQUE,
    node_id TEXT NOT NULL,
    remote_agent_name TEXT NOT NULL,
    callback_url TEXT,
    connection_metadata TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (node_id) REFERENCES acn_nodes(id) ON DELETE CASCADE,
    UNIQUE(node_id, remote_agent_name)
);

CREATE INDEX IF NOT EXISTS idx_acn_nodes_status ON acn_nodes(status);
CREATE INDEX IF NOT EXISTS idx_remote_mappings_node ON remote_agent_mappings(node_id);
