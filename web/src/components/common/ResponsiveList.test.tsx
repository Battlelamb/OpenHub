import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import { ResponsiveList } from './ResponsiveList'

const renderSample = () =>
  render(
    <ResponsiveList>
      <ResponsiveList.Header>
        <tr>
          <th>Name</th>
          <th>Status</th>
        </tr>
      </ResponsiveList.Header>
      <ResponsiveList.Row>
        <ResponsiveList.Cell header>Test</ResponsiveList.Cell>
        <ResponsiveList.Cell>Online</ResponsiveList.Cell>
      </ResponsiveList.Row>
    </ResponsiveList>,
  )

describe('ResponsiveList', () => {
  let consoleError: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  afterEach(() => {
    consoleError.mockRestore()
  })

  it('renders a valid desktop table and mobile card list without React nesting warnings', () => {
    const { container } = renderSample()

    expect(screen.getByText('Name')).toBeInTheDocument()
    expect(consoleError).not.toHaveBeenCalled()

    const table = container.querySelector('table')
    expect(table).not.toBeNull()
    expect(table?.querySelector('thead tr th')?.textContent).toBe('Name')
    expect(table?.querySelector('tbody tr td')?.textContent).toBe('Test')
    expect(table?.querySelector('tbody > div')).toBeNull()
    expect(table?.querySelector('tr > div')).toBeNull()

    const mobileList = container.querySelector('[data-responsive-list-mobile]')
    expect(mobileList).not.toBeNull()
    expect(mobileList?.querySelector('td')).toBeNull()
    expect(within(mobileList as HTMLElement).getByText('Test')).toBeInTheDocument()
    expect(within(mobileList as HTMLElement).getByText('Online')).toBeInTheDocument()
  })
})
