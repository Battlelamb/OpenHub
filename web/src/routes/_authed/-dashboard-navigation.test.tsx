import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import type { ComponentType, ReactNode } from 'react'
import '@/i18n'

vi.mock('@tanstack/react-router', async () => {
  const actual = await vi.importActual<typeof import('@tanstack/react-router')>('@tanstack/react-router')

  return {
    ...actual,
    Link: ({ to, children, className }: { to: string; children: ReactNode; className?: string }) => (
      <a href={to} className={className}>
        {children}
      </a>
    ),
  }
})

vi.mock('@/components/common/SemanticSearchPanel', () => ({
  SemanticSearchPanel: () => <div data-testid="semantic-search-panel" />,
}))

import { Route } from './index'

const DashboardRouteComponent = Route.options.component as ComponentType

describe('Dashboard navigation cards', () => {
  it('links the Tasks card to the live task board', () => {
    render(<DashboardRouteComponent />)

    const taskCard = screen.getByRole('link', { name: /tasks coordinate agent tasks/i })
    expect(taskCard).toHaveAttribute('href', '/tasks')
    expect(screen.queryByText(/coming soon/i)).not.toBeInTheDocument()
  })
})
