import { cn } from '@/lib/utils'
import type { AgentStatus, TaskStatus } from '@/types/entities'

const agentTokens: Record<AgentStatus, { dot: string; bg: string; text: string }> = {
  online: { dot: 'bg-emerald-500', bg: 'bg-emerald-500/10', text: 'text-emerald-400' },
  idle: { dot: 'bg-amber-500', bg: 'bg-amber-500/10', text: 'text-amber-400' },
  offline: { dot: 'bg-zinc-500', bg: 'bg-zinc-500/10', text: 'text-zinc-400' },
  error: { dot: 'bg-red-500', bg: 'bg-red-500/10', text: 'text-red-400' },
}

const taskTokens: Record<TaskStatus, { dot: string; text: string; pulse?: boolean; strike?: boolean }> = {
  queued: { dot: 'bg-zinc-400', text: 'text-zinc-400' },
  claimed: { dot: 'bg-violet-400', text: 'text-violet-400' },
  running: { dot: 'bg-sky-400', text: 'text-sky-400', pulse: true },
  waiting_approval: { dot: 'bg-amber-400', text: 'text-amber-400', pulse: true },
  completed: { dot: 'bg-emerald-500', text: 'text-emerald-500' },
  failed: { dot: 'bg-red-500', text: 'text-red-500' },
  cancelled: { dot: 'bg-zinc-500', text: 'text-zinc-500', strike: true },
}

interface StatusBadgeProps {
  status: AgentStatus | TaskStatus
  variant?: 'agent' | 'task'
}

export function AgentStatusBadge({ status }: { status: AgentStatus }) {
  const tokens = agentTokens[status]
  return (
    <span className={cn('inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium', tokens.bg, tokens.text)}>
      <span className={cn('size-1.5 rounded-full', tokens.dot)} />
      {status}
    </span>
  )
}

export function TaskStatusBadge({ status }: { status: TaskStatus }) {
  const tokens = taskTokens[status]
  return (
    <span className={cn('inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium', tokens.text, tokens.strike && 'line-through')}>
      <span className={cn('size-1.5 rounded-full', tokens.dot, tokens.pulse && 'animate-pulse')} />
      {status}
    </span>
  )
}

export function StatusBadge({ status, variant = 'agent' }: StatusBadgeProps) {
  if (variant === 'task') {
    return <TaskStatusBadge status={status as TaskStatus} />
  }
  return <AgentStatusBadge status={status as AgentStatus} />
}
