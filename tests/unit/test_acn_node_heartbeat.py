from datetime import datetime, timedelta, timezone

from app.database.connection import Database
from app.services.remote_agent_service import RemoteAgentService


def _create_acn_tables(db: Database) -> None:
    db.execute(
        """
        CREATE TABLE agents (
            id TEXT PRIMARY KEY,
            agent_name TEXT NOT NULL UNIQUE,
            description TEXT,
            capabilities TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'offline',
            labels TEXT DEFAULT '{}',
            metadata TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_heartbeat TIMESTAMP,
            tasks_completed INTEGER DEFAULT 0,
            tasks_failed INTEGER DEFAULT 0,
            average_task_duration REAL,
            current_task TEXT
        )
        """
    )
    db.execute(
        """
        CREATE TABLE acn_nodes (
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
        )
        """
    )
    db.execute(
        """
        CREATE TABLE remote_agent_mappings (
            id TEXT PRIMARY KEY,
            local_agent_id TEXT NOT NULL UNIQUE,
            node_id TEXT NOT NULL,
            remote_agent_name TEXT NOT NULL,
            callback_url TEXT,
            connection_metadata TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def _make_db(tmp_path) -> Database:
    db = Database(str(tmp_path / "openhub-test.db"))
    # Test isolation: local development may have Turso credentials in .env,
    # but these regression tests must use an empty disposable SQLite DB.
    db._use_turso = False
    db.db_path.parent.mkdir(parents=True, exist_ok=True)
    _create_acn_tables(db)
    return db


def _insert_node(db: Database, node_id: str, node_name: str, heartbeat: str, status: str = "online") -> None:
    db.execute(
        """
        INSERT INTO acn_nodes (
            id, node_name, node_url, status, capabilities, metadata, labels,
            last_heartbeat, created_at, updated_at
        ) VALUES (
            :node_id, :node_name, 'http://localhost:18789', :status,
            '[]', '{}', '{}', :heartbeat, :heartbeat, :heartbeat
        )
        """,
        {"node_id": node_id, "node_name": node_name, "status": status, "heartbeat": heartbeat},
    )


def _insert_mapped_agent(db: Database, agent_id: str, agent_name: str, node_id: str, stale_heartbeat: str) -> None:
    db.execute(
        """
        INSERT INTO agents (
            id, agent_name, capabilities, status, labels, metadata,
            created_at, updated_at, last_heartbeat, tasks_completed, tasks_failed
        ) VALUES (
            :agent_id, :agent_name, '["code_edit"]', 'offline', '{}', '{}',
            :stale, :stale, :stale, 0, 0
        )
        """,
        {"agent_id": agent_id, "agent_name": agent_name, "stale": stale_heartbeat},
    )
    db.execute(
        """
        INSERT INTO remote_agent_mappings (
            id, local_agent_id, node_id, remote_agent_name, connection_metadata,
            created_at, updated_at
        ) VALUES (
            :mapping_id, :agent_id, :node_id, :agent_name, '{}', :stale, :stale
        )
        """,
        {
            "mapping_id": f"mapping-{agent_id}",
            "agent_id": agent_id,
            "node_id": node_id,
            "agent_name": agent_name,
            "stale": stale_heartbeat,
        },
    )


def test_node_heartbeat_does_not_mark_mapped_remote_agents_online(tmp_path):
    db = _make_db(tmp_path)

    stale_heartbeat = "2026-04-07T13:58:35+00:00"
    _insert_node(db, "node-1", "brunhilde-vps", stale_heartbeat, status="offline")
    _insert_mapped_agent(db, "agent-1", "claude-code", "node-1", stale_heartbeat)

    service = RemoteAgentService(db)

    assert service.heartbeat_node("node-1") is True

    node = db.fetch_one("SELECT status, last_heartbeat FROM acn_nodes WHERE id = 'node-1'")
    agent = db.fetch_one("SELECT status, last_heartbeat FROM agents WHERE id = 'agent-1'")

    try:
        assert node["status"] == "online"
        assert node["last_heartbeat"] != stale_heartbeat
        assert agent["status"] == "offline"
        assert agent["last_heartbeat"] == stale_heartbeat
    finally:
        db.close_all_connections()


def test_node_heartbeat_refreshes_only_the_authenticated_mapped_agent(tmp_path):
    db = _make_db(tmp_path)

    stale_heartbeat = "2026-04-07T13:58:35+00:00"
    _insert_node(db, "node-1", "brunhilde-vps", stale_heartbeat, status="offline")
    _insert_mapped_agent(db, "agent-1", "brunhilde", "node-1", stale_heartbeat)
    _insert_mapped_agent(db, "agent-2", "claude-code", "node-1", stale_heartbeat)

    service = RemoteAgentService(db)

    assert service.heartbeat_node("node-1", agent_id="agent-1") is True

    brunhilde = db.fetch_one("SELECT status, last_heartbeat FROM agents WHERE id = 'agent-1'")
    claude = db.fetch_one("SELECT status, last_heartbeat FROM agents WHERE id = 'agent-2'")

    try:
        assert brunhilde["status"] == "online"
        assert brunhilde["last_heartbeat"] != stale_heartbeat
        assert claude["status"] == "offline"
        assert claude["last_heartbeat"] == stale_heartbeat
    finally:
        db.close_all_connections()


def test_remote_agent_status_separates_fresh_node_from_stale_agent(tmp_path):
    db = _make_db(tmp_path)
    now = datetime.now(timezone.utc)
    fresh_node_heartbeat = now.isoformat()
    stale_agent_heartbeat = (now - timedelta(minutes=45)).isoformat()
    _insert_node(db, "node-1", "brunhilde-vps", fresh_node_heartbeat, status="online")
    _insert_mapped_agent(db, "agent-1", "claude-code", "node-1", stale_agent_heartbeat)

    service = RemoteAgentService(db)

    try:
        [agent] = service.get_remote_agents()
        assert agent["node_status"] == "online"
        assert agent["agent_status"] == "offline"
        assert agent["status"] == "offline"
        assert agent["last_node_heartbeat"] == fresh_node_heartbeat
        assert agent["last_agent_heartbeat"] == stale_agent_heartbeat
        assert agent["last_heartbeat"] == stale_agent_heartbeat
        assert agent["offline_reason"] == "stale_agent_heartbeat"
    finally:
        db.close_all_connections()


def test_remote_agent_status_keeps_fresh_agent_online(tmp_path):
    db = _make_db(tmp_path)
    fresh = datetime.now(timezone.utc).isoformat()
    _insert_node(db, "node-1", "brunhilde-vps", fresh, status="online")
    _insert_mapped_agent(db, "agent-1", "brunhilde", "node-1", fresh)
    db.execute("UPDATE agents SET status = 'online' WHERE id = 'agent-1'")

    service = RemoteAgentService(db)

    try:
        [agent] = service.get_remote_agents()
        assert agent["node_status"] == "online"
        assert agent["agent_status"] == "online"
        assert agent["status"] == "online"
        assert agent["offline_reason"] is None
    finally:
        db.close_all_connections()
