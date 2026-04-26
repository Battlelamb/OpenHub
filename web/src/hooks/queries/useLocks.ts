import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api-client'
import { qk } from '@/lib/query-keys'
import type { ResourceLock } from '@/types/entities'

export function useLocks() {
  return useQuery({
    queryKey: qk.locks,
    queryFn: async (): Promise<ResourceLock[]> => {
      // Backend: GET /v1/locks/ returns List[ResourceLock] directly (added in Plan 04-10 Task 1).
      const res = await api<ResourceLock[]>('/v1/locks/')
      return res ?? []
    },
  })
}
