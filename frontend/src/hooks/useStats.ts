import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

export function useStats() {
  return useQuery({
    queryKey: ['stats'],
    queryFn: () => api.getStats(),
  })
}

export function useApiUsage() {
  return useQuery({
    queryKey: ['api-usage'],
    queryFn: () => api.getApiUsage(),
  })
}

export function useSettings() {
  return useQuery({
    queryKey: ['settings'],
    queryFn: () => api.getSettings(),
  })
}

export function useVectorStats() {
  return useQuery({
    queryKey: ['vector-stats'],
    queryFn: () => api.getVectorStats(),
  })
}