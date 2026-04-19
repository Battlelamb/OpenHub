export type AgentStatus = 'online' | 'offline' | 'idle' | 'error'
export type TaskStatus = 'queued' | 'claimed' | 'running' | 'completed' | 'failed' | 'cancelled'
export type TaskPriority = 1 | 2 | 3 | 4 | 5

export interface Agent {
  id: string
  name: string
  status: AgentStatus
  capabilities: string[]
  last_heartbeat?: string
  current_task_id?: string | null
  created_at: string
  updated_at: string
}

export interface Task {
  id: string
  title: string
  description?: string
  status: TaskStatus
  priority: TaskPriority
  agent_id?: string | null
  required_capabilities?: string[]
  progress?: number
  result?: Record<string, unknown>
  error?: string
  created_at: string
  updated_at: string
}

export interface Workflow {
  id: string
  name: string
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'
  steps: WorkflowStep[]
  created_at: string
  updated_at: string
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
  failed_at: string
  error: string
  retries: number
}

export interface CostItem {
  agent_id: string
  agent_name: string
  total_tokens: number
  total_cost_usd: number
  task_count: number
}

export interface MemoryItem {
  key: string
  size_bytes: number
  age_seconds: number
  value_preview?: unknown
}

export interface ResourceLock {
  resource_id: string
  agent_id: string
  acquired_at: string
  expires_at: string
  conflict?: boolean
}

export interface HealthResponse {
  status: 'ok' | 'degraded' | 'down'
  version?: string
  uptime_seconds?: number
}

export type TraceCategory = 'llm' | 'tool' | 'db' | 'http' | 'internal' | 'error'

export interface TraceSpan {
  id: string
  name: string
  category: TraceCategory
  duration_ms: number
  level: number
  started_at: string
  completed_at?: string
}
