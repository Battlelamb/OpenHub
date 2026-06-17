import { createRoute, Link } from '@tanstack/react-router'
import { Route as parentRoute } from '../../_authed'
import { Activity, ArrowLeft, BarChart3, CalendarClock, FileText, GitBranch, Info, RotateCcw } from 'lucide-react'
import { useTask, useTaskTimeline } from '@/hooks/queries/useTasks'
import { TaskStatusBadge } from '@/components/common/StatusBadge'
import { WorkflowCanvas } from '@/components/canvas/WorkflowCanvas'
import { JsonViewer } from '@/components/common/JsonViewer'
import type { Task, TaskTimelineItem } from '@/types/entities'

export const Route = createRoute({
  getParentRoute: () => parentRoute,
  path: '/tasks/$taskId',
  component: TaskDetailPage,
})

function TaskDetailPage() {
  const { taskId } = Route.useParams()
  return <TaskWorkflowDetail taskId={taskId} />
}

export function TaskWorkflowDetail({ taskId }: { taskId: string }) {
  const { data: task, isLoading } = useTask(taskId)
  const {
    data: timeline = [],
    isLoading: isTimelineLoading,
    isError: isTimelineError,
  } = useTaskTimeline(taskId)

  if (isLoading) {
    return (
      <div className="flex h-[calc(100vh-3.5rem)] items-center justify-center text-sm text-zinc-500">
        Loading workflow...
      </div>
    )
  }

  if (!task) {
    return <div className="p-8 text-zinc-400">Task not found</div>
  }

  return (
    <div className="flex h-[calc(100vh-3.5rem)] min-h-[720px] flex-col p-4">
      <div className="mb-4 flex items-center justify-between gap-4">
        <div className="min-w-0">
          <Link
            to="/tasks"
            className="mb-2 inline-flex items-center gap-1 text-sm text-zinc-400 hover:text-zinc-200"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to Kanban
          </Link>
          <div className="flex min-w-0 items-center gap-3">
            <GitBranch className="h-5 w-5 shrink-0 text-emerald-500" />
            <h1 className="truncate text-2xl font-semibold text-zinc-50">{task.title}</h1>
            <TaskStatusBadge status={task.status} />
          </div>
          {task.description ? (
            <p className="mt-2 max-w-3xl text-sm text-zinc-400">{task.description}</p>
          ) : null}
        </div>
        <div className="hidden shrink-0 rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2 text-xs text-zinc-500 md:block">
          Task ID <span className="font-mono text-zinc-300">{task.id}</span>
        </div>
      </div>

      <WorkflowCanvas task={task} open mode="embedded" onClose={() => {}} />

      <TaskEvidenceTimelinePanel
        timeline={timeline}
        isLoading={isTimelineLoading}
        isError={isTimelineError}
      />

      <TaskDetailInfoPanel task={task} />
    </div>
  )
}

function TaskEvidenceTimelinePanel({
  timeline,
  isLoading,
  isError,
}: {
  timeline: TaskTimelineItem[]
  isLoading: boolean
  isError: boolean
}) {
  const evidenceCount = timeline.filter((item) => item.source === 'evidence').length
  const traceCount = timeline.filter((item) => item.source === 'trace').length

  return (
    <section className="mt-4 rounded-xl border border-zinc-800 bg-zinc-950/80 p-4" aria-label="Task evidence timeline">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-emerald-400" />
          <div>
            <h2 className="text-sm font-semibold text-zinc-100">Evidence Timeline</h2>
            <p className="mt-1 text-xs text-zinc-500">
              Private evidence and trace events for this task, newest context preserved below the canvas.
            </p>
          </div>
        </div>
        <div className="flex gap-2 text-xs">
          <TimelinePill label="Evidence" value={evidenceCount} />
          <TimelinePill label="Trace" value={traceCount} />
        </div>
      </div>

      {isLoading ? (
        <TimelineEmptyState title="Loading timeline..." description="Collecting task evidence and trace events." />
      ) : isError ? (
        <TimelineEmptyState title="Evidence timeline unavailable" description="The task is loaded, but timeline evidence could not be fetched." />
      ) : timeline.length === 0 ? (
        <TimelineEmptyState title="No timeline evidence yet" description="Commands, files, artifacts, logs, and trace events will appear here as agents work." />
      ) : (
        <ol className="space-y-3">
          {timeline.map((item) => (
            <TaskTimelineRow key={`${item.source}:${item.id}`} item={item} />
          ))}
        </ol>
      )}
    </section>
  )
}

function TaskTimelineRow({ item }: { item: TaskTimelineItem }) {
  const hasContent = item.content && Object.keys(item.content).length > 0
  const artifactIds = item.artifact_ids ?? []

  return (
    <li className="rounded-lg border border-zinc-800 bg-zinc-900/60 p-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <span className={timelineSourceClass(item.source)}>{item.source}</span>
            <span className="rounded-full border border-zinc-700 px-2 py-0.5 text-xs font-medium text-zinc-300">
              {item.item_type}
            </span>
            {item.outcome ? (
              <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-xs font-medium text-emerald-200">
                {item.outcome}
              </span>
            ) : null}
          </div>
          <h3 className="text-sm font-semibold text-zinc-100">{item.title}</h3>
          {item.summary ? <p className="mt-1 text-sm text-zinc-400">{item.summary}</p> : null}
        </div>
        <div className="shrink-0 text-right text-xs text-zinc-500">
          <div>{formatDateTime(item.occurred_at)}</div>
          {item.duration_ms != null ? <div className="mt-1 font-mono text-zinc-300">{formatDuration(item.duration_ms)}</div> : null}
        </div>
      </div>

      <div className="mt-3 grid gap-3 text-xs text-zinc-400 lg:grid-cols-[0.85fr_1.15fr]">
        <div className="space-y-2">
          {item.actor_id ? <TimelineMeta icon={<GitBranch className="h-3.5 w-3.5" />} label="Actor" value={item.actor_id} /> : null}
          {item.trace_id ? <TimelineMeta icon={<Activity className="h-3.5 w-3.5" />} label="Trace" value={item.trace_id} /> : null}
          {artifactIds.length > 0 ? (
            <div className="rounded-md border border-zinc-800 bg-zinc-950/70 p-2">
              <div className="mb-1 flex items-center gap-1.5 font-medium uppercase tracking-wide text-zinc-500">
                <FileText className="h-3.5 w-3.5" />
                Artifacts
              </div>
              <ul className="space-y-1">
                {artifactIds.map((artifactId) => (
                  <li key={artifactId} className="break-all font-mono text-zinc-300">
                    {artifactId}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
        {hasContent ? (
          <div className="rounded-md border border-zinc-800 bg-zinc-950/70 p-2">
            <div className="mb-2 flex items-center gap-1.5 font-medium uppercase tracking-wide text-zinc-500">
              <FileText className="h-3.5 w-3.5" />
              Payload
            </div>
            <JsonViewer value={item.content} />
          </div>
        ) : null}
      </div>
    </li>
  )
}

function TimelineMeta({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="rounded-md border border-zinc-800 bg-zinc-950/70 p-2">
      <div className="mb-1 flex items-center gap-1.5 font-medium uppercase tracking-wide text-zinc-500">
        {icon}
        {label}
      </div>
      <div className="break-all font-mono text-zinc-300">{value}</div>
    </div>
  )
}

function TimelinePill({ label, value }: { label: string; value: number }) {
  return (
    <span className="rounded-full border border-zinc-800 bg-zinc-900 px-2 py-1 text-zinc-300">
      {label}: <span className="font-mono text-zinc-100">{value}</span>
    </span>
  )
}

function TimelineEmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="rounded-lg border border-dashed border-zinc-800 bg-zinc-900/40 p-4">
      <p className="text-sm font-medium text-zinc-200">{title}</p>
      <p className="mt-1 text-sm text-zinc-500">{description}</p>
    </div>
  )
}

function timelineSourceClass(source: TaskTimelineItem['source']) {
  const base = 'rounded-full border px-2 py-0.5 text-xs font-medium uppercase tracking-wide'
  if (source === 'evidence') return `${base} border-emerald-500/30 bg-emerald-500/10 text-emerald-200`
  return `${base} border-sky-500/30 bg-sky-500/10 text-sky-200`
}

function TaskDetailInfoPanel({ task }: { task: Task }) {
  const capabilities = task.required_capabilities ?? []
  const retryBudget = `${task.retry_count ?? 0} / ${task.max_retries ?? 0}`
  const completedLabel = task.completed_at ? formatDateTime(task.completed_at) : 'Not completed yet'
  const ownerLabel = task.agent_id ?? 'Unassigned'

  return (
    <section className="mt-4 grid gap-4 lg:grid-cols-[1.3fr_0.9fr_0.9fr]" aria-label="Task detail information">
      <div className="rounded-xl border border-zinc-800 bg-zinc-950/80 p-4">
        <div className="mb-3 flex items-center gap-2">
          <Info className="h-4 w-4 text-emerald-400" />
          <h2 className="text-sm font-semibold text-zinc-100">Task Details</h2>
        </div>
        <dl className="grid gap-3 text-sm sm:grid-cols-2">
          <InfoRow label="Type" value={task.task_type ?? 'unknown'} />
          <InfoRow label="Priority" value={`P${task.priority}`} />
          <InfoRow label="Owner" value={ownerLabel} mono={ownerLabel !== 'Unassigned'} />
          <InfoRow label="Status" value={task.status} />
        </dl>
        <div className="mt-4">
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-zinc-500">Requested capabilities</p>
          {capabilities.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {capabilities.map((capability) => (
                <span
                  key={capability}
                  className="rounded-full border border-emerald-500/20 bg-emerald-500/10 px-2.5 py-1 text-xs text-emerald-200"
                >
                  {capability}
                </span>
              ))}
            </div>
          ) : (
            <p className="text-sm text-zinc-500">No explicit capability requirement.</p>
          )}
        </div>
      </div>

      <div className="rounded-xl border border-zinc-800 bg-zinc-950/80 p-4">
        <div className="mb-3 flex items-center gap-2">
          <BarChart3 className="h-4 w-4 text-sky-400" />
          <h2 className="text-sm font-semibold text-zinc-100">Statistics</h2>
        </div>
        <dl className="space-y-3 text-sm">
          <InfoRow label="Retry budget" value={retryBudget} />
          <InfoRow label="Completed" value={completedLabel} />
          <InfoRow label="Last error" value={task.error ?? 'None'} />
        </dl>
      </div>

      <div className="rounded-xl border border-zinc-800 bg-zinc-950/80 p-4">
        <div className="mb-3 flex items-center gap-2">
          <CalendarClock className="h-4 w-4 text-violet-400" />
          <h2 className="text-sm font-semibold text-zinc-100">System info</h2>
        </div>
        <dl className="space-y-3 text-sm">
          <InfoRow label="Created" value={formatDateTime(task.created_at)} />
          <InfoRow label="Updated" value={formatDateTime(task.updated_at)} />
          <InfoRow label="Created by" value={task.created_by ?? 'unknown'} mono />
        </dl>
        <div className="mt-4 flex items-center gap-2 rounded-lg border border-zinc-800 bg-zinc-900/70 px-3 py-2 text-xs text-zinc-400">
          <RotateCcw className="h-3.5 w-3.5" />
          Canvas remains the working surface; this panel is the operational context below it.
        </div>
      </div>
    </section>
  )
}

function InfoRow({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wide text-zinc-500">{label}</dt>
      <dd className={mono ? 'mt-1 break-all font-mono text-zinc-200' : 'mt-1 text-zinc-200'}>{value}</dd>
    </div>
  )
}

function formatDuration(value: number) {
  if (Number.isInteger(value)) return `${value}ms`
  return `${value.toFixed(1)}ms`
}

function formatDateTime(value?: string | null) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toISOString().slice(0, 16).replace('T', ' ') + ' UTC'
}
