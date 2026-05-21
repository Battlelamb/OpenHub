import { createRoute } from '@tanstack/react-router'
import { Route as parentRoute } from '../../_authed'
import { KanbanBoard } from '@/components/kanban/KanbanBoard'

export const Route = createRoute({
  getParentRoute: () => parentRoute,
  path: '/tasks',
  component: TasksPage,
})

function TasksPage() {
  return (
    <div className="p-4">
      <KanbanBoard />
    </div>
  )
}
