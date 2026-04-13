import { createRoute } from '@tanstack/react-router'
import { Route as rootRoute } from './__root'

export const Route = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  component: IndexComponent,
})

function IndexComponent() {
  return (
    <div className="p-8">
      <h1 className="text-2xl font-semibold">OpenHub Command Center</h1>
      <p className="text-sm text-muted-foreground">Scaffold online.</p>
    </div>
  )
}
