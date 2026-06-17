import { useState, useCallback, useMemo } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { DragDropContext, type DropResult } from '@hello-pangea/dnd'
import { toast } from 'sonner'
import { KanbanColumn } from './KanbanColumn'
import { useTasks, useTransitionTaskStatus } from '@/hooks/queries/useTasks'
import { TaskCreateForm } from '@/components/forms/TaskCreateForm'
import { ApiError } from '@/lib/api-client'
import {
  Inbox,
  Hand,
  PlayCircle,
  Clock3,
  CheckCircle2,
  XCircle,
  LayoutGrid,
  Ban,
  Loader2,
} from 'lucide-react'
import type { Task, TaskStatus } from '@/types/entities'

const COLUMNS: {
  id: TaskStatus
  title: string
  icon: React.ReactNode
  color: string
}[] = [
  { id: 'queued', title: 'Queued', icon: <Inbox className="h-4 w-4" />, color: 'text-zinc-400' },
  { id: 'claimed', title: 'Claimed', icon: <Hand className="h-4 w-4" />, color: 'text-violet-400' },
  { id: 'running', title: 'Running', icon: <PlayCircle className="h-4 w-4" />, color: 'text-sky-400' },
  { id: 'waiting_approval', title: 'Waiting approval', icon: <Clock3 className="h-4 w-4" />, color: 'text-amber-400' },
  { id: 'completed', title: 'Completed', icon: <CheckCircle2 className="h-4 w-4" />, color: 'text-emerald-400' },
  { id: 'failed', title: 'Failed', icon: <XCircle className="h-4 w-4" />, color: 'text-red-400' },
  { id: 'cancelled', title: 'Cancelled', icon: <Ban className="h-4 w-4" />, color: 'text-amber-400' },
]

export function KanbanBoard() {
  const navigate = useNavigate()
  const { data: tasks, isLoading } = useTasks()
  const transitionStatus = useTransitionTaskStatus()
  const [pendingTaskId, setPendingTaskId] = useState<string | null>(null)

  // Group tasks by status
  const columns = useMemo(() => {
    const grouped: Record<string, Task[]> = {}
    for (const col of COLUMNS) {
      grouped[col.id] = []
    }
    for (const task of tasks ?? []) {
      if (grouped[task.status]) {
        grouped[task.status].push(task)
      }
    }
    // Sort each column by priority (lower = higher priority) then by updated_at
    for (const col of COLUMNS) {
      grouped[col.id].sort((a, b) => {
        if (a.priority !== b.priority) return a.priority - b.priority
        return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
      })
    }
    return grouped
  }, [tasks])

  const handleTaskClick = useCallback((task: Task) => {
    navigate({
      to: '/tasks/$taskId',
      params: { taskId: task.id },
    })
  }, [navigate])

  const handleDragEnd = useCallback(
    (result: DropResult) => {
      const { destination, source, draggableId } = result
      if (!destination) return
      if (destination.droppableId === source.droppableId && destination.index === source.index) return
      if (transitionStatus.isPending) {
        toast.warning('Status update already in progress')
        return
      }

      const nextStatus = destination.droppableId as TaskStatus
      setPendingTaskId(draggableId)
      transitionStatus.mutate(
        {
          taskId: draggableId,
          status: nextStatus,
        },
        {
          onSuccess: (task) => {
            toast.success('Task status updated', {
              description: `${task.title} moved to ${task.status}`,
            })
          },
          onError: (error) => {
            if (error instanceof ApiError) {
              toast.error(error.problem.title || 'Status update failed', {
                description: error.problem.detail ?? `Could not move task to ${nextStatus}`,
              })
            } else {
              toast.error('Status update failed', {
                description: `Could not move task to ${nextStatus}`,
              })
            }
          },
          onSettled: () => setPendingTaskId(null),
        }
      )
    },
    [transitionStatus]
  )
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64 text-zinc-500">
        <div className="animate-pulse text-sm">Loading tasks...</div>
      </div>
    )
  }

  return (
    <>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <LayoutGrid className="h-5 w-5 text-emerald-500" />
          <h1 className="text-xl font-semibold text-zinc-50">Tasks</h1>
          <span className="text-xs text-zinc-600 bg-zinc-800 px-2 py-0.5 rounded-full font-mono">
            {tasks?.length ?? 0} total
          </span>
        </div>
        <div className="flex items-center gap-3">
          {transitionStatus.isPending && (
            <span className="inline-flex items-center gap-1 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-1 text-xs text-emerald-300">
              <Loader2 className="h-3 w-3 animate-spin" />
              Updating status
            </span>
          )}
          <TaskCreateForm />
        </div>
      </div>

      {/* Kanban Board */}
      <DragDropContext onDragEnd={handleDragEnd}>
        <div className="grid grid-cols-1 gap-4 overflow-x-auto pb-4 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-7">
          {COLUMNS.map((col) => (
            <KanbanColumn
              key={col.id}
              id={col.id}
              title={col.title}
              icon={col.icon}
              color={col.color}
              tasks={columns[col.id] ?? []}
              onTaskClick={handleTaskClick}
              pendingTaskId={pendingTaskId}
              isTransitioning={transitionStatus.isPending}
            />
          ))}
        </div>
      </DragDropContext>

    </>
  )
}
