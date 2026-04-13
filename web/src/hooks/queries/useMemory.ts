import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api-client'
import { qk } from '@/lib/query-keys'
import type { MemoryItem } from '@/types/entities'

export function useMemoryEntries() {
  return useQuery({
    queryKey: qk.memory,
    queryFn: () => api<MemoryItem[]>('/v1/memory'),
  })
}
