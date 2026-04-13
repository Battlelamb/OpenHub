import { describe, it, expect, beforeEach } from 'vitest'
import { useAuthStore } from '@/stores/auth-store'

describe('LoginForm', () => {
  beforeEach(() => {
    useAuthStore.getState().clear()
  })

  it('stores session after setSession call', () => {
    useAuthStore.getState().setSession('jwt-abc', 'refresh-xyz', 900, { id: 'u1', name: 'admin', role: 'admin' })
    expect(useAuthStore.getState().token).toBe('jwt-abc')
    expect(useAuthStore.getState().user?.name).toBe('admin')
    expect(useAuthStore.getState().expiresAt).toBeGreaterThan(Date.now())
  })
})
