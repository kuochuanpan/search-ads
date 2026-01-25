import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'

export function usePapers(params?: {
  limit?: number
  offset?: number
  project?: string
  year_min?: number
  year_max?: number
  min_citations?: number
  has_pdf?: boolean
  pdf_embedded?: boolean
  is_my_paper?: boolean
  has_note?: boolean
  search?: string
  sort_by?: 'title' | 'year' | 'citation_count' | 'created_at' | 'updated_at'
  sort_order?: 'asc' | 'desc'
}) {
  return useQuery({
    queryKey: ['papers', params],
    queryFn: () => api.getPapers(params),
  })
}

export function usePaper(bibcode: string) {
  return useQuery({
    queryKey: ['paper', bibcode],
    queryFn: () => api.getPaper(bibcode),
    enabled: !!bibcode,
  })
}

export function useDeletePaper() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (bibcode: string) => api.deletePaper(bibcode),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['papers'] })
      queryClient.invalidateQueries({ queryKey: ['paper'] })
      queryClient.invalidateQueries({ queryKey: ['stats'] })
    },
  })
}

export function useToggleMyPaper() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ bibcode, isMyPaper }: { bibcode: string; isMyPaper: boolean }) =>
      api.toggleMyPaper(bibcode, isMyPaper),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['papers'] })
      queryClient.invalidateQueries({ queryKey: ['paper'] })
      queryClient.invalidateQueries({ queryKey: ['my-papers'] })
      queryClient.invalidateQueries({ queryKey: ['stats'] })
    },
  })
}

export function useBulkDeletePapers() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (bibcodes: string[]) => api.bulkDeletePapers(bibcodes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['papers'] })
      queryClient.invalidateQueries({ queryKey: ['paper'] })
      queryClient.invalidateQueries({ queryKey: ['my-papers'] })
      queryClient.invalidateQueries({ queryKey: ['stats'] })
    },
  })
}

export function useBulkMarkMyPapers() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ bibcodes, isMyPaper }: { bibcodes: string[]; isMyPaper: boolean }) =>
      api.bulkMarkMyPapers(bibcodes, isMyPaper),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['papers'] })
      queryClient.invalidateQueries({ queryKey: ['paper'] })
      queryClient.invalidateQueries({ queryKey: ['my-papers'] })
      queryClient.invalidateQueries({ queryKey: ['stats'] })
    },
  })
}

export function useMyPapers(limit = 100) {
  return useQuery({
    queryKey: ['my-papers', limit],
    queryFn: () => api.getMyPapers(limit),
  })
}