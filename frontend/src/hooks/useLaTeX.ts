import { useMutation } from '@tanstack/react-query'
import { api } from '@/lib/api'

/**
 * Hook for parsing LaTeX text to find empty citations
 */
export function useParseLaTeX() {
  return useMutation({
    mutationFn: (latexText: string) => api.parseLaTeX(latexText),
  })
}

export interface CitationSuggestionsParams {
  latex_text: string
  limit?: number
  use_library?: boolean
  use_ads?: boolean
}

/**
 * Hook for getting citation suggestions for empty citations
 */
export function useCitationSuggestions() {
  return useMutation({
    mutationFn: (params: CitationSuggestionsParams) => api.getCitationSuggestions(params),
  })
}

/**
 * Hook for generating bibliography entries (BibTeX or AASTeX)
 */
export function useGenerateBibliography() {
  return useMutation({
    mutationFn: ({ bibcodes, format }: { bibcodes: string[]; format: 'bibtex' | 'aastex' }) =>
      api.generateBibliography(bibcodes, format),
  })
}
