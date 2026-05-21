import { Droppable } from '@hello-pangea/dnd'
import { KanbanCard } from './KanbanCard'
import type { Task, TaskStatus } from '@/types/entities'

interface KanbanColumnProps {
  id: TaskStatus
  title: string
  icon: React.ReactNode
  color: string
  tasks: Task[]
  onTaskClick: (task: Task) => void
  pendingTaskId?: string | null
  isTransitioning?: boolean
}

export function KanbanColumn({
  id,
  title,
  icon,
  color,
  tasks,
  onTaskClick,
  pendingTaskId,
  isTransitioning = false,
}: KanbanColumnProps) {
  return (
    <div className="flex flex-col min-w-[200px] flex-1" data-testid={`kanban-column-${id}`}>
      {/* Column header */}
      <div className="flex items-center gap-2 mb-3 px-1">
        <span className={color}>{icon}</span>
        <h3 className="text-sm font-semibold text-zinc-300 uppercase tracking-wider">
          {title}
        </h3>
        <span className="ml-auto text-xs font-mono text-zinc-600 bg-zinc-800/80 px-2 py-0.5 rounded-full">
          {tasks.length}
        </span>
      </div>

      {/* Droppable area */}
      <Droppable droppableId={id}>
        {(provided, snapshot) => (
          <div
            ref={provided.innerRef}
            {...provided.droppableProps}
            className={`
              flex-1 rounded-xl p-2 space-y-2 min-h-[200px] transition-colors duration-200
              ${isTransitioning ? 'opacity-80' : ''}
              ${snapshot.isDraggingOver
                ? 'bg-emerald-500/5 border-2 border-dashed border-emerald-500/20'
                : 'bg-zinc-900/40 border-2 border-transparent'
              }
            `}
            data-testid={`kanban-dropzone-${id}`}
          >
            {tasks.map((task, index) => (
              <KanbanCard
                key={task.id}
                task={task}
                index={index}
                onClick={onTaskClick}
                isPending={pendingTaskId === task.id}
              />
            ))}
            {provided.placeholder}

            {/* Empty state */}
            {tasks.length === 0 && !snapshot.isDraggingOver && (
              <div className="flex items-center justify-center h-24 text-xs text-zinc-700">
                Drop tasks here
              </div>
            )}
          </div>
        )}
      </Droppable>
    </div>
  )
}
