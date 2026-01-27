import { useNavigate, useParams } from '@tanstack/react-router'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft,
  ExternalLink,
  Copy,
  Star,
  FileText,
  Download,
  FolderPlus,
  Network,
  Pencil,
  Trash2,
  Check,
  Sparkles,
  Send,
  Loader2,
} from 'lucide-react'
import { useState, useRef, useEffect } from 'react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Icon } from '@/components/ui/Icon'
import { Modal } from '@/components/ui/Modal'
import { usePaper, useToggleMyPaper, useDeletePaper } from '@/hooks/usePapers'
import { useNote, useCreateOrUpdateNote, useDeleteNote } from '@/hooks/useNotes'
import { useProjects, useAddPaperToProject } from '@/hooks/useProjects'
import { useAskPaper } from '@/hooks/useSearch'
import { formatAuthorList, cn } from '@/lib/utils'
import { api } from '@/lib/api'

export function PaperDetailPage() {
  const navigate = useNavigate()
  const { bibcode } = useParams({ from: '/library/$bibcode' })
  const { data: paper, isLoading, error } = usePaper(bibcode)
  const { data: note } = useNote(bibcode)
  const { data: projectsData } = useProjects()
  const toggleMyPaper = useToggleMyPaper()
  const deletePaper = useDeletePaper()
  const createOrUpdateNote = useCreateOrUpdateNote()
  const deleteNote = useDeleteNote()
  const addPaperToProject = useAddPaperToProject()

  const queryClient = useQueryClient()
  const [showNoteModal, setShowNoteModal] = useState(false)
  const [noteContent, setNoteContent] = useState('')
  const [copiedBibtex, setCopiedBibtex] = useState(false)
  const [copiedCiteKey, setCopiedCiteKey] = useState(false)
  const [copiedAastex, setCopiedAastex] = useState(false)
  const [loadingBibtex, setLoadingBibtex] = useState(false)
  const [loadingAastex, setLoadingAastex] = useState(false)
  const [aiQuestion, setAiQuestion] = useState('')
  const [aiAnswer, setAiAnswer] = useState<{ answer: string; sources: string[] } | null>(null)
  const [showProjectDropdown, setShowProjectDropdown] = useState(false)

  const projectDropdownRef = useRef<HTMLDivElement>(null)

  const askPaper = useAskPaper()

  // Close project dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (projectDropdownRef.current && !projectDropdownRef.current.contains(e.target as Node)) {
        setShowProjectDropdown(false)
      }
    }
    if (showProjectDropdown) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [showProjectDropdown])

  const handleAddToProject = async (projectName: string) => {
    try {
      await addPaperToProject.mutateAsync({ projectName, bibcode })
      setShowProjectDropdown(false)
    } catch (e) {
      console.error('Failed to add paper to project:', e)
    }
  }

  const handleCopyBibtex = async () => {
    if (paper?.bibtex) {
      await navigator.clipboard.writeText(paper.bibtex)
      setCopiedBibtex(true)
      setTimeout(() => setCopiedBibtex(false), 2000)
    } else {
      // Fetch from ADS if not cached
      setLoadingBibtex(true)
      try {
        const result = await api.getCitationExport(bibcode)
        if (result.bibtex) {
          await navigator.clipboard.writeText(result.bibtex)
          setCopiedBibtex(true)
          setTimeout(() => setCopiedBibtex(false), 2000)
          // Invalidate query to refresh paper data
          queryClient.invalidateQueries({ queryKey: ['paper', bibcode] })
        }
      } catch (e) {
        console.error('Failed to fetch BibTeX:', e)
      } finally {
        setLoadingBibtex(false)
      }
    }
  }

  const handleCopyCiteKey = async () => {
    await navigator.clipboard.writeText(bibcode)
    setCopiedCiteKey(true)
    setTimeout(() => setCopiedCiteKey(false), 2000)
  }

  const handleCopyAastex = async () => {
    if (paper?.bibitem_aastex) {
      await navigator.clipboard.writeText(paper.bibitem_aastex)
      setCopiedAastex(true)
      setTimeout(() => setCopiedAastex(false), 2000)
    } else {
      // Fetch from ADS if not cached
      setLoadingAastex(true)
      try {
        const result = await api.getCitationExport(bibcode)
        if (result.bibitem_aastex) {
          await navigator.clipboard.writeText(result.bibitem_aastex)
          setCopiedAastex(true)
          setTimeout(() => setCopiedAastex(false), 2000)
          // Invalidate query to refresh paper data
          queryClient.invalidateQueries({ queryKey: ['paper', bibcode] })
        }
      } catch (e) {
        console.error('Failed to fetch AASTeX:', e)
      } finally {
        setLoadingAastex(false)
      }
    }
  }

  const handleToggleMyPaper = () => {
    if (paper) {
      toggleMyPaper.mutate({ bibcode: paper.bibcode, isMyPaper: !paper.is_my_paper })
    }
  }

  const handleDelete = async () => {
    if (confirm('Are you sure you want to delete this paper?')) {
      await deletePaper.mutateAsync(bibcode)
      navigate({ to: '/library' })
    }
  }

  const handleOpenNote = () => {
    setNoteContent(note?.content || '')
    setShowNoteModal(true)
  }

  const handleSaveNote = async () => {
    await createOrUpdateNote.mutateAsync({ bibcode, content: noteContent })
    setShowNoteModal(false)
  }

  const handleDeleteNote = async () => {
    if (confirm('Are you sure you want to delete this note?')) {
      await deleteNote.mutateAsync(bibcode)
      setShowNoteModal(false)
    }
  }

  const handleDownloadPdf = async () => {
    try {
      await api.downloadPdf(bibcode)
    } catch (e) {
      console.error('Failed to download PDF:', e)
    }
  }

  const handleOpenPdf = async () => {
    try {
      await api.openPdf(bibcode)
    } catch (e) {
      console.error('Failed to open PDF:', e)
    }
  }

  const handleAskQuestion = async () => {
    if (!aiQuestion.trim()) return

    askPaper.mutate(
      { bibcode, question: aiQuestion },
      {
        onSuccess: (data) => {
          setAiAnswer({ answer: data.answer, sources: data.sources_used })
        },
      }
    )
  }

  const handleKeyDownAI = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleAskQuestion()
    }
  }

  if (isLoading) {
    return (
      <div className="py-8 text-center text-muted-foreground">
        Loading paper...
      </div>
    )
  }

  if (error || !paper) {
    return (
      <div className="py-8 text-center">
        <p className="text-destructive mb-4">Paper not found</p>
        <Button variant="outline" onClick={() => navigate({ to: '/library' })}>
          Back to Library
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Back button */}
      <button
        onClick={() => navigate({ to: '/library' })}
        className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors"
      >
        <Icon icon={ArrowLeft} size={18} />
        Back to Library
      </button>

      {/* Title and metadata */}
      <div>
        <div className="flex items-start justify-between gap-4">
          <h1 className="text-2xl font-semibold leading-tight">{paper.title}</h1>
          {paper.is_my_paper && (
            <Badge variant="secondary" className="flex items-center gap-1 shrink-0">
              <Icon icon={Star} size={14} className="text-yellow-500" />
              My Paper
            </Badge>
          )}
        </div>
        <p className="text-muted-foreground mt-2">
          {formatAuthorList(paper.authors)} &middot; {paper.year}
          {paper.journal && ` &middot; ${paper.journal}`}
          {paper.volume && ` ${paper.volume}`}
          {paper.pages && `, ${paper.pages}`}
        </p>
      </div>

      {/* Action buttons */}
      <Card className="p-4">
        <div className="flex flex-wrap gap-2">
          {paper.pdf_path ? (
            <Button variant="outline" onClick={handleOpenPdf}>
              <Icon icon={FileText} size={16} />
              Open PDF
            </Button>
          ) : paper.pdf_url ? (
            <Button variant="outline" onClick={handleDownloadPdf}>
              <Icon icon={Download} size={16} />
              Download PDF
            </Button>
          ) : null}

          <Button variant="outline" onClick={handleCopyBibtex} disabled={loadingBibtex}>
            {loadingBibtex ? (
              <Icon icon={Loader2} size={16} className="animate-spin" />
            ) : (
              <Icon icon={copiedBibtex ? Check : Copy} size={16} />
            )}
            {copiedBibtex ? 'Copied!' : loadingBibtex ? 'Fetching...' : 'Copy BibTeX'}
          </Button>

          <Button variant="outline" onClick={handleCopyCiteKey}>
            <Icon icon={copiedCiteKey ? Check : Copy} size={16} />
            {copiedCiteKey ? 'Copied!' : 'Copy Cite Key'}
          </Button>

          <Button variant="outline" onClick={handleCopyAastex} disabled={loadingAastex}>
            {loadingAastex ? (
              <Icon icon={Loader2} size={16} className="animate-spin" />
            ) : (
              <Icon icon={copiedAastex ? Check : Copy} size={16} />
            )}
            {copiedAastex ? 'Copied!' : loadingAastex ? 'Fetching...' : 'Copy AASTeX'}
          </Button>

          <Button
            variant="outline"
            as="a"
            href={`https://ui.adsabs.harvard.edu/abs/${bibcode}/abstract`}
            target="_blank"
          >
            <Icon icon={ExternalLink} size={16} />
            ADS
          </Button>

          {paper.arxiv_id && (
            <Button
              variant="outline"
              as="a"
              href={`https://arxiv.org/abs/${paper.arxiv_id}`}
              target="_blank"
            >
              <Icon icon={ExternalLink} size={16} />
              arXiv
            </Button>
          )}

          <Button
            variant={paper.is_my_paper ? 'secondary' : 'outline'}
            onClick={handleToggleMyPaper}
          >
            <Icon icon={Star} size={16} className={paper.is_my_paper ? 'text-yellow-500' : ''} />
            {paper.is_my_paper ? 'My Paper' : 'Mark as Mine'}
          </Button>

          <Button
            variant="outline"
            onClick={() => navigate({ to: '/graph/$bibcode', params: { bibcode } })}
          >
            <Icon icon={Network} size={16} />
            View in Graph
          </Button>
        </div>
      </Card>

      {/* Content grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Sidebar */}
        <div className="space-y-4">
          {/* Metrics */}
          <Card className="p-4">
            <h3 className="font-medium mb-3">Metrics</h3>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Citations</dt>
                <dd className="font-medium">{paper.citation_count ?? '-'}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">PDF</dt>
                <dd>{paper.pdf_path ? 'Downloaded' : paper.pdf_url ? 'Available' : 'None'}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Embedded</dt>
                <dd>{paper.pdf_embedded ? 'Yes' : 'No'}</dd>
              </div>
            </dl>
          </Card>

          {/* Projects */}
          <Card className="p-4">
            <h3 className="font-medium mb-3">Projects</h3>
            {paper.projects.length === 0 ? (
              <p className="text-sm text-muted-foreground">Not in any project</p>
            ) : (
              <div className="flex flex-wrap gap-1">
                {paper.projects.map((project) => (
                  <Badge key={project} variant="secondary">
                    {project}
                  </Badge>
                ))}
              </div>
            )}
            <div className="relative mt-2" ref={projectDropdownRef}>
              <Button
                variant="ghost"
                size="sm"
                className="w-full"
                onClick={() => setShowProjectDropdown(!showProjectDropdown)}
              >
                <Icon icon={FolderPlus} size={14} />
                Add to Project
              </Button>
              {showProjectDropdown && (
                <div className="absolute left-0 right-0 top-full mt-1 bg-card border rounded-lg shadow-lg py-1 z-10 max-h-48 overflow-auto">
                  {projectsData?.projects.length === 0 && (
                    <p className="text-xs text-muted-foreground px-3 py-2">
                      No projects yet. Create one in the Library view.
                    </p>
                  )}
                  {projectsData?.projects.map((project) => {
                    const isInProject = paper.projects.includes(project.name)
                    return (
                      <button
                        key={project.name}
                        onClick={() => handleAddToProject(project.name)}
                        disabled={isInProject}
                        className={cn(
                          'w-full flex items-center justify-between px-3 py-1.5 text-sm text-left hover:bg-secondary',
                          isInProject && 'opacity-50 cursor-not-allowed'
                        )}
                      >
                        <span className="truncate">{project.name}</span>
                        {isInProject && <Icon icon={Check} size={14} className="text-green-500" />}
                      </button>
                    )
                  })}
                </div>
              )}
            </div>
          </Card>

          {/* Danger zone */}
          <Card className="p-4 border-destructive/50">
            <h3 className="font-medium mb-3 text-destructive">Danger Zone</h3>
            <Button variant="destructive" size="sm" className="w-full" onClick={handleDelete}>
              <Icon icon={Trash2} size={14} />
              Delete Paper
            </Button>
          </Card>
        </div>

        {/* Main content */}
        <div className="md:col-span-2 space-y-4">
          {/* Abstract */}
          <Card className="p-4">
            <h3 className="font-medium mb-3">Abstract</h3>
            <p className="text-sm leading-relaxed whitespace-pre-wrap">
              {paper.abstract || 'No abstract available.'}
            </p>
          </Card>

          {/* Note */}
          <Card className="p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-medium">Your Note</h3>
              <Button variant="ghost" size="sm" onClick={handleOpenNote}>
                <Icon icon={Pencil} size={14} />
                {note ? 'Edit' : 'Add Note'}
              </Button>
            </div>
            {note ? (
              <p className="text-sm leading-relaxed whitespace-pre-wrap">{note.content}</p>
            ) : (
              <p className="text-sm text-muted-foreground">No note yet. Add one to remember key points.</p>
            )}
          </Card>

          {/* AI Q&A */}
          <Card className="p-4">
            <div className="flex items-center gap-2 mb-3">
              <Icon icon={Sparkles} size={18} className="text-primary" />
              <h3 className="font-medium">Ask AI About This Paper</h3>
              {paper.pdf_embedded && (
                <Badge variant="secondary" className="ml-auto text-xs">PDF indexed</Badge>
              )}
            </div>
            <div className="space-y-3">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={aiQuestion}
                  onChange={(e) => setAiQuestion(e.target.value)}
                  onKeyDown={handleKeyDownAI}
                  placeholder="What is the main methodology used in this paper?"
                  className="flex-1 h-10 px-3 border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-ring"
                />
                <Button
                  onClick={handleAskQuestion}
                  disabled={askPaper.isPending || !aiQuestion.trim()}
                >
                  {askPaper.isPending ? (
                    <Icon icon={Loader2} size={16} className="animate-spin" />
                  ) : (
                    <Icon icon={Send} size={16} />
                  )}
                </Button>
              </div>

              {aiAnswer && (
                <div className="p-4 bg-secondary/50 rounded-lg">
                  <p className="text-sm leading-relaxed whitespace-pre-wrap">{aiAnswer.answer}</p>
                  {aiAnswer.sources.length > 0 && (
                    <div className="flex gap-2 mt-3 pt-3 border-t border-border/50">
                      <span className="text-xs text-muted-foreground">Sources:</span>
                      {aiAnswer.sources.map((source) => (
                        <Badge key={source} variant="outline" className="text-xs">
                          {source}
                        </Badge>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {askPaper.isError && (
                <div className="p-3 bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200 rounded text-sm">
                  Failed to get answer. Make sure an LLM API key is configured.
                </div>
              )}

              <p className="text-xs text-muted-foreground">
                {paper.pdf_embedded
                  ? 'AI uses the paper abstract and PDF content to answer questions.'
                  : 'AI uses the paper abstract to answer. Embed the PDF for more detailed answers.'}
              </p>
            </div>
          </Card>
        </div>
      </div>

      {/* Note Modal */}
      <Modal
        isOpen={showNoteModal}
        onClose={() => setShowNoteModal(false)}
        title={`Note for: ${paper.title}`}
      >
        <div className="space-y-4">
          <textarea
            value={noteContent}
            onChange={(e) => setNoteContent(e.target.value)}
            className="w-full h-48 p-3 border rounded-lg bg-background resize-none focus:outline-none focus:ring-2 focus:ring-ring"
            placeholder="Add your notes here..."
          />
          <p className="text-xs text-muted-foreground">
            Tip: Use markdown formatting. Notes are searchable in the library.
          </p>
          <div className="flex justify-between">
            {note && (
              <Button variant="destructive" size="sm" onClick={handleDeleteNote}>
                Delete Note
              </Button>
            )}
            <div className="flex gap-2 ml-auto">
              <Button variant="outline" onClick={() => setShowNoteModal(false)}>
                Cancel
              </Button>
              <Button onClick={handleSaveNote}>
                Save Note
              </Button>
            </div>
          </div>
        </div>
      </Modal>
    </div>
  )
}
