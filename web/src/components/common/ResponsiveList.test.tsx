import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ResponsiveList } from './ResponsiveList'

describe('ResponsiveList', () => {
  it('renders table header on md+ screens', () => {
    render(
      <ResponsiveList>
        <ResponsiveList.Header>
          <tr>
            <th>Name</th>
            <th>Status</th>
          </tr>
        </ResponsiveList.Header>
        <ResponsiveList.Row>
          <ResponsiveList.Cell>Test</ResponsiveList.Cell>
          <ResponsiveList.Cell>Online</ResponsiveList.Cell>
        </ResponsiveList.Row>
      </ResponsiveList>,
    )
    expect(screen.getByText('Name')).toBeInTheDocument()
  })
})
