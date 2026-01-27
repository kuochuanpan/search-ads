import { useState, useEffect } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Link, RefreshCw, Check, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Icon } from '@/components/ui/Icon'
import { Input } from '@/components/ui/Input'
import { useProjects } from '@/hooks/useProjects'
import { useActiveProject } from '@/store'
import { api } from '@/lib/api'

export function ImportPage() {
  const queryClient = useQueryClient()
  const { data: projects } = useProjects()
  const { project: activeProject } = useActiveProject()

  // ADS Import
  const [adsUrl, setAdsUrl] = useState('')
  const [expandRefs, setExpandRefs] = useState(true)
  const [expandCitations, setExpandCitations] = useState(false)
  const [downloadPdf, setDownloadPdf] = useState(true)
  const [selectedProject, setSelectedProject] = useState<string>(activeProject || '')

  // Update selected project when active project changes
  useEffect(() => {
    if (activeProject) {
      setSelectedProject(activeProject)
    }
  }, [activeProject])
  const [adsLoading, setAdsLoading] = useState(false)
  const [adsResult, setAdsResult] = useState<{ success: boolean; message: string } | null>(null)
  const [adsProgress, setAdsProgress] = useState<{
    message: string
    logs: Array<{ type: 'success' | 'info' | 'error'; message: string }>
  } | null>(null)





  const handleAdsImport = async () => {
    if (!adsUrl.trim()) return
    setAdsLoading(true)
    setAdsResult(null)
    setAdsProgress({ message: 'Starting import...', logs: [] })

    try {
      for await (const event of api.streamImportFromAds(adsUrl, {
        project: selectedProject || undefined,
        expand_references: expandRefs,
        expand_citations: expandCitations,
      })) {
        if (event.type === 'progress') {
          setAdsProgress(prev => prev ? ({ ...prev, message: event.message || 'Processing...' }) : null)
        } else if (event.type === 'log') {
          setAdsProgress(prev => prev ? ({
            ...prev,
            logs: [...prev.logs, { type: event.level === 'error' ? 'error' : (event.level === 'info' ? 'info' : 'success'), message: event.message || '' }]
          }) : null)
        } else if (event.type === 'result' && event.data) {
          setAdsResult({ success: event.data.success, message: event.data.message })
          if (event.data.success) {
            setAdsUrl('')
            // Invalidate queries to refresh library view
            queryClient.invalidateQueries({ queryKey: ['papers'] })
            queryClient.invalidateQueries({ queryKey: ['stats'] })
            queryClient.invalidateQueries({ queryKey: ['projects'] })
          }
        } else if (event.type === 'error') {
          setAdsResult({ success: false, message: event.message || 'Import failed' })
        }
      }
    } catch (e: any) {
      setAdsResult({ success: false, message: e.message || 'Import failed' })
    } finally {
      setAdsLoading(false)
    }
  }





  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="text-center py-8">
        <h1 className="text-2xl font-semibold mb-2">Import Papers</h1>
        <p className="text-muted-foreground">
          Add papers to your library from ADS
        </p>
      </div>

      {/* Project Selection (shared) */}
      <Card className="p-4">
        <label className="block text-sm font-medium mb-2">Add to project:</label>
        <select
          value={selectedProject}
          onChange={(e) => setSelectedProject(e.target.value)}
          className="w-full h-9 px-3 border rounded-md bg-background"
        >
          <option value="">No project</option>
          {projects?.projects.map((p) => (
            <option key={p.name} value={p.name}>{p.name}</option>
          ))}
        </select>
      </Card>

      {/* From ADS URL */}
      <Card className="p-6">
        <div className="flex items-center gap-2 mb-4">
          <Icon icon={Link} size={20} className="text-primary" />
          <h3 className="font-medium">From ADS URL or Bibcode</h3>
        </div>

        <Input
          value={adsUrl}
          onChange={(e) => setAdsUrl(e.target.value)}
          placeholder="https://ui.adsabs.harvard.edu/abs/2024ApJ...996...35P/abstract"
        />

        <div className="flex flex-wrap gap-4 mt-4 text-sm">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={expandRefs}
              onChange={(e) => setExpandRefs(e.target.checked)}
              className="rounded"
            />
            Auto-expand references (1 hop)
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={expandCitations}
              onChange={(e) => setExpandCitations(e.target.checked)}
              className="rounded"
            />
            Auto-expand citations (1 hop)
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={downloadPdf}
              onChange={(e) => setDownloadPdf(e.target.checked)}
              className="rounded"
            />
            Download PDF if available
          </label>
        </div>

        <Button
          className="w-full mt-4"
          onClick={handleAdsImport}
          disabled={adsLoading || !adsUrl.trim()}
        >
          {adsLoading ? 'Importing...' : 'Add Paper'}
        </Button>

        {adsProgress && (
          <div className="mt-4 space-y-2">
            <div className="text-sm flex justify-between">
              <span>{adsProgress.message}</span>
            </div>
            {/* Indeterminate progress bar since we don't know total steps for single import recursion easily */}
            <div className="w-full bg-secondary rounded-full h-1.5 overflow-hidden">
              <div className="bg-primary h-full transition-all duration-300 animate-pulse" style={{ width: '100%' }}></div>
            </div>

            {adsProgress.logs.length > 0 && (
              <div className="mt-2 max-h-32 overflow-y-auto text-xs space-y-1 p-2 bg-secondary/30 rounded border">
                {adsProgress.logs.map((log, i) => (
                  <div key={i} className={log.type === 'error' ? 'text-red-500' : (log.type === 'info' ? 'text-blue-500' : 'text-green-600 dark:text-green-400')}>
                    {log.message}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {adsResult && (
          <div className={`mt-3 p-3 rounded flex items-center gap-2 ${adsResult.success ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-200' : 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200'}`}>
            <Icon icon={adsResult.success ? Check : AlertCircle} size={16} />
            {adsResult.message}
          </div>
        )}
      </Card>



      {/* Zotero Sync */}
      <Card className="p-6 opacity-60">
        <div className="flex items-center gap-2 mb-4">
          <Icon icon={RefreshCw} size={20} className="text-primary" />
          <h3 className="font-medium">Sync with Zotero</h3>
          <span className="text-xs bg-secondary px-2 py-0.5 rounded">Coming Soon</span>
        </div>
        <p className="text-sm text-muted-foreground">
          Connect your Zotero library for two-way sync.
        </p>
        <Button className="w-full mt-4" disabled>
          Connect Zotero Account
        </Button>
      </Card>
    </div>
  )
}
