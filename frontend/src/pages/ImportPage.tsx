import { useState } from 'react'
import { Link, Upload, Clipboard, RefreshCw, Check, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Icon } from '@/components/ui/Icon'
import { Input } from '@/components/ui/Input'
import { useProjects } from '@/hooks/useProjects'
import { api } from '@/lib/api'

export function ImportPage() {
  const { data: projects } = useProjects()

  // ADS Import
  const [adsUrl, setAdsUrl] = useState('')
  const [expandRefs, setExpandRefs] = useState(true)
  const [expandCitations, setExpandCitations] = useState(false)
  const [downloadPdf, setDownloadPdf] = useState(true)
  const [selectedProject, setSelectedProject] = useState<string>('')
  const [adsLoading, setAdsLoading] = useState(false)
  const [adsResult, setAdsResult] = useState<{ success: boolean; message: string } | null>(null)

  // Batch Import
  const [batchText, setBatchText] = useState('')
  const [batchLoading, setBatchLoading] = useState(false)
  const [batchResult, setBatchResult] = useState<{ success: boolean; imported: number; failed: number } | null>(null)

  // BibTeX Import
  const [bibtexContent, setBibtexContent] = useState('')
  const [bibtexLoading, setBibtexLoading] = useState(false)
  const [bibtexResult, setBibtexResult] = useState<{ success: boolean; imported: number; failed: number } | null>(null)

  const handleAdsImport = async () => {
    if (!adsUrl.trim()) return
    setAdsLoading(true)
    setAdsResult(null)
    try {
      const result = await api.importFromAds(adsUrl, {
        project: selectedProject || undefined,
        expand_references: expandRefs,
        expand_citations: expandCitations,
      })
      setAdsResult({ success: result.success, message: result.message })
      if (result.success) setAdsUrl('')
    } catch (e: any) {
      setAdsResult({ success: false, message: e.message || 'Import failed' })
    } finally {
      setAdsLoading(false)
    }
  }

  const handleBatchImport = async () => {
    const identifiers = batchText.split('\n').map(s => s.trim()).filter(Boolean)
    if (identifiers.length === 0) return
    setBatchLoading(true)
    setBatchResult(null)
    try {
      const result = await api.batchImport(identifiers, selectedProject || undefined)
      setBatchResult({ success: result.success, imported: result.imported, failed: result.failed })
      if (result.success) setBatchText('')
    } catch (e: any) {
      setBatchResult({ success: false, imported: 0, failed: identifiers.length })
    } finally {
      setBatchLoading(false)
    }
  }

  const handleBibtexImport = async () => {
    if (!bibtexContent.trim()) return
    setBibtexLoading(true)
    setBibtexResult(null)
    try {
      const result = await api.importBibtex(bibtexContent, selectedProject || undefined)
      setBibtexResult({ success: result.success, imported: result.imported, failed: result.failed })
      if (result.success) setBibtexContent('')
    } catch (e: any) {
      setBibtexResult({ success: false, imported: 0, failed: 0 })
    } finally {
      setBibtexLoading(false)
    }
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="text-center py-8">
        <h1 className="text-2xl font-semibold mb-2">Import Papers</h1>
        <p className="text-muted-foreground">
          Add papers to your library from ADS, BibTeX, or by identifier
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

        {adsResult && (
          <div className={`mt-3 p-3 rounded flex items-center gap-2 ${adsResult.success ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-200' : 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200'}`}>
            <Icon icon={adsResult.success ? Check : AlertCircle} size={16} />
            {adsResult.message}
          </div>
        )}
      </Card>

      {/* From Clipboard */}
      <Card className="p-6">
        <div className="flex items-center gap-2 mb-4">
          <Icon icon={Clipboard} size={20} className="text-primary" />
          <h3 className="font-medium">From Clipboard (DOI/arXiv/Bibcode)</h3>
        </div>

        <textarea
          value={batchText}
          onChange={(e) => setBatchText(e.target.value)}
          placeholder={`Paste DOIs, arXiv IDs, or bibcodes (one per line):
10.1088/0004-637X/996/1/35
2301.12345
2024MNRAS.528.1234J`}
          className="w-full h-32 p-3 border rounded-lg bg-background resize-none focus:outline-none focus:ring-2 focus:ring-ring font-mono text-sm"
        />

        <Button
          className="w-full mt-4"
          onClick={handleBatchImport}
          disabled={batchLoading || !batchText.trim()}
        >
          {batchLoading ? 'Importing...' : `Import ${batchText.split('\n').filter(s => s.trim()).length} Papers`}
        </Button>

        {batchResult && (
          <div className={`mt-3 p-3 rounded flex items-center gap-2 ${batchResult.success ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-200' : 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200'}`}>
            <Icon icon={batchResult.success ? Check : AlertCircle} size={16} />
            Imported {batchResult.imported} papers{batchResult.failed > 0 && `, ${batchResult.failed} failed`}
          </div>
        )}
      </Card>

      {/* From BibTeX */}
      <Card className="p-6">
        <div className="flex items-center gap-2 mb-4">
          <Icon icon={Upload} size={20} className="text-primary" />
          <h3 className="font-medium">From BibTeX</h3>
        </div>

        <textarea
          value={bibtexContent}
          onChange={(e) => setBibtexContent(e.target.value)}
          placeholder={`Paste BibTeX content or drag & drop a .bib file:

@article{2024ApJ...996...35P,
  author = {Pan, Z. and others},
  title = {A Great Paper},
  journal = {ApJ},
  year = {2024}
}`}
          className="w-full h-40 p-3 border rounded-lg bg-background resize-none focus:outline-none focus:ring-2 focus:ring-ring font-mono text-sm"
        />

        <div className="flex items-center gap-2 mt-3">
          <input type="checkbox" id="fetchAds" defaultChecked className="rounded" />
          <label htmlFor="fetchAds" className="text-sm">Fetch full metadata from ADS</label>
        </div>

        <Button
          className="w-full mt-4"
          onClick={handleBibtexImport}
          disabled={bibtexLoading || !bibtexContent.trim()}
        >
          {bibtexLoading ? 'Importing...' : 'Import'}
        </Button>

        {bibtexResult && (
          <div className={`mt-3 p-3 rounded flex items-center gap-2 ${bibtexResult.success ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-200' : 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200'}`}>
            <Icon icon={bibtexResult.success ? Check : AlertCircle} size={16} />
            Imported {bibtexResult.imported} papers{bibtexResult.failed > 0 && `, ${bibtexResult.failed} failed`}
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
