import { ReactNode } from 'react'
import { Sidebar } from './Sidebar'
import { Topbar } from './Topbar'
import { useWebSocketSync } from '@/hooks/useWebSocketSync'

export function AppShell({ children }: { children: ReactNode }) {
  useWebSocketSync()
  return (
    <div className="flex h-screen w-screen bg-zinc-950 text-zinc-50">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Topbar />
        <main className="flex-1 overflow-y-auto">{children}</main>
      </div>
    </div>
  )
}
