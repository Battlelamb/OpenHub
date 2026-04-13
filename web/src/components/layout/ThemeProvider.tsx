import { ReactNode } from 'react'
import { useTheme } from '@/hooks/useTheme'

export function ThemeProvider({ children }: { children: ReactNode }) {
  useTheme()
  return <>{children}</>
}
