import { useEffect, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { useAuthStore } from '@/stores/auth-store'
import { useUIStore } from '@/stores/ui-store'
import { qk } from '@/lib/query-keys'
import type { Agent, Task } from '@/types/entities'

type WSEvent =
  | { event: 'connected'; data: { client_id: string } }
  | { event: 'agent_status_changed'; timestamp: string; data: { agent_id: string; status: Agent['status'] } }
  | { event: 'acn_agent_registered'; timestamp: string; data: { agent_id: string; agent_name?: string; node_name?: string } }
  | { event: 'acn_node_registered'; timestamp: string; data: { node_id: string; node_name?: string } }
  | { event: 'acn_node_heartbeat'; timestamp: string; data: { node_id: string; agent_id?: string | null } }
  | { event: 'task_status_changed'; timestamp: string; data: { task_id: string; status: Task['status'] } }
  | { event: 'task_progress'; timestamp: string; data: { task_id: string; progress: number } }
  | { event: 'workflow_step_changed'; timestamp: string; data: { workflow_id: string; step_id: string; status: string } }
  | { event: 'heartbeat'; timestamp: string; data: { agent_id: string } }
  | { event: 'metadata_changed'; timestamp: string; data: { entity: string; id: string } }
  | { event: 'token_expiring'; timestamp: string; data: { seconds_remaining: number } }
  | { event: 'error'; timestamp: string; data: { code: string; message: string } }

const MAX_DELAY = 30_000

export function buildWsUrl(): string {
  const proto = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = typeof window !== 'undefined' ? window.location.host : 'localhost:5173'
  return `${proto}//${host}/v1/ws/ui`
}

export function handleEvent(qc: ReturnType<typeof useQueryClient>, msg: WSEvent) {
  switch (msg.event) {
    case 'agent_status_changed':
      qc.setQueryData<Agent[]>(qk.agents.all, (prev) =>
        prev?.map((a) => (a.id === msg.data.agent_id ? { ...a, status: msg.data.status } : a)),
      )
      qc.setQueryData<Agent | undefined>(qk.agents.detail(msg.data.agent_id), (prev) =>
        prev ? { ...prev, status: msg.data.status } : prev,
      )
      break
    case 'acn_agent_registered':
    case 'acn_node_registered':
    case 'acn_node_heartbeat':
      qc.invalidateQueries({ queryKey: qk.agents.all })
      break
    case 'task_status_changed':
      qc.setQueryData<Task[]>(qk.tasks.all, (prev) =>
        prev?.map((t) => (t.id === msg.data.task_id ? { ...t, status: msg.data.status } : t)),
      )
      qc.setQueryData<Task | undefined>(qk.tasks.detail(msg.data.task_id), (prev) =>
        prev ? { ...prev, status: msg.data.status } : prev,
      )
      qc.invalidateQueries({ queryKey: qk.tasks.all })
      break
    case 'task_progress':
      qc.setQueryData<Task | undefined>(qk.tasks.detail(msg.data.task_id), (prev) =>
        prev ? { ...prev, progress: msg.data.progress } : prev,
      )
      break
    case 'workflow_step_changed':
      qc.invalidateQueries({ queryKey: qk.workflows.detail(msg.data.workflow_id) })
      break
    case 'heartbeat':
      qc.invalidateQueries({ queryKey: qk.agents.all, refetchType: 'none' })
      break
    case 'metadata_changed':
      qc.invalidateQueries({ queryKey: [msg.data.entity] })
      break
    case 'token_expiring':
      toast.warning('Session ending soon', {
        description: `${msg.data.seconds_remaining}s remaining`,
      })
      break
    case 'error':
      toast.error(msg.data.code, { description: msg.data.message })
      break
  }
}

export function useWebSocketSync() {
  const queryClient = useQueryClient()
  const token = useAuthStore((s) => s.token)
  const setWsStatus = useUIStore((s) => s.setWsStatus)
  const wsRef = useRef<WebSocket | null>(null)
  const attemptRef = useRef(0)
  const timerRef = useRef<number | null>(null)

  useEffect(() => {
    if (!token) {
      setWsStatus('idle')
      return
    }

    let cancelled = false

    const connect = () => {
      if (cancelled) return
      const url = buildWsUrl()
      const ws = new WebSocket(url)
      wsRef.current = ws
      setWsStatus('connecting')

      ws.onopen = () => {
        ws.send(JSON.stringify({ type: 'auth', token }))
      }

      ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data) as WSEvent
          if (msg.event === 'connected') {
            setWsStatus('connected')
            attemptRef.current = 0
            queryClient.invalidateQueries()
          } else {
            handleEvent(queryClient, msg)
          }
        } catch {
          // Ignore parse errors
        }
      }

      ws.onclose = () => {
        setWsStatus('reconnecting')
        const delay = Math.min(MAX_DELAY, 1000 * 2 ** attemptRef.current) * (0.5 + Math.random() * 0.5)
        attemptRef.current += 1
        timerRef.current = window.setTimeout(connect, delay)
      }

      ws.onerror = () => {
        ws.close()
      }
    }

    connect()

    return () => {
      cancelled = true
      if (timerRef.current) clearTimeout(timerRef.current)
      if (wsRef.current) wsRef.current.close()
    }
  }, [token, queryClient, setWsStatus])
}
