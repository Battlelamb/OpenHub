# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains specifications and plans for an **Agent Collaboration Hub** system - a local multi-agent coordination platform that enables multiple AI agents (Claude Code, Cursor, Copilot, etc.) to work together on the same codebase without conflicts.

## Repository Structure

- `CODEX_PLAN.md` - Comprehensive implementation plan for the Codex AgentHub Local project
- `MULTI_AGENT_HUB_SPEC.md` - High-level specification for multi-agent collaboration system

## Project Architecture

### Core Concept
The system implements a **local orchestrator service** that coordinates multiple AI agents through:
- **FastAPI-based coordination server** running on `0.0.0.0:7788`
- **SQLite state store** for persistent data (`./data/state/agenthub.db`)
- **Local artifact storage** (`./data/artifacts`)
- **WebSocket + REST hybrid** for universal agent connectivity
- **Agent registration and heartbeat system**
- **Task queue with claim/lease mechanism**
- **Resource locks** to prevent file conflicts
- **Audit/event logging** for full traceability

### Key Components
1. **WebSocket Orchestrator** - Real-time agent coordination (FastAPI + WebSockets)
2. **Universal Agent Protocol** - WebSocket-based communication for all agent types
3. **State Store** - SQLite database with migration system
4. **Artifact Store** - Local filesystem storage with integrity checks
5. **Dashboard** - Real-time Web UI with live updates
6. **Background Jobs** - Lease expiry, retry scheduling, cleanup

## Technical Stack

- **Python 3.11+** with FastAPI + Uvicorn + WebSockets
- **SQLite** with custom migration system
- **Pydantic v2** for data validation
- **WebSocket protocol** for real-time agent communication
- **Jinja2** templates for dashboard
- **pytest** for testing
- **Docker** support with compose configuration

## Development Commands

### Project Setup
```bash
# Initialize database
python scripts/init_db.py

# Seed demo data
python scripts/seed_demo.py

# Run development server
uvicorn app.main:app --host 0.0.0.0 --port 7788 --reload
```

### Docker Operations (Recommended Deployment)
```bash
# Build and run with Docker Compose
docker-compose up --build

# Development with volume mounting
docker-compose -f docker-compose.dev.yml up

# Production deployment
docker run -d \
  -p 7788:7788 \
  -v ./data:/app/data \
  --name agenthub \
  --restart unless-stopped \
  agenthub:latest

# Health check
curl http://localhost:7788/v1/health
```

### Testing
```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/test_task_claim_concurrency.py
pytest tests/test_retries.py
pytest tests/test_locks.py
```

## API Architecture

### Authentication
- Header: `X-AgentHub-Key: <token>`
- Roles: `admin`, `agent`, `viewer`

### Core Endpoints
- **Health**: `GET /v1/health`
- **Agent Management**: `/v1/agents/*` (register, heartbeat, disconnect)
- **Task Lifecycle**: `/v1/tasks/*` (create, claim, start, complete, fail)
- **Resource Locks**: `/v1/locks/*` (acquire, renew, release)
- **Artifacts**: `/v1/artifacts/*` (upload, download, metadata)
- **Events**: `/v1/events/*` (audit trail, SSE streaming)
- **Administration**: `/v1/admin/*` (stats, requeue, retention)

### Task State Flow
```
queued → claimed → running → completed/failed
                ↓
         waiting_approval → approved → running
```

## Data Model Key Tables

- `agents` - Agent registry with capabilities and status
- `tasks` - Task queue with state, priority, and lease management
- `task_attempts` - Per-attempt logging for retries
- `threads` & `messages` - Communication system
- `artifacts` - File storage with metadata and integrity
- `locks` - Resource conflict prevention
- `events` - Audit trail and event streaming
- `approvals` - Human-in-the-loop workflow

## Configuration

Environment variables (with defaults):
- `AGENTHUB_HOST=0.0.0.0`
- `AGENTHUB_PORT=7788`
- `AGENTHUB_DB_PATH=./data/state/agenthub.db`
- `AGENTHUB_ARTIFACT_DIR=./data/artifacts`
- `AGENTHUB_TASK_LEASE_TTL_SEC=60`
- `AGENTHUB_LOG_LEVEL=INFO`

## Implementation Phases

For detailed implementation roadmap with 200+ modular sub-tasks, see [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md).

### Phase 1: Foundation & Setup (2-3 weeks)
- Repository & environment setup
- Core FastAPI infrastructure  
- Database layer implementation
- Authentication & security system

### Phase 2: Agent Management (1-2 weeks)
- Agent registration system
- Agent lifecycle management
- Capability matching system

### Phase 3: Task Coordination (2-3 weeks)
- Task management core
- Task assignment & claiming
- Task execution management

### Phase 4: Real-Time Communication (1-2 weeks)
- WebSocket infrastructure
- Real-time events system
- Message routing

### Phase 5: Vector Memory System (1-2 weeks)
- Zvec integration
- Knowledge sharing system
- Agent learning framework

### Phase 6-10: Advanced Features (4-6 weeks)
- Resource management
- Monitoring & analytics
- Testing & QA
- Web dashboard
- Documentation & deployment

**Total Estimated Time: 10-15 weeks**

**Key Milestones:**
- ✅ Milestone 1: Basic Infrastructure (Week 3)
- ✅ Milestone 2: Agent Registration (Week 5)
- ✅ Milestone 3: Task Coordination (Week 8)  
- ✅ Milestone 4: Real-Time Communication (Week 10)
- ✅ Milestone 5: Production Ready (Week 15)

## Key Design Decisions

- **Docker-first deployment**: Universal agent access via HTTP REST API
- **Cross-agent compatibility**: Works with Claude Code, Cursor, Copilot, custom scripts
- **Local-first**: Single machine/LAN deployment target
- **SQLite**: Simple, reliable persistence without external dependencies
- **Lease-based concurrency**: Prevents conflicts through time-bounded resource claims
- **Event-driven**: Full audit trail with real-time streaming
- **WebSocket-first with REST fallback**: Real-time coordination with file operation support
- **Capability matching**: Tasks routed based on agent capabilities
- **Retry with backoff**: Resilient task processing with dead-letter queue

## Critical Acceptance Criteria

1. Multiple agents can work simultaneously without task conflicts
2. Agent crashes/disconnects trigger automatic task lease recovery
3. All artifacts stored locally with integrity verification
4. Dashboard provides near real-time status visibility
5. Complete audit trail for all state transitions
6. System state persists across restarts
7. Concurrent task claims are properly serialized

## Universal Agent Integration (WebSocket-First)

### All Agent Types Use Same Protocol
```javascript
// Works with Claude Code, Cursor, Copilot, Custom Scripts
const ws = new WebSocket('ws://localhost:7788/v1/agent-connect');

// 1. Register agent
ws.send(JSON.stringify({
  type: 'agent_register',
  name: 'claude-fe-dev',
  capabilities: ['react', 'typescript', 'testing'],
  api_key: 'your-api-key'
}));

// 2. Listen for real-time events
ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  
  switch(msg.type) {
    case 'task_assigned':
      processTask(msg.task);
      break;
    case 'approval_required':
      requestHumanApproval(msg.task_id, msg.reason);
      break;
    case 'resource_lock_acquired':
      proceedWithFileEdit(msg.resource_key);
      break;
  }
};

// 3. Send responses
function completeTask(taskId, result) {
  ws.send(JSON.stringify({
    type: 'task_complete',
    task_id: taskId,
    result: result,
    artifacts: ['artifact_id_1', 'artifact_id_2']
  }));
}
```

### Language-Specific WebSocket Clients

#### Python (for custom scripts)
```python
import asyncio
import websockets
import json

async def agent_client():
    uri = "ws://localhost:7788/v1/agent-connect"
    
    async with websockets.connect(uri) as websocket:
        # Register
        await websocket.send(json.dumps({
            "type": "agent_register",
            "name": "python-automation",
            "capabilities": ["data_analysis", "reporting"],
            "api_key": "your-api-key"
        }))
        
        # Listen for tasks
        async for message in websocket:
            data = json.loads(message)
            if data["type"] == "task_assigned":
                result = process_task(data["task"])
                await websocket.send(json.dumps({
                    "type": "task_complete",
                    "task_id": data["task"]["id"],
                    "result": result
                }))

asyncio.run(agent_client())
```

#### Node.js/TypeScript (for extensions)
```typescript
import WebSocket from 'ws';

class AgentHubClient {
  private ws: WebSocket;
  
  constructor(private apiKey: string) {
    this.ws = new WebSocket('ws://localhost:7788/v1/agent-connect');
    this.setupEventHandlers();
  }
  
  private setupEventHandlers() {
    this.ws.on('open', () => {
      this.register('cursor-extension', ['code_edit', 'refactor']);
    });
    
    this.ws.on('message', (data: string) => {
      const msg = JSON.parse(data);
      this.handleMessage(msg);
    });
  }
  
  private register(name: string, capabilities: string[]) {
    this.send({
      type: 'agent_register',
      name,
      capabilities,
      api_key: this.apiKey
    });
  }
  
  private send(data: any) {
    this.ws.send(JSON.stringify(data));
  }
}
```

### REST API (Fallback for file operations)
```bash
# File upload (too large for WebSocket)
curl -F "file=@report.pdf" \
     -H "X-AgentHub-Key: your-key" \
     http://localhost:7788/v1/artifacts/upload

# Health check
curl http://localhost:7788/v1/health
```

## System Rules & Best Practices

### Agent Development Guidelines

#### 1. Agent Registration Rules
```python
# ✅ GOOD: Descriptive capabilities
capabilities = [
    "code_edit_python", 
    "test_execution", 
    "api_documentation",
    "error_analysis"
]

# ❌ BAD: Vague capabilities  
capabilities = ["coding", "help", "general"]
```

#### 2. Task Claiming Protocol
- **Always check task requirements** before claiming
- **Heartbeat every 30 seconds** during execution
- **Release locks immediately** after task completion
- **Set reasonable timeouts** (default: 5 minutes for code tasks)

#### 3. Resource Lock Management
```python
# ✅ GOOD: Specific resource locks
resource_key = "repo:SkorAI:file:src/api/endpoints.py:lines:45-67"

# ❌ BAD: Broad locks
resource_key = "repo:SkorAI"  # Blocks entire repo
```

#### 4. Knowledge Sharing Standards
```python
# ✅ GOOD: Structured findings
finding = {
    "category": "solution",
    "content": "CORS fixed by adding origins=['http://localhost:3000'] to FastAPI middleware",
    "code_snippet": "app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:3000'])",
    "severity": "info",
    "tags": ["cors", "fastapi", "frontend"],
    "success_rate": 1.0
}

# ❌ BAD: Vague findings  
finding = {"content": "fixed something"}
```

### Architecture Evaluation

#### Performance Trade-offs

| Component | Choice | Pros | Cons | Alternative |
|-----------|--------|------|------|-------------|
| **Language** | Python | AI ecosystem, rapid dev | GIL limitations | Go (performance) |
| **Vector DB** | Zvec | Embedded, 8K QPS | Python-only | Chroma (HTTP API) |
| **Coordination** | WebSocket | Real-time, bidirectional | Connection overhead | Server-Sent Events |
| **Persistence** | SQLite | Simple, reliable | Single writer | PostgreSQL |
| **Cache** | Redis | Proven, fast | Extra service | In-memory Python |

#### Scalability Limits
- **Concurrent Agents**: ~500 (WebSocket limit)
- **Task Throughput**: ~1000 tasks/minute  
- **Vector Storage**: 10M+ embeddings (Zvec)
- **File Storage**: Limited by disk space

#### Security Model
```yaml
API_KEY_ROLES:
  admin: ["*"]  # Full access
  agent: ["task_claim", "artifact_upload", "knowledge_share"]
  viewer: ["read_only"]

RESOURCE_ISOLATION:
  - Agent A cannot access Agent B's private artifacts
  - File locks prevent concurrent modifications
  - API rate limiting: 100 requests/minute per agent
```

### Development Best Practices

#### 1. Error Handling Protocol
```python
# ✅ GOOD: Structured error responses
try:
    result = process_task(task)
    await complete_task(task_id, result)
except RetryableError as e:
    await fail_task(task_id, str(e), retryable=True)
except CriticalError as e:
    await fail_task(task_id, str(e), retryable=False)
    await create_incident(e)
```

#### 2. Logging Standards
```python
# Use structured logging
logger.info(
    "task_claimed",
    extra={
        "task_id": task_id,
        "agent_id": agent_id,
        "capabilities_required": task.capabilities,
        "estimated_duration": "5min"
    }
)
```

#### 3. Testing Requirements
- **Unit tests**: All core orchestration logic
- **Integration tests**: Agent registration → task completion flow
- **Load tests**: 100+ concurrent WebSocket connections
- **Chaos tests**: Agent disconnection scenarios

#### 4. Monitoring & Observability
```yaml
METRICS_TO_TRACK:
  - agent_connection_count
  - task_completion_rate  
  - average_task_duration
  - lock_contention_events
  - vector_search_latency
  - memory_usage_per_agent
```

### Agent Integration Patterns

#### 1. Polling Agent Pattern
```python
# For simple agents without WebSocket
while True:
    task = get_next_task(agent_id)
    if task:
        result = process_task(task)
        complete_task(task.id, result)
    await asyncio.sleep(5)  # Polling interval
```

#### 2. Event-Driven Agent Pattern  
```python
# For advanced agents with WebSocket
async def agent_main():
    async with websockets.connect(hub_url) as ws:
        await register_agent(ws)
        async for message in ws:
            event = json.loads(message)
            await handle_event(event)
```

#### 3. Hybrid Agent Pattern
```python
# WebSocket for coordination + HTTP for file ops
class HybridAgent:
    def __init__(self):
        self.ws = WebSocketClient()
        self.http = HTTPClient() 
        
    async def upload_large_artifact(self, file_path):
        # Use HTTP for large files
        return await self.http.upload(file_path)
```

### Deployment Guidelines

#### 1. Environment Configuration
```env
# Production values
AGENTHUB_MAX_AGENTS=100
AGENTHUB_TASK_TIMEOUT_SEC=300
AGENTHUB_VECTOR_BATCH_SIZE=1000
AGENTHUB_LOG_LEVEL=INFO
REDIS_MAX_MEMORY=512mb
```

#### 2. Resource Limits
```yaml
# docker-compose.prod.yml
services:
  agenthub:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
```

#### 3. Backup Strategy
```bash
# Daily backups
0 2 * * * docker exec agenthub sqlite3 /app/data/agenthub.db ".backup /backup/agenthub-$(date +%Y%m%d).db"
0 2 * * * tar -czf /backup/zvec-$(date +%Y%m%d).tar.gz ./data/zvec/
```

### Troubleshooting Guide

#### Common Issues

1. **Agent Connection Drops**
   - Check network stability
   - Verify heartbeat implementation
   - Review WebSocket timeout settings

2. **Task Stuck in 'claimed' State**  
   - Run lease cleanup: `POST /v1/admin/cleanup-expired-leases`
   - Check agent health
   - Review task timeout configuration

3. **Vector Search Slow**
   - Monitor Zvec index optimization
   - Check embedding dimensionality match
   - Review query complexity

4. **Memory Usage High**
   - Monitor Redis memory usage
   - Check for connection leaks
   - Review Zvec collection size

#### Performance Optimization
- **WebSocket**: Use connection pooling
- **Vector Search**: Batch queries when possible  
- **Database**: Enable SQLite WAL mode
- **Cache**: Implement LRU eviction in Redis

## Development Notes

- This is a **specification/planning repository** - implementation occurs in separate project
- Target location: `d:\OneDrive\OLD\Documents\SkorAI\Codex_AgentHub_Local`
- Focus on **coordination and conflict resolution** between multiple AI agents
- **Docker deployment** provides universal agent compatibility
- **WebSocket-first** ensures real-time coordination across all agent types
- **Zvec embedded** eliminates vector service complexity while maintaining performance