-- Migration 002: API Keys table
-- Version: 0.1.0
-- Description: Add API key management system

-- API Keys table for service authentication
CREATE TABLE IF NOT EXISTS api_keys (
    id TEXT PRIMARY KEY,                    -- UUID v4
    name TEXT NOT NULL,                     -- Human-readable key name
    key_type TEXT NOT NULL,                 -- agent|service|admin|readonly|webhook
    key_hash TEXT NOT NULL,                 -- SHA-256 hash of API key
    salt TEXT NOT NULL,                     -- Salt for hashing
    scopes TEXT NOT NULL,                   -- JSON array of allowed scopes
    
    -- Metadata
    description TEXT,                       -- Key description
    created_by TEXT,                        -- Who created the key
    metadata TEXT DEFAULT '{}',             -- JSON object for additional data
    
    -- Lifecycle management
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,                   -- Optional expiration
    last_used_at TIMESTAMP,                 -- Last usage timestamp
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,         -- Whether key is active
    revoked_at TIMESTAMP,                   -- When key was revoked
    revoked_by TEXT,                        -- Who revoked the key
    
    -- Constraints
    FOREIGN KEY (created_by) REFERENCES agents(id) ON DELETE SET NULL,
    FOREIGN KEY (revoked_by) REFERENCES agents(id) ON DELETE SET NULL
);

-- Indexes for API keys
CREATE INDEX IF NOT EXISTS idx_api_keys_active ON api_keys(is_active);
CREATE INDEX IF NOT EXISTS idx_api_keys_type ON api_keys(key_type);
CREATE INDEX IF NOT EXISTS idx_api_keys_creator ON api_keys(created_by);
CREATE INDEX IF NOT EXISTS idx_api_keys_expires ON api_keys(expires_at);
CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash); -- For validation lookup

-- Triggers for API keys
CREATE TRIGGER IF NOT EXISTS update_api_keys_timestamp
    AFTER UPDATE ON api_keys
    FOR EACH ROW
BEGIN
    UPDATE api_keys SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Add to schema migrations
INSERT INTO schema_migrations (version, description) 
VALUES (2, 'API Keys management system');