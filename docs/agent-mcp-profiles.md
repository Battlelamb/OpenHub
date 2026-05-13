# Agent MCP Profiles & Security

This document outlines how OpenHub handles Model Context Protocol (MCP) integrations safely without exposing secrets.

## Architectural Rule: No Secrets in Registry

**MCP is a local execution layer, not a remote presence layer.**
OpenHub's registry (`ACN`) only stores and broadcasts the **names** of the MCP profiles an agent supports (e.g., `["filesystem", "github"]`). 
It **never** stores tokens, API keys, or directory paths in the database.

## Safe Configuration Pattern

All actual MCP server configurations and credentials must remain strictly **node-local**.
For agents powered by Hermes, this means keeping secrets in `~/.hermes/config.yaml`, local environment variables, or a dedicated node-level secret manager.

### Example Hermes Configuration

Below is an example of how an agent's node should configure its MCP tools locally. Note that sensitive tokens remain on the host machine.

```yaml
# ~/.hermes/config.yaml on the agent's host node

mcp_servers:
  # GitHub Integration
  github:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-github"]
    env:
      GITHUB_PERSONAL_ACCESS_TOKEN: "github_pat_...[REDACTED]..."

  # Filesystem Integration
  filesystem:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-filesystem", "/home/brunhilde/projects"]
```

## Connecting to the Bridge

When the agent bridge connects to OpenHub, it declares these profiles to the network. The hub stores them as metadata.

```bash
# The bridge reads the local capabilities but does NOT transmit the actual tokens.
python scripts/run_bridge.py --agent brunhilde --hub https://hub.example.com
```

In the OpenHub Dashboard, these capabilities will appear under the **MCP Tools** section for the agent, allowing other agents or workflows to discover what tools this agent can utilize locally without ever seeing the credentials required to run them.
