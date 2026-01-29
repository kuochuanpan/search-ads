import { useQuery, useMutation, useQueryClient, useInfiniteQuery } from '@tanstack/react-query'
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
  sort_by?: 'title' | 'year' | 'citation_count' | 'created_at' | 'updated_at' | 'authors' | 'journal'
  sort_order?: 'asc' | 'desc'
}) {
  return useInfiniteQuery({
    queryKey: ['papers', params],
    queryFn: ({ pageParam }) => api.getPapers({ ...params, offset: pageParam, limit: params?.limit || 100 }),
    initialPageParam: 0,
    getNextPageParam: (lastPage) => {
      const nextOffset = lastPage.offset + lastPage.limit
      if (nextOffset >= lastPage.total) return undefined
      return nextOffset
    },
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

export function useDownloadPdf() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (bibcode: string) => api.downloadPdf(bibcode),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['papers'] })
      queryClient.invalidateQueries({ queryKey: ['paper'] })
      queryClient.invalidateQueries({ queryKey: ['stats'] })
    },
  })
}

export function useOpenPdf() {
  return useMutation({
    mutationFn: (bibcode: string) => api.openPdf(bibcode),
  })
}

export function useEmbedPdf() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (bibcode: string) => api.embedPdf(bibcode),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['papers'] })
      queryClient.invalidateQueries({ queryKey: ['paper'] })
      queryClient.invalidateQueries({ queryKey: ['stats'] })
    },
  })
}

export function useDeletePdfEmbedding() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (bibcode: string) => api.deletePdfEmbedding(bibcode),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['papers'] })
      queryClient.invalidateQueries({ queryKey: ['paper'] })
      queryClient.invalidateQueries({ queryKey: ['stats'] })
    },
  })
}