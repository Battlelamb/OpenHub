import { createRoute, Link } from '@tanstack/react-router'
import { Route as parentRoute } from '../../_authed'
import { ArrowLeft, GitBranch } from 'lucide-react'
import { useTask } from '@/hooks/queries/useTasks'
import { TaskStatusBadge } from '@/components/common/StatusBadge'
import { WorkflowCanvas } from '@/components/canvas/WorkflowCanvas'

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
    </div>
  )
}
