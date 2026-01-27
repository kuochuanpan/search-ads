import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'

export function useProjects() {
  return useQuery({
    queryKey: ['projects'],
    queryFn: () => api.getProjects(),
  })
}

export function useProject(name: string) {
  return useQuery({
    queryKey: ['project', name],
    queryFn: () => api.getProject(name),
    enabled: !!name,
  })
}

export function useCreateProject() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ name, description }: { name: string; description?: string }) =>
      api.createProject(name, description),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
    },
  })
}

export function useDeleteProject() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ name, deletePapers }: { name: string; deletePapers?: boolean }) =>
      api.deleteProject(name, deletePapers),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
      queryClient.invalidateQueries({ queryKey: ['papers'] })
      queryClient.invalidateQueries({ queryKey: ['stats'] })
    },
  })
}

export function useAddPaperToProject() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ projectName, bibcode }: { projectName: string; bibcode: string }) =>
      api.addPaperToProject(projectName, bibcode),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
      queryClient.invalidateQueries({ queryKey: ['papers'] })
      queryClient.invalidateQueries({ queryKey: ['paper'] })
    },
  })
}

export function useAddPapersToProject() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ projectName, bibcodes }: { projectName: string; bibcodes: string[] }) =>
      api.addPapersToProject(projectName, bibcodes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
      queryClient.invalidateQueries({ queryKey: ['papers'] })
    },
  })
}

export function useProjectPapers(name: string) {
  return useQuery({
    queryKey: ['project-papers', name],
    queryFn: () => api.getProjectPapers(name),
    enabled: !!name,
  })
}