import { useMutation } from '@tanstack/react-query'
import { api } from '@/lib/api'

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
 * Hook for AI-powered search with context analysis and ranking
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
