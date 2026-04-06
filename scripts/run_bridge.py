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
        "description": "Brunhilde von Nacht - OpenClaw AI Agent (gpt-5.3-codex)",
        "node_name": "brunhilde-vps",
        "node_url": "http://localhost:18789",
    },
    "claude-code": {
        "capabilities": ["code_edit", "code_review", "testing", "analysis", "refactoring", "documentation"],
        "description": "Claude Code (Opus 4.6) - WSL local agent",
        "node_name": "brunhilde-vps",
        "node_url": "http://localhost:7788",
    },
    "qwen-code": {
        "capabilities": ["code_edit", "code_review", "browser_automation", "security_analysis", "research"],
        "description": "Qwen Code (qwen3.5-plus) - VPS agent",
        "node_name": "brunhilde-vps",
        "node_url": "http://localhost:7788",
    },
}


def main():
    parser = argparse.ArgumentParser(description="Run OpenHub Agent Bridge")
    parser.add_argument("--agent", required=True, help="Agent name (brunhilde, claude-code, qwen-code)")
    parser.add_argument("--hub", default="http://localhost:7788", help="OpenHub URL")
    parser.add_argument("--api-key", default=None, help="API key for authentication")
    parser.add_argument("--heartbeat", type=int, default=60, help="Heartbeat interval (seconds)")
    parser.add_argument("--poll", type=int, default=10, help="Task poll interval (seconds)")
    args = parser.parse_args()

    config = AGENT_CONFIGS.get(args.agent)
    if not config:
        print(f"Unknown agent: {args.agent}")
        print(f"Available: {', '.join(AGENT_CONFIGS.keys())}")
        sys.exit(1)

    bridge = AgentBridge(
        hub_url=args.hub,
        agent_name=args.agent,
        capabilities=config["capabilities"],
        node_name=config["node_name"],
        node_url=config["node_url"],
        description=config["description"],
        api_key=args.api_key,
        heartbeat_interval=args.heartbeat,
        task_poll_interval=args.poll,
    )

    print(f"Starting bridge: {args.agent} -> {args.hub}")
    asyncio.run(bridge.run())


if __name__ == "__main__":
    main()
