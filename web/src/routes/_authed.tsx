import { createRoute, Outlet } from '@tanstack/react-router'
import { Route as rootRoute } from './__root'
import { useAuthStore } from '@/stores/auth-store'
import { AppShell } from '@/components/layout/AppShell'

export const Route = createRoute({
  getParentRoute: () => rootRoute,
  id: '_authed',
  beforeLoad: ({ location }) => {
    const { token, expiresAt } = useAuthStore.getState()
    if (!token || (expiresAt && expiresAt < Date.now())) {
      throw new Error(`redirect:/login?redirect=${encodeURIComponent(location.href)}`)
    }
  },
  component: () => (
    <AppShell>
      <Outlet />
    </AppShell>
  ),
})
