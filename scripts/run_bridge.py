#!/usr/bin/env python3
"""
Run an agent bridge to connect to OpenHub.

Usage:
    python scripts/run_bridge.py --agent brunhilde --hub https://hub.brunhilde.cloud
    python scripts/run_bridge.py --agent claude-code --hub http://localhost:7788
"""
import argparse
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.bridge.agent_bridge import AgentBridge


AGENT_CONFIGS = {
    "brunhilde": {
        "capabilities": ["code_edit", "code_review", "research", "email", "telegram", "discord"],
        "mcp_servers": ["filesystem", "github", "discord", "openhub"],
        "description": "Brunhilde von Nacht - OpenHub AI Agent (GPT 5.5 / OpenAI Codex)",
        "node_name": "brunhilde-vps",
        "node_url": "http://localhost:18789",
    },
    "claude-code": {
        "capabilities": ["code_edit", "code_review", "testing", "analysis", "refactoring", "documentation"],
        "mcp_servers": ["filesystem", "bash"],
        "description": "Codex-compatible local coding agent (GPT 5.5) - WSL local agent",
        "node_name": "brunhilde-vps",
        "node_url": "http://localhost:7788",
    },
    "qwen-code": {
        "capabilities": ["code_edit", "code_review", "browser_automation", "security_analysis", "research"],
        "mcp_servers": ["filesystem", "bash", "playwright"],
        "description": "Qwen Code (qwen3.5-plus) - VPS agent",
        "node_name": "brunhilde-vps",
        "node_url": "http://localhost:7788",
    },
}


def main():
    parser = argparse.ArgumentParser(description="Run OpenHub Agent Bridge")
    parser.add_argument("--agent", required=True, help="Agent name (brunhilde, claude-code, qwen-code)")
    parser.add_argument("--hub", default="http://localhost:7788", help="OpenHub URL")
    parser.add_argument("--api-key", default=os.environ.get("OPENHUB_AGENT_KEY"), help="API key for authentication (or OPENHUB_AGENT_KEY env var)")
    parser.add_argument("--heartbeat", type=int, default=60, help="Heartbeat interval (seconds)")
    parser.add_argument("--poll", type=int, default=10, help="Task poll interval (seconds)")
    parser.add_argument("--execute", action="store_true", help="Execute tasks with a registered handler; default is dry-run polling")
    args = parser.parse_args()

    config = AGENT_CONFIGS.get(args.agent)
    if not args.api_key:
        print("Missing API key: pass --api-key or set OPENHUB_AGENT_KEY")
        sys.exit(1)
    if not config:
        print(f"Unknown agent: {args.agent}")
        print(f"Available: {', '.join(AGENT_CONFIGS.keys())}")
        sys.exit(1)

    bridge = AgentBridge(
        hub_url=args.hub,
        agent_name=args.agent,
        capabilities=config["capabilities"],
        api_key=args.api_key,
        node_name=config["node_name"],
        description=config["description"],
        mcp_servers=config.get("mcp_servers", []),
        heartbeat_interval=args.heartbeat,
        task_poll_interval=args.poll,
        dry_run=not args.execute,
    )

    print(f"Starting bridge: {args.agent} -> {args.hub}")
    asyncio.run(bridge.run())


if __name__ == "__main__":
    main()
