import { useMutation, useInfiniteQuery } from '@tanstack/react-query'
import { api, SearchMode, SearchScope, UnifiedSearchResponse } from '@/lib/api'

export interface AISearchParams {
  query: string
  limit?: number
  search_library?: boolean
  search_ads?: boolean
  search_pdf?: boolean
  min_year?: number
  min_citations?: number
  use_llm?: boolean
}

/**
 * Hook for AI-powered search with context analysis and ranking (legacy)
 */
export function useAISearch() {
  return useMutation({
    mutationFn: (params: AISearchParams) => api.aiSearch(params),
  })
}

/**
 * Hook for asking questions about a paper using its embedded content
 */
export function useAskPaper() {
  return useMutation({
    mutationFn: ({ bibcode, question }: { bibcode: string; question: string }) =>
      api.askPaper(bibcode, question),
  })
}

export interface UnifiedSearchParams {
  query: string
  mode: SearchMode
  scope: SearchScope
  min_year?: number
  max_year?: number
  min_citations?: number
  /** Auto-incremented ID to force refetch on every Search click */
  searchId: number
}

const BATCH_SIZE = 100

/**
 * Hook for unified search with infinite query pagination.
 * Fetches in batches of 100, displayed 20 at a time on the client.
 * Each search click gets a unique searchId in the queryKey to prevent stale cache hits.
 */
export function useUnifiedSearch(params: UnifiedSearchParams | null) {
  return useInfiniteQuery<UnifiedSearchResponse>({
    queryKey: ['search-unified', params],
    queryFn: async ({ pageParam }) => {
      if (!params) throw new Error('No search params')
      return api.searchUnified({
        query: params.query,
        mode: params.mode,
        scope: params.scope,
        limit: BATCH_SIZE,
        offset: pageParam as number,
        min_year: params.min_year,
        max_year: params.max_year,
        min_citations: params.min_citations,
      })
    },
    initialPageParam: 0,
    getNextPageParam: (lastPage) => {
      if (!lastPage.has_more) return undefined
      return lastPage.offset + lastPage.limit
    },
    enabled: !!params?.query,
    staleTime: 0, // Always refetch — searches should never serve stale results
    gcTime: 10 * 60 * 1000, // Keep in garbage collection for 10 min (back-nav cache)
  })
}
