import { createRoute } from '@tanstack/react-router'
import { Route as parentRoute } from '../_authed'

export const Route = createRoute({
  getParentRoute: () => parentRoute,
  path: '/traces',
  component: TracesPage,
})

function TracesPage() {
  return (
    <div className="p-6">
      <h1 className="mb-4 text-2xl font-semibold text-zinc-50">Traces</h1>
      <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-6 text-center">
        <div className="text-lg font-semibold text-zinc-50">
          Select a task to view its trace
        </div>
        <div className="mt-2 text-sm text-zinc-400">
          Distributed traces show tool calls, sub-steps, and timing.
        </div>
      </div>
    </div>
  )
}
