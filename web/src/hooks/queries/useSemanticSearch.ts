import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api-client'
import { qk } from '@/lib/query-keys'
import type { SemanticSearchResponse } from '@/types/entities'

export function useSemanticSearch(query: string) {
  const normalized = query.trim()

  return useQuery({
    queryKey: qk.search.semantic(normalized),
    enabled: normalized.length >= 2,
    staleTime: 15_000,
    queryFn: () =>
      api<SemanticSearchResponse>('/v1/search', {
        method: 'POST',
        body: JSON.stringify({
          query: normalized,
          types: ['agent', 'task'],
          top_k: 8,
        }),
      }),
  })
}
