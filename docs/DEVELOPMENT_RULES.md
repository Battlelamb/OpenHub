# Agent Hub Development Rules & Guidelines

## Code Quality Standards

### 1. Code Structure Rules

#### Python Code Organization
```python
# ✅ GOOD: Clear module structure
app/
├── api/               # FastAPI routes
├── core/             # Business logic
├── db/               # Database operations
├── models/           # Pydantic models
├── services/         # External services
└── utils/            # Helper functions

# ❌ BAD: Mixed responsibilities
app/
├── everything.py     # Monolithic file
```

#### Function Design Rules
```python
# ✅ GOOD: Single responsibility, typed
async def claim_task(
    agent_id: str, 
    capabilities: list[str],
    timeout_seconds: int = 300
) -> Optional[Task]:
    """Claim next available task for agent."""
    pass

# ❌ BAD: Multiple responsibilities, no types
def handle_agent_stuff(agent, data, options=None):
    # Claims task, updates status, sends notifications
    pass
```

### 2. API Design Rules

#### Endpoint Consistency
```python
# ✅ GOOD: RESTful, consistent naming
POST   /v1/agents/register
GET    /v1/agents/{agent_id}
POST   /v1/tasks/claim
PUT    /v1/tasks/{task_id}/complete

# ❌ BAD: Inconsistent patterns
POST   /register_agent
GET    /getAgentById/{id}
POST   /claim-task
PUT    /complete_task_by_id/{task_id}
```

#### Response Format Standard
```python
# ✅ GOOD: Consistent response structure
{
    "success": true,
    "data": {...},
    "message": "Task claimed successfully",
    "timestamp": "2026-02-24T10:30:00Z"
}

# Error responses
{
    "success": false,
    "error": {
        "code": "TASK_ALREADY_CLAIMED",
        "message": "Task is already claimed by another agent",
        "details": {"claimed_by": "agent-123"}
    },
    "timestamp": "2026-02-24T10:30:00Z"
}
```

### 3. Database Access Rules

#### Repository Pattern
```python
# ✅ GOOD: Repository abstraction
class TaskRepository:
    async def create_task(self, task: TaskCreate) -> Task:
        """Create new task."""
        
    async def claim_task(self, agent_id: str, capabilities: list[str]) -> Optional[Task]:
        """Atomically claim task for agent."""
        
    async def update_task_status(self, task_id: str, status: TaskStatus) -> bool:
        """Update task status."""

# ❌ BAD: Direct DB access in API handlers
@app.post("/tasks/claim")
async def claim_task():
    cursor = db.execute("UPDATE tasks SET...")  # No abstraction
```

#### Transaction Rules
```python
# ✅ GOOD: Proper transaction handling
async def claim_task_atomic(agent_id: str) -> Optional[Task]:
    async with db.transaction():
        task = await find_available_task(agent_id)
        if task:
            await update_task_owner(task.id, agent_id)
            await create_lease(task.id, agent_id, ttl=300)
            await log_claim_event(task.id, agent_id)
        return task

# ❌ BAD: Race conditions possible
async def claim_task_unsafe(agent_id: str):
    task = await find_available_task(agent_id)  # Race window
    await update_task_owner(task.id, agent_id)  # Could fail
```

## Performance Guidelines

### 1. WebSocket Connection Management

#### Connection Pooling
```python
# ✅ GOOD: Connection pool with limits
class WebSocketManager:
    def __init__(self, max_connections: int = 500):
        self.connections: Dict[str, WebSocket] = {}
        self.max_connections = max_connections
        
    async def add_connection(self, agent_id: str, websocket: WebSocket):
        if len(self.connections) >= self.max_connections:
            raise ConnectionLimitExceeded()
        self.connections[agent_id] = websocket
```

#### Heartbeat Protocol
```python
# ✅ GOOD: Regular heartbeat with timeout
HEARTBEAT_INTERVAL = 30  # seconds
HEARTBEAT_TIMEOUT = 90   # seconds

async def heartbeat_monitor():
    while True:
        await asyncio.sleep(HEARTBEAT_INTERVAL)
        for agent_id, last_seen in agent_heartbeats.items():
            if time.now() - last_seen > HEARTBEAT_TIMEOUT:
                await mark_agent_offline(agent_id)
```

### 2. Vector Search Optimization

#### Batch Operations
```python
# ✅ GOOD: Batch vector operations
async def search_similar_solutions(problems: list[str]) -> list[Solution]:
    embeddings = await batch_embed(problems)  # Batch embedding
    results = zvec_collection.query(embeddings, batch=True)
    return results

# ❌ BAD: Individual operations
async def search_similar_solutions(problems: list[str]):
    results = []
    for problem in problems:
        embedding = await embed(problem)  # Slow individual calls
        result = zvec_collection.query(embedding)
        results.append(result)
```

#### Embedding Caching
```python
# ✅ GOOD: Cache frequent embeddings
class EmbeddingCache:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.ttl = 3600  # 1 hour
        
    async def get_embedding(self, text: str) -> list[float]:
        cache_key = f"embedding:{hashlib.md5(text.encode()).hexdigest()}"
        cached = await self.redis.get(cache_key)
        if cached:
            return json.loads(cached)
            
        embedding = await compute_embedding(text)
        await self.redis.setex(cache_key, self.ttl, json.dumps(embedding))
        return embedding
```

## Security Rules

### 1. Authentication & Authorization

#### API Key Management
```python
# ✅ GOOD: Hashed API keys with roles
class APIKeyManager:
    async def validate_key(self, api_key: str) -> Optional[AgentRole]:
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        stored_key = await self.db.get_api_key(key_hash)
        return stored_key.role if stored_key else None

# ❌ BAD: Plain text keys
api_keys = {
    "agent123": "admin",  # Plain text storage
    "agent456": "viewer"
}
```

#### Permission Checks
```python
# ✅ GOOD: Granular permission system
@require_permission("task:claim")
async def claim_task(agent_id: str, current_role: AgentRole):
    if current_role not in [AgentRole.AGENT, AgentRole.ADMIN]:
        raise PermissionDenied("Insufficient privileges")
```

### 2. Input Validation

#### Request Validation
```python
# ✅ GOOD: Pydantic validation with constraints
class TaskCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., max_length=5000)
    priority: int = Field(default=50, ge=0, le=100)
    capabilities: list[str] = Field(..., min_items=1, max_items=10)
    
    @field_validator('capabilities')
    def validate_capabilities(cls, v):
        allowed = ['code_edit', 'test_run', 'review', 'documentation']
        for cap in v:
            if cap not in allowed:
                raise ValueError(f'Invalid capability: {cap}')
        return v
```

#### Path Traversal Prevention
```python
# ✅ GOOD: Secure file handling
def validate_artifact_path(file_path: str) -> str:
    # Prevent directory traversal
    safe_path = os.path.normpath(file_path)
    if '..' in safe_path or safe_path.startswith('/'):
        raise SecurityError("Invalid file path")
    return os.path.join(ARTIFACT_DIR, safe_path)

# ❌ BAD: Direct path usage
def save_artifact(file_path: str, content: bytes):
    with open(file_path, 'wb') as f:  # Vulnerable to traversal
        f.write(content)
```

## Testing Standards

### 1. Test Coverage Requirements

#### Minimum Coverage
- **Unit Tests**: 90% coverage for core orchestration
- **Integration Tests**: All API endpoints
- **Load Tests**: 100+ concurrent WebSocket connections
- **Security Tests**: Authentication, authorization, input validation

#### Test Organization
```python
tests/
├── unit/
│   ├── test_task_orchestrator.py
│   ├── test_agent_manager.py
│   └── test_vector_search.py
├── integration/
│   ├── test_agent_lifecycle.py
│   ├── test_task_completion_flow.py
│   └── test_websocket_coordination.py
├── load/
│   └── test_concurrent_agents.py
└── security/
    ├── test_authentication.py
    └── test_input_validation.py
```

### 2. Test Quality Rules

#### Unit Test Standards
```python
# ✅ GOOD: Clear, isolated tests
async def test_claim_task_with_matching_capabilities():
    # Arrange
    agent = create_test_agent(capabilities=['python', 'testing'])
    task = create_test_task(required_capabilities=['python'])
    
    # Act
    result = await orchestrator.claim_task(agent.id)
    
    # Assert
    assert result.task_id == task.id
    assert result.claimed_by == agent.id
    assert result.status == TaskStatus.CLAIMED

# ❌ BAD: Complex, multi-purpose test
async def test_task_stuff():
    # Tests claiming, updating, completing all in one
    pass
```

#### Mock Usage Guidelines
```python
# ✅ GOOD: Mock external dependencies only
@patch('app.services.embedding_service.embed')
async def test_knowledge_search(mock_embed):
    mock_embed.return_value = [0.1, 0.2, 0.3]
    result = await search_knowledge("python testing")
    assert len(result) > 0

# ❌ BAD: Mocking internal logic
@patch('app.core.orchestrator.TaskOrchestrator.claim_task')
async def test_claim_endpoint(mock_claim):
    # Testing the mock, not the real logic
    pass
```

## Monitoring & Logging Rules

### 1. Structured Logging

#### Log Format Standard
```python
# ✅ GOOD: Structured logging with context
logger.info(
    "task_completed",
    extra={
        "task_id": task.id,
        "agent_id": task.claimed_by,
        "duration_seconds": task.completion_time - task.claim_time,
        "artifacts_created": len(task.artifacts),
        "knowledge_entries": task.knowledge_shared
    }
)

# ❌ BAD: Unstructured logging
logger.info(f"Task {task.id} completed by {task.claimed_by}")
```

#### Log Levels Usage
- **DEBUG**: Development debugging, verbose operation details
- **INFO**: Normal operations, state changes, completions
- **WARNING**: Recoverable errors, retries, timeouts
- **ERROR**: Failed operations, exceptions
- **CRITICAL**: System-level failures, security breaches

### 2. Metrics Collection

#### Key Metrics to Track
```python
# Performance Metrics
AGENT_CONNECTION_COUNT = Gauge('agent_connections', 'Active agent connections')
TASK_COMPLETION_RATE = Counter('tasks_completed_total', 'Total completed tasks')
TASK_DURATION = Histogram('task_duration_seconds', 'Task completion time')
VECTOR_SEARCH_LATENCY = Histogram('vector_search_seconds', 'Vector search time')

# Business Metrics  
KNOWLEDGE_SHARING_RATE = Counter('knowledge_shared_total', 'Knowledge entries shared')
AGENT_UTILIZATION = Gauge('agent_utilization_ratio', 'Agent busy ratio')
LOCK_CONTENTION = Counter('lock_conflicts_total', 'Resource lock conflicts')
```

## Deployment Rules

### 1. Environment Management

#### Configuration Hierarchy
```yaml
# 1. Default values in code
# 2. Environment-specific config files
# 3. Environment variables (override)
# 4. Runtime configuration API (admin only)

# config/production.yaml
agenthub:
  max_agents: 100
  task_timeout_sec: 300
  log_level: "INFO"
  
database:
  backup_interval_hours: 24
  wal_mode: true
  
vector_store:
  batch_size: 1000
  index_optimization_interval: 3600
```

#### Secret Management
```python
# ✅ GOOD: Environment-based secrets
API_KEYS_FILE = os.getenv('API_KEYS_FILE', '/secrets/api_keys.json')
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD')
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')

# ❌ BAD: Hardcoded secrets
ADMIN_API_KEY = "super-secret-key"  # Never do this
```

### 2. Docker Best Practices

#### Multi-stage Builds
```dockerfile
# ✅ GOOD: Multi-stage for smaller images
FROM python:3.11-slim as builder
WORKDIR /build
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /build/wheels -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /build/wheels /wheels
RUN pip install --no-cache-dir --find-links /wheels -r requirements.txt
```

#### Health Check Implementation
```dockerfile
# Health check with proper timeout and retries
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:7788/v1/health || exit 1
```

## Error Handling Standards

### 1. Exception Hierarchy

#### Custom Exception Classes
```python
class AgentHubException(Exception):
    """Base exception for all AgentHub errors."""
    pass

class AgentNotFound(AgentHubException):
    """Agent ID not found in registry."""
    pass

class TaskClaimConflict(AgentHubException):
    """Task already claimed by another agent."""
    pass

class InsufficientCapabilities(AgentHubException):
    """Agent lacks required capabilities for task."""
    pass
```

### 2. Error Response Standards

#### HTTP Error Mapping
```python
ERROR_STATUS_MAP = {
    AgentNotFound: 404,
    TaskClaimConflict: 409,
    InsufficientCapabilities: 403,
    ValidationError: 400,
    AuthenticationError: 401,
    PermissionDenied: 403,
    InternalError: 500
}
```

## Code Review Checklist

### Before Submitting PR
- [ ] All tests pass (unit + integration)
- [ ] Code coverage meets 90% threshold  
- [ ] No security vulnerabilities detected
- [ ] Performance impact assessed
- [ ] Documentation updated
- [ ] Logging added for new operations
- [ ] Error handling implemented
- [ ] Input validation added

### Review Focus Areas
1. **Security**: Authentication, authorization, input validation
2. **Performance**: Database queries, WebSocket handling, caching
3. **Reliability**: Error handling, transaction boundaries, retries
4. **Maintainability**: Code organization, documentation, testing
5. **Scalability**: Resource usage, connection limits, bottlenecks

### Deployment Checklist
- [ ] Environment configuration reviewed
- [ ] Database migrations tested
- [ ] Backup procedures verified
- [ ] Monitoring alerts configured
- [ ] Load testing completed
- [ ] Security scan passed
- [ ] Rollback plan prepared
- [ ] Documentation updated