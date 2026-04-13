import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useAuthStore } from './auth-store'

describe('useAuthStore', () => {
  beforeEach(() => {
    useAuthStore.getState().clear()
  })

  it('stores session in memory on setSession', () => {
    useAuthStore.getState().setSession('tok', 'reftok', 900, { id: 'u1', name: 'admin', role: 'admin' })
    expect(useAuthStore.getState().token).toBe('tok')
    expect(useAuthStore.getState().user?.name).toBe('admin')
  })

  it('sets expiresAt to now + expires_in*1000', () => {
    const before = Date.now()
    useAuthStore.getState().setSession('t', 'r', 900, { id: 'u1', name: 'a', role: 'admin' })
    const exp = useAuthStore.getState().expiresAt!
    expect(exp).toBeGreaterThanOrEqual(before + 900_000)
    expect(exp).toBeLessThanOrEqual(before + 901_000)
  })

  it('clear() wipes all fields', () => {
    useAuthStore.getState().setSession('t', 'r', 900, { id: 'u1', name: 'a', role: 'admin' })
    useAuthStore.getState().clear()
    const s = useAuthStore.getState()
    expect(s.token).toBeNull()
    expect(s.user).toBeNull()
    expect(s.expiresAt).toBeNull()
  })

  it('does NOT write to localStorage (UI-01 / D-14)', () => {
    const spy = vi.spyOn(Storage.prototype, 'setItem')
    useAuthStore.getState().setSession('t', 'r', 900, { id: 'u1', name: 'a', role: 'admin' })
    const authCalls = spy.mock.calls.filter(([key]) =>
      String(key).toLowerCase().includes('token') || String(key).toLowerCase().includes('auth'),
    )
    expect(authCalls).toHaveLength(0)
    spy.mockRestore()
  })

  it('isExpired returns true when expiresAt in past', () => {
    useAuthStore.setState({ token: 't', expiresAt: Date.now() - 1000, user: null, refreshToken: null })
    expect(useAuthStore.getState().isExpired()).toBe(true)
  })
})
