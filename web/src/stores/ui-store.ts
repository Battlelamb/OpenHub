import { create } from 'zustand'

export type Theme = 'dark' | 'light'
export type Language = 'en' | 'tr'
export type WsStatus = 'idle' | 'connecting' | 'connected' | 'reconnecting' | 'disconnected'

interface UIState {
  theme: Theme
  language: Language
  sidebarCollapsed: boolean
  wsStatus: WsStatus
  setTheme: (theme: Theme) => void
  toggleTheme: () => void
  setLanguage: (language: Language) => void
  toggleSidebar: () => void
  setWsStatus: (status: WsStatus) => void
}

export const useUIStore = create<UIState>((set) => ({
  theme: 'dark',
  language: 'en',
  sidebarCollapsed: false,
  wsStatus: 'idle',
  setTheme: (theme) => set({ theme }),
  toggleTheme: () => set((s) => ({ theme: s.theme === 'dark' ? 'light' : 'dark' })),
  setLanguage: (language) => set({ language }),
  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
  setWsStatus: (wsStatus) => set({ wsStatus }),
}))
