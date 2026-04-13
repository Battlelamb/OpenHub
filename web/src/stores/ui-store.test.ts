import { describe, it, expect, beforeEach } from 'vitest'
import { useUIStore } from './ui-store'

describe('useUIStore', () => {
  beforeEach(() => {
    useUIStore.setState({
      theme: 'dark',
      language: 'en',
      sidebarCollapsed: false,
      wsStatus: 'idle',
    })
  })

  it('defaults to dark theme per D-02', () => {
    expect(useUIStore.getState().theme).toBe('dark')
  })

  it('toggles theme dark <-> light', () => {
    useUIStore.getState().toggleTheme()
    expect(useUIStore.getState().theme).toBe('light')
    useUIStore.getState().toggleTheme()
    expect(useUIStore.getState().theme).toBe('dark')
  })

  it('sets ws status', () => {
    useUIStore.getState().setWsStatus('reconnecting')
    expect(useUIStore.getState().wsStatus).toBe('reconnecting')
  })

  it('toggles sidebar collapsed', () => {
    expect(useUIStore.getState().sidebarCollapsed).toBe(false)
    useUIStore.getState().toggleSidebar()
    expect(useUIStore.getState().sidebarCollapsed).toBe(true)
  })

  it('sets language', () => {
    useUIStore.getState().setLanguage('tr')
    expect(useUIStore.getState().language).toBe('tr')
  })
})
