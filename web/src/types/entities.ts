export type AgentStatus = 'online' | 'offline' | 'idle' | 'error'
export type TaskStatus = 'queued' | 'claimed' | 'running' | 'waiting_approval' | 'completed' | 'failed' | 'cancelled'
export type TaskPriority = 1 | 2 | 3 | 4 | 5

export interface Agent {
  id: string
  name: string
  status: AgentStatus
  agent_status?: AgentStatus
  capabilities: string[]
  last_heartbeat?: string
  last_agent_heartbeat?: string
  current_task_id?: string | null
  node_id?: string
  node_name?: string
  node_status?: AgentStatus
  last_node_heartbeat?: string
  offline_reason?: string | null
  mcp_profiles?: string[]
  load_score?: number  // surfaces in /discover/available
  created_at?: string  // optional - /discover/available does not include this
  updated_at?: string  // optional - /discover/available does not include this
}

export interface Task {
  id: string
  title: string
  description?: string
  status: TaskStatus
  priority: TaskPriority
  agent_id?: string | null         // adapter renames from backend's assigned_agent_id
  required_capabilities?: string[]
  task_type?: string
  created_by?: string | null
  completed_at?: string | null
  started_at?: string | null
  assigned_at?: string | null
  retry_count?: number
  max_retries?: number
  progress?: number
  result?: Record<string, unknown>
  error?: string                    // adapter renames from backend's last_error
  created_at: string
  updated_at: string
}

export interface Workflow {
  id: string                // adapter renames from backend's run_id
  name: string
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'
  steps: WorkflowStep[]     // adapter pulls from backend's progress.steps[] or defaults to []
  created_at: string
  updated_at: string        // adapter falls back to created_at when backend omits this field
}

export interface WorkflowStep {
  id: string
  name: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped'
  agent_id?: string | null
  started_at?: string
  completed_at?: string
}

export interface DlqItem {
  task_id: string
  title: string
  failed_at: string         // adapter renames from backend's created_at
  error: string             // adapter renames from backend's last_error
  retries: number           // adapter renames from backend's retry_count
  task_type?: string
  priority?: number
  max_retries?: number
  assigned_to?: string
}

export interface CostItem {
  agent_id: string         // adapter falls back to agent_name when backend lacks it
  agent_name: string
  total_tokens: number     // adapter sums input_tokens + output_tokens from backend
  total_cost_usd: number
  task_count: number       // adapter maps from backend's api_calls field
}

export interface MemoryItem {
  key: string
  size_bytes: number       // backend /keys does not return size; adapter sets 0
  age_seconds: number      // adapter computes from now - updated_at
  value_preview?: unknown
  value_type?: string      // surfaces from backend for richer display in future
  tags?: string[]
  updated_at?: string
}

export interface SemanticSearchHit {
  entity_type: 'agent' | 'task' | 'memory' | 'artifact' | 'message'
  id: string
  content: string
  distance: number
}

export interface SemanticSearchResponse {
  query: string
  total: number
  hits: SemanticSearchHit[]
}

export interface ResourceLock {
  resource_id: string
  agent_id: string
  acquired_at: string
  expires_at: string
  conflict?: boolean
}

export interface HealthResponse {
  status: string
  version?: string
  uptime_seconds?: number
  database?: {
    status?: string
    [key: string]: unknown
  }
  [key: string]: unknown
}

export type TraceCategory = 'llm' | 'tool' | 'db' | 'http' | 'internal' | 'error'

export type TaskTimelineSource = 'evidence' | 'trace'

export interface TaskTimelineItem {
  id: string
  task_id: string
  source: TaskTimelineSource
  item_type: string
  title: string
  occurred_at: string
  actor_id?: string | null
  summary?: string | null
  content?: Record<string, unknown>
  artifact_ids?: string[]
  outcome?: string | null
  trace_id?: string | null
  duration_ms?: number | null
  category?: string | null
  level?: number | null
  created_at?: string | null
  updated_at?: string | null
}

export interface TraceSpan {
  id: string
  name: string
  category: TraceCategory
  duration_ms: number
  level: number
  started_at: string
  completed_at?: string
}
