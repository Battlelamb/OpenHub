import { useEffect } from 'react'
import { useUIStore } from '@/stores/ui-store'

export function useTheme() {
  const theme = useUIStore((s) => s.theme)
  useEffect(() => {
    const root = document.documentElement
    root.classList.toggle('dark', theme === 'dark')
  }, [theme])
}
