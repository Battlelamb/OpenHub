import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api-client'
import { qk } from '@/lib/query-keys'
import type { ResourceLock } from '@/types/entities'

export function useLocks() {
  return useQuery({
    queryKey: qk.locks,
    queryFn: () => api<ResourceLock[]>('/v1/locks'),
  })
}
