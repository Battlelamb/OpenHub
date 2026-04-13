import { create } from 'zustand'

export interface AuthUser {
  id: string
  name: string
  role: 'admin' | 'agent' | 'viewer'
}

interface AuthState {
  token: string | null
  refreshToken: string | null
  expiresAt: number | null
  user: AuthUser | null
  setSession: (token: string, refreshToken: string, expiresIn: number, user: AuthUser) => void
  clear: () => void
  isExpired: () => boolean
}

export const useAuthStore = create<AuthState>((set, get) => ({
  token: null,
  refreshToken: null,
  expiresAt: null,
  user: null,
  setSession: (token, refreshToken, expiresIn, user) =>
    set({
      token,
      refreshToken,
      expiresAt: Date.now() + expiresIn * 1000,
      user,
    }),
  clear: () => set({ token: null, refreshToken: null, expiresAt: null, user: null }),
  isExpired: () => {
    const exp = get().expiresAt
    return exp === null || exp < Date.now()
  },
}))
