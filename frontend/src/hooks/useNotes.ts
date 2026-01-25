import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'

export function useNotes(limit = 100) {
  return useQuery({
    queryKey: ['notes', limit],
    queryFn: () => api.getNotes(limit),
  })
}

export function useNote(bibcode: string) {
  return useQuery({
    queryKey: ['note', bibcode],
    queryFn: () => api.getNote(bibcode),
    enabled: !!bibcode,
  })
}

export function useCreateOrUpdateNote() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ bibcode, content, replace }: { bibcode: string; content: string; replace?: boolean }) =>
      api.createOrUpdateNote(bibcode, content, replace),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notes'] })
      queryClient.invalidateQueries({ queryKey: ['note'] })
      queryClient.invalidateQueries({ queryKey: ['papers'] })
      queryClient.invalidateQueries({ queryKey: ['paper'] })
      queryClient.invalidateQueries({ queryKey: ['stats'] })
    },
  })
}

export function useDeleteNote() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (bibcode: string) => api.deleteNote(bibcode),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notes'] })
      queryClient.invalidateQueries({ queryKey: ['note'] })
      queryClient.invalidateQueries({ queryKey: ['papers'] })
      queryClient.invalidateQueries({ queryKey: ['paper'] })
      queryClient.invalidateQueries({ queryKey: ['stats'] })
    },
  })
}

export function useSearchNotes() {
  return useMutation({
    mutationFn: ({ query, limit }: { query: string; limit?: number }) =>
      api.searchNotes(query, limit),
  })
}