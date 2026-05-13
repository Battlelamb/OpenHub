from app.models.acn import RemoteAgentRegister


def test_remote_agent_register_normalizes_capabilities_and_profiles():
    agent = RemoteAgentRegister(
        agent_name="brunhilde",
        node_name="brunhilde-vps",
        capabilities=[" Code Edit ", "code edit", "RESEARCH"],
        channels=["Telegram", "telegram", " Discord "],
        mcp_servers=[" Filesystem ", "filesystem"],
    )

    assert agent.capabilities == ["code_edit", "research"]
    assert agent.channels == ["telegram", "discord"]
    assert agent.mcp_servers == ["filesystem"]


def test_remote_agent_register_accepts_legacy_string_lists():
    agent = RemoteAgentRegister(
        agent_name="legacy",
        node_name="legacy-node",
        capabilities="Code Edit, RESEARCH",
        channels="Telegram",
        mcp_servers="Filesystem, Git",
    )

    assert agent.capabilities == ["code_edit", "research"]
    assert agent.channels == ["telegram"]
    assert agent.mcp_servers == ["filesystem", "git"]
