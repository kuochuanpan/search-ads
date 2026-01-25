import { useState } from 'react'
import { Trash2, Star, Download, FolderPlus, X } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Icon } from '@/components/ui/Icon'
import { usePaperSelection } from '@/store'
import { useBulkDeletePapers, useBulkMarkMyPapers } from '@/hooks/usePapers'
import { useProjects } from '@/hooks/useProjects'
import { api } from '@/lib/api'

interface BulkActionsBarProps {
  selectedBibcodes: string[]
}

export function BulkActionsBar({ selectedBibcodes }: BulkActionsBarProps) {
  const { deselectAll } = usePaperSelection()
  const bulkDelete = useBulkDeletePapers()
  const bulkMarkMyPapers = useBulkMarkMyPapers()
  const { data: projects } = useProjects()
  const [showProjectMenu, setShowProjectMenu] = useState(false)
  const [isDownloading, setIsDownloading] = useState(false)

  const count = selectedBibcodes.length

  const handleDelete = async () => {
    if (confirm(`Are you sure you want to delete ${count} paper(s)?`)) {
      await bulkDelete.mutateAsync(selectedBibcodes)
      deselectAll()
    }
  }

  const handleMarkAsMine = async () => {
    await bulkMarkMyPapers.mutateAsync({ bibcodes: selectedBibcodes, isMyPaper: true })
    deselectAll()
  }

  const handleDownloadPdfs = async () => {
    setIsDownloading(true)
    try {
      for (const bibcode of selectedBibcodes) {
        await api.downloadPdf(bibcode)
      }
    } catch (e) {
      console.error('Failed to download PDFs:', e)
    } finally {
      setIsDownloading(false)
    }
  }

  const handleAddToProject = async (projectName: string) => {
    try {
      await api.addPapersToProject(projectName, selectedBibcodes)
      setShowProjectMenu(false)
      deselectAll()
    } catch (e) {
      console.error('Failed to add papers to project:', e)
    }
  }

  return (
    <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-50">
      <div className="flex items-center gap-2 px-4 py-2 bg-card border rounded-lg shadow-lg">
        <span className="text-sm font-medium mr-2">
          {count} selected
        </span>

        <div className="h-4 w-px bg-border" />

        <Button variant="ghost" size="sm" onClick={handleDownloadPdfs} disabled={isDownloading}>
          <Icon icon={Download} size={16} />
          {isDownloading ? 'Downloading...' : 'Download PDFs'}
        </Button>

        <Button variant="ghost" size="sm" onClick={handleMarkAsMine}>
          <Icon icon={Star} size={16} />
          Mark as Mine
        </Button>

        <div className="relative">
          <Button variant="ghost" size="sm" onClick={() => setShowProjectMenu(!showProjectMenu)}>
            <Icon icon={FolderPlus} size={16} />
            Add to Project
          </Button>
          {showProjectMenu && (
            <div className="absolute bottom-full left-0 mb-1 w-48 bg-card border rounded-lg shadow-lg p-1">
              {projects?.projects.length === 0 && (
                <p className="text-xs text-muted-foreground p-2">No projects yet</p>
              )}
              {projects?.projects.map((project) => (
                <button
                  key={project.name}
                  className="w-full text-left px-3 py-1.5 text-sm hover:bg-secondary rounded"
                  onClick={() => handleAddToProject(project.name)}
                >
                  {project.name}
                </button>
              ))}
            </div>
          )}
        </div>

        <Button variant="ghost" size="sm" onClick={handleDelete} className="text-destructive hover:text-destructive">
          <Icon icon={Trash2} size={16} />
          Delete
        </Button>

        <div className="h-4 w-px bg-border" />

        <Button variant="ghost" size="sm" onClick={deselectAll}>
          <Icon icon={X} size={16} />
        </Button>
      </div>
    </div>
  )
}
