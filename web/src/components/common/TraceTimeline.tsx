import { cn } from '@/lib/utils'

interface TraceSpan {
  id: string
  name: string
  category: 'llm' | 'tool' | 'db' | 'http' | 'internal' | 'error'
  duration_ms: number
  level: number
  started_at: string
  completed_at?: string
}

interface TraceTimelineProps {
  spans?: TraceSpan[]
}

const categoryColors: Record<TraceSpan['category'], string> = {
  llm: 'violet-400',
  tool: 'sky-400',
  db: 'amber-400',
  http: 'emerald-400',
  internal: 'zinc-500',
  error: 'red-500',
}

export function TraceTimeline({ spans }: TraceTimelineProps) {
  if (!spans || spans.length === 0) {
    return (
      <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-6">
        <h3 className="text-lg font-medium text-zinc-50">No trace available</h3>
        <p className="text-sm text-zinc-400 mt-2">Traces appear once the task is claimed and the agent emits spans.</p>
      </div>
    )
  }

  const maxDuration = Math.max(...spans.map((s) => s.duration_ms), 1)

  return (
    <div className="space-y-2">
      {spans.map((span) => (
        <div
          key={span.id}
          className="flex items-center gap-2"
          style={{ paddingLeft: `${span.level * 16}px` }}
        >
          <div className="flex-shrink-0 w-4">
            <div className={cn(`h-2 w-2 rounded-full bg-${categoryColors[span.category]}`)} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between gap-4">
              <span className="text-sm text-zinc-300 truncate">{span.name}</span>
              <span className="text-xs text-zinc-500">{span.duration_ms}ms</span>
            </div>
            <div className="h-1 bg-zinc-800 rounded-full mt-1">
              <div
                className={cn(`h-full rounded-full bg-${categoryColors[span.category]}`)}
                style={{ width: `${(span.duration_ms / maxDuration) * 100}%` }}
              />
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
