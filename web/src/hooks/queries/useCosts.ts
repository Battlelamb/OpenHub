import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api-client'
import { qk } from '@/lib/query-keys'
import type { CostItem } from '@/types/entities'

export function useCosts() {
  return useQuery({
    queryKey: qk.costs,
    queryFn: () => api<CostItem[]>('/v1/costs'),
  })
}
