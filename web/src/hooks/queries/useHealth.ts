import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api-client'
import { qk } from '@/lib/query-keys'
import type { HealthResponse } from '@/types/entities'

export function useHealth() {
  return useQuery({
    queryKey: qk.health,
    queryFn: () => api<HealthResponse>('/v1/health'),
    refetchInterval: 10_000,
    refetchIntervalInBackground: true,
    retry: false,
  })
}
