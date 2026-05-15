import sqlite3

from app.services.vector_search_service import VectorSearchService


class SQLiteFakeDB:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row

    def fetch_all(self, sql, params=None):
        return self.conn.execute(sql, params or {}).fetchall()


def test_agent_list_unindexed_uses_registry_metadata_when_description_is_empty():
    db = SQLiteFakeDB()
    db.conn.execute(
        """
        CREATE TABLE agents (
            id TEXT PRIMARY KEY,
            agent_name TEXT,
            description TEXT,
            capabilities TEXT,
            skills TEXT,
            mcp_servers TEXT,
            languages TEXT,
            channels TEXT,
            model TEXT,
            platform TEXT,
            embedding_status TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        """
    )
    db.conn.execute(
        """
        INSERT INTO agents (
            id, agent_name, description, capabilities, skills, mcp_servers,
            languages, channels, model, platform, embedding_status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """,
        (
            "agent-1",
            "Sparse Registry Agent",
            "",
            '["rare-capability-vector-smoke"]',
            '["semantic-routing"]',
            '["registry-profile"]',
            '["tr"]',
            '["telegram"]',
            "qwen-smoke",
            "hermes",
            None,
        ),
    )

    rows = VectorSearchService(db).list_unindexed("agent", limit=10)
    db.conn.close()

    assert rows == [
        {
            "id": "agent-1",
            "content": (
                "Agent: Sparse Registry Agent\n"
                "Model: qwen-smoke\n"
                "Platform: hermes\n"
                "Capabilities: [\"rare-capability-vector-smoke\"]\n"
                "Skills: [\"semantic-routing\"]\n"
                "MCP profiles: [\"registry-profile\"]\n"
                "Languages: [\"tr\"]\n"
                "Channels: [\"telegram\"]"
            ),
        }
    ]
