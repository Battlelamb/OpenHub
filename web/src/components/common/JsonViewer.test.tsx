import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { JsonViewer } from './JsonViewer'

describe('JsonViewer', () => {
  it('renders primitive string', () => {
    render(<JsonViewer value="hello" name="greeting" />)
    expect(screen.getByText(/greeting/)).toBeInTheDocument()
    expect(screen.getByText(/"hello"/)).toBeInTheDocument()
  })

  it('renders object with nested keys', () => {
    render(<JsonViewer value={{ foo: 'bar', n: 42 }} />)
    expect(screen.getByText(/foo:/)).toBeInTheDocument()
    expect(screen.getByText(/"bar"/)).toBeInTheDocument()
    expect(screen.getByText(/n:/)).toBeInTheDocument()
    expect(screen.getByText(/42/)).toBeInTheDocument()
  })

  it('renders array indices', () => {
    render(<JsonViewer value={['a', 'b']} />)
    expect(screen.getByText(/"a"/)).toBeInTheDocument()
    expect(screen.getByText(/"b"/)).toBeInTheDocument()
  })
})
