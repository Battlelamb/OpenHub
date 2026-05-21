import { Draggable } from '@hello-pangea/dnd'
import { GripVertical, User, Clock, Zap, Loader2 } from 'lucide-react'
import type { Task } from '@/types/entities'

interface KanbanCardProps {
  task: Task
  index: number
  onClick: (task: Task) => void
  isPending?: boolean
}

const priorityColors: Record<number, string> = {
  1: 'bg-red-500/20 text-red-400 border-red-500/30',
  2: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  3: 'bg-zinc-500/20 text-zinc-400 border-zinc-500/30',
  4: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  5: 'bg-zinc-700/20 text-zinc-500 border-zinc-700/30',
}

const priorityLabels: Record<number, string> = {
  1: 'Critical',
  2: 'High',
  3: 'Normal',
  4: 'Low',
  5: 'Minimal',
}

export function KanbanCard({ task, index, onClick, isPending = false }: KanbanCardProps) {
  return (
    <Draggable draggableId={task.id} index={index}>
      {(provided, snapshot) => (
        <div
          ref={provided.innerRef}
          {...provided.draggableProps}
          className={`
            group relative rounded-lg border bg-zinc-900 p-3 cursor-pointer select-none
            transition-all duration-150
            ${isPending ? 'pointer-events-none border-emerald-500/40 opacity-70' : ''}
            ${snapshot.isDragging
              ? 'border-emerald-500/60 shadow-lg shadow-emerald-500/10 rotate-1 scale-[1.02] z-50'
              : 'border-zinc-800 hover:border-zinc-700 hover:bg-zinc-900/80'
            }
          `}
          onClick={() => onClick(task)}
          data-testid={`kanban-card-${task.id}`}
        >
          {isPending && (
            <div className="absolute inset-0 z-10 flex items-center justify-center rounded-lg bg-zinc-950/60 backdrop-blur-[1px]">
              <Loader2 className="h-4 w-4 animate-spin text-emerald-400" aria-label="Updating task status" />
            </div>
          )}

          {/* Drag handle */}
          <div
            {...provided.dragHandleProps}
            className="absolute left-1 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-40 hover:!opacity-80 cursor-grab active:cursor-grabbing p-1"
            data-testid={`kanban-drag-handle-${task.id}`}
          >
            <GripVertical className="h-3.5 w-3.5 text-zinc-400" />
          </div>

          {/* Title */}
          <h4 className="text-sm font-medium text-zinc-100 pl-4 pr-1 leading-snug line-clamp-2">
            {task.title}
          </h4>

          {/* Description preview */}
          {task.description && (
            <p className="text-xs text-zinc-500 mt-1 pl-4 line-clamp-1">
              {task.description}
            </p>
          )}

          {/* Footer row */}
          <div className="flex items-center gap-2 mt-2.5 pl-4 flex-wrap">
            {/* Priority badge */}
            <span className={`inline-flex items-center gap-1 text-[10px] font-medium px-1.5 py-0.5 rounded border ${priorityColors[task.priority] ?? priorityColors[3]}`}>
              <Zap className="h-2.5 w-2.5" />
              {priorityLabels[task.priority] ?? `P${task.priority}`}
            </span>

            {/* Agent */}
            {task.agent_id && (
              <span className="inline-flex items-center gap-1 text-[10px] text-zinc-500">
                <User className="h-2.5 w-2.5" />
                <span className="truncate max-w-[80px]">{task.agent_id}</span>
              </span>
            )}

            {/* Time */}
            <span className="inline-flex items-center gap-1 text-[10px] text-zinc-600 ml-auto">
              <Clock className="h-2.5 w-2.5" />
              {formatRelativeTime(task.updated_at)}
            </span>
          </div>
        </div>
      )}
    </Draggable>
  )
}

function formatRelativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const sec = Math.floor(diff / 1000)
  if (sec < 60) return `${sec}s`
  const min = Math.floor(sec / 60)
  if (min < 60) return `${min}m`
  const hr = Math.floor(min / 60)
  if (hr < 24) return `${hr}h`
  const d = Math.floor(hr / 24)
  return `${d}d`
}
