-- Migration 004: Durable task evidence
-- Version: 0.4.0
-- Description: Create private/internal task_evidence table for logs, commands, artifacts, reviews, and quality gates

CREATE TABLE IF NOT EXISTS task_evidence (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    evidence_type TEXT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT,
    content TEXT DEFAULT '{}',
    artifact_ids TEXT DEFAULT '[]',
    outcome TEXT DEFAULT 'unknown',
    source_agent_id TEXT,
    labels TEXT DEFAULT '{}',
    metadata TEXT DEFAULT '{}',
    occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_task_evidence_task ON task_evidence(task_id);
CREATE INDEX IF NOT EXISTS idx_task_evidence_task_occurred ON task_evidence(task_id, occurred_at);
CREATE INDEX IF NOT EXISTS idx_task_evidence_type ON task_evidence(evidence_type);
CREATE INDEX IF NOT EXISTS idx_task_evidence_source ON task_evidence(source_agent_id);
