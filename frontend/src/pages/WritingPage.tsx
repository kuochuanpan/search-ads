import { useState } from 'react'
import { FileText, Search, Copy, Plus, Check, Sparkles, ChevronDown, ChevronUp, Loader2, ExternalLink, Library } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Icon } from '@/components/ui/Icon'
import { Badge } from '@/components/ui/Badge'
import { Modal } from '@/components/ui/Modal'
import { useCitationSuggestions, useGenerateBibliography } from '@/hooks/useLaTeX'
import { useProjects, useAddPapersToProject } from '@/hooks/useProjects'
import { api, CitationSuggestion, SuggestedPaper } from '@/lib/api'

// Citation type colors
const citationTypeColors: Record<string, string> = {
  foundational: 'bg-purple-500',
  review: 'bg-blue-500',
  methodological: 'bg-green-500',
  supporting: 'bg-yellow-500',
  contrasting: 'bg-orange-500',
  general: 'bg-gray-500',
}

export function WritingPage() {
  const [latexText, setLatexText] = useState('')
  const [outputFormat, setOutputFormat] = useState<'bibtex' | 'aastex'>('bibtex')
  const [selectedPapers, setSelectedPapers] = useState<Map<number, SuggestedPaper>>(new Map())
  const [expandedCitations, setExpandedCitations] = useState<Set<number>>(new Set())
  const [copiedOutput, setCopiedOutput] = useState(false)
  const [showAddModal, setShowAddModal] = useState(false)
  const [selectedProjects, setSelectedProjects] = useState<Set<string>>(new Set())
  const [addingToLibrary, setAddingToLibrary] = useState(false)

  const { data: projects } = useProjects()
  const addToProject = useAddPapersToProject()
  const citationSuggestions = useCitationSuggestions()
  const generateBibliography = useGenerateBibliography()

  const handleFindCitations = () => {
    if (!latexText.trim()) return

    citationSuggestions.mutate({
      latex_text: latexText,
      limit: 5,
      use_library: true,
      use_ads: true,
    })

    // Clear previous selections
    setSelectedPapers(new Map())
  }

  const toggleExpanded = (index: number) => {
    const newExpanded = new Set(expandedCitations)
    if (newExpanded.has(index)) {
      newExpanded.delete(index)
    } else {
      newExpanded.add(index)
    }
    setExpandedCitations(newExpanded)
  }

  const selectPaper = (citationIndex: number, paper: SuggestedPaper) => {
    const newSelected = new Map(selectedPapers)
    const currentSelection = newSelected.get(citationIndex)

    if (currentSelection?.bibcode === paper.bibcode) {
      // Deselect if clicking the same paper
      newSelected.delete(citationIndex)
    } else {
      // Select new paper
      newSelected.set(citationIndex, paper)
    }

    setSelectedPapers(newSelected)
  }

  const handleGenerateBibliography = async () => {
    const bibcodes = Array.from(selectedPapers.values()).map(p => p.bibcode)
    if (bibcodes.length === 0) return

    generateBibliography.mutate({
      bibcodes,
      format: outputFormat,
    })
  }

  const handleCopyToClipboard = async () => {
    if (!generateBibliography.data?.combined) return

    try {
      await navigator.clipboard.writeText(generateBibliography.data.combined)
      setCopiedOutput(true)
      setTimeout(() => setCopiedOutput(false), 2000)
    } catch (error) {
      console.error('Failed to copy:', error)
    }
  }

  const handleAddAllToLibrary = async () => {
    setAddingToLibrary(true)
    try {
      const bibcodes = Array.from(selectedPapers.values()).map(p => p.bibcode)

      // Import each paper
      for (const bibcode of bibcodes) {
        await api.importFromAds(bibcode)
      }

      // Add to selected projects
      for (const projectName of selectedProjects) {
        await addToProject.mutateAsync({
          projectName,
          bibcodes,
        })
      }

      setShowAddModal(false)
      setSelectedProjects(new Set())

      // Refresh suggestions to update in_library status
      handleFindCitations()
    } catch (error) {
      console.error('Failed to add papers:', error)
    } finally {
      setAddingToLibrary(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="text-center py-8">
        <h1 className="text-2xl font-semibold mb-2">Writing Assistant</h1>
        <p className="text-muted-foreground">
          Paste your LaTeX text to find and fill citations
        </p>
      </div>

      {/* LaTeX Input */}
      <Card className="p-6">
        <label className="block text-sm font-medium mb-2">Paste your LaTeX text:</label>
        <textarea
          value={latexText}
          onChange={(e) => setLatexText(e.target.value)}
          placeholder={`Dark matter halos \\cite{} follow NFW profiles, though some studies
\\cite{} suggest alternative models. The mass-concentration relation
\\citep{} is well established in simulations.`}
          className="w-full h-48 p-3 font-mono text-sm border rounded-lg bg-background resize-none focus:outline-none focus:ring-2 focus:ring-ring"
        />

        <Button
          className="w-full mt-4"
          onClick={handleFindCitations}
          disabled={citationSuggestions.isPending || !latexText.trim()}
        >
          {citationSuggestions.isPending ? (
            <>
              <Icon icon={Loader2} size={16} className="animate-spin" />
              Finding Citations...
            </>
          ) : (
            <>
              <Icon icon={Search} size={16} />
              Find Citations
            </>
          )}
        </Button>
      </Card>

      {/* Empty Citations Found */}
      {citationSuggestions.data?.suggestions && citationSuggestions.data.suggestions.length > 0 ? (
        <div className="space-y-4">
          <h3 className="font-medium">
            Found {citationSuggestions.data.total_citations} empty citation{citationSuggestions.data.total_citations !== 1 ? 's' : ''}
          </h3>

          {citationSuggestions.data.suggestions.map((citation) => (
            <CitationCard
              key={citation.citation_index}
              citation={citation}
              isExpanded={expandedCitations.has(citation.citation_index)}
              onToggleExpand={() => toggleExpanded(citation.citation_index)}
              selectedPaper={selectedPapers.get(citation.citation_index)}
              onSelectPaper={(paper) => selectPaper(citation.citation_index, paper)}
            />
          ))}
        </div>
      ) : citationSuggestions.data?.total_citations === 0 ? (
        <Card className="p-6">
          <div className="text-center py-8 text-muted-foreground">
            <Icon icon={Check} size={48} className="mx-auto mb-4 text-green-500" />
            <p>No empty citations found in your text!</p>
            <p className="text-sm mt-2">All your \\cite{'{}'} commands have keys filled in.</p>
          </div>
        </Card>
      ) : !citationSuggestions.isPending && (
        <Card className="p-6">
          <div className="text-center py-8 text-muted-foreground">
            <Icon icon={FileText} size={48} className="mx-auto mb-4 opacity-50" />
            <p>Paste LaTeX text above and click "Find Citations" to detect empty citation commands</p>
          </div>
        </Card>
      )}

      {/* Output Format & Generated Citations */}
      {selectedPapers.size > 0 && (
        <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-4">
              <span className="text-sm font-medium">Output Format:</span>
              <div className="flex gap-2">
                <Button
                  variant={outputFormat === 'bibtex' ? 'secondary' : 'outline'}
                  size="sm"
                  onClick={() => setOutputFormat('bibtex')}
                >
                  BibTeX (.bib)
                </Button>
                <Button
                  variant={outputFormat === 'aastex' ? 'secondary' : 'outline'}
                  size="sm"
                  onClick={() => setOutputFormat('aastex')}
                >
                  AASTeX (bibitem)
                </Button>
              </div>
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={handleGenerateBibliography}
              disabled={generateBibliography.isPending}
            >
              {generateBibliography.isPending ? (
                <>
                  <Icon icon={Loader2} size={14} className="animate-spin" />
                  Generating...
                </>
              ) : (
                'Generate'
              )}
            </Button>
          </div>

          <label className="block text-sm font-medium mb-2">
            Generated Citations ({selectedPapers.size} paper{selectedPapers.size !== 1 ? 's' : ''}):
          </label>
          <textarea
            readOnly
            value={generateBibliography.data?.combined || `% Click "Generate" to create ${outputFormat === 'bibtex' ? 'BibTeX' : 'AASTeX'} entries for ${selectedPapers.size} selected paper${selectedPapers.size !== 1 ? 's' : ''}`}
            className="w-full h-48 p-3 font-mono text-sm border rounded-lg bg-secondary/50 resize-none"
          />

          <div className="flex gap-2 mt-4">
            <Button
              variant="outline"
              onClick={handleCopyToClipboard}
              disabled={!generateBibliography.data?.combined}
            >
              <Icon icon={copiedOutput ? Check : Copy} size={16} />
              {copiedOutput ? 'Copied!' : 'Copy to Clipboard'}
            </Button>
            <Button
              variant="outline"
              onClick={() => setShowAddModal(true)}
              disabled={selectedPapers.size === 0}
            >
              <Icon icon={Plus} size={16} />
              Add All to Library
            </Button>
          </div>
        </Card>
      )}

      {/* Add to Library Modal */}
      <Modal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        title="Add Selected Papers to Library"
        size="sm"
      >
        <div className="space-y-4">
          <div>
            <p className="text-sm text-muted-foreground">
              Adding {selectedPapers.size} paper{selectedPapers.size !== 1 ? 's' : ''} to your library:
            </p>
            <ul className="mt-2 text-sm space-y-1">
              {Array.from(selectedPapers.values()).map((paper) => (
                <li key={paper.bibcode} className="truncate">
                  • {paper.first_author} et al. ({paper.year}) - {paper.title}
                </li>
              ))}
            </ul>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Add to project(s):</label>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {projects?.projects.map((project) => (
                <label
                  key={project.name}
                  className="flex items-center gap-2 p-2 rounded hover:bg-secondary cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={selectedProjects.has(project.name)}
                    onChange={(e) => {
                      const newSelected = new Set(selectedProjects)
                      if (e.target.checked) {
                        newSelected.add(project.name)
                      } else {
                        newSelected.delete(project.name)
                      }
                      setSelectedProjects(newSelected)
                    }}
                    className="rounded"
                  />
                  <span>{project.name}</span>
                  <span className="text-xs text-muted-foreground">({project.paper_count} papers)</span>
                </label>
              ))}
              {!projects?.projects.length && (
                <p className="text-sm text-muted-foreground p-2">No projects yet</p>
              )}
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button variant="outline" onClick={() => setShowAddModal(false)}>
              Cancel
            </Button>
            <Button onClick={handleAddAllToLibrary} disabled={addingToLibrary}>
              {addingToLibrary ? (
                <>
                  <Icon icon={Loader2} size={14} className="animate-spin" />
                  Adding...
                </>
              ) : (
                <>
                  <Icon icon={Plus} size={14} />
                  Add {selectedPapers.size} Paper{selectedPapers.size !== 1 ? 's' : ''}
                </>
              )}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}

// Citation card component for individual empty citations
interface CitationCardProps {
  citation: CitationSuggestion
  isExpanded: boolean
  onToggleExpand: () => void
  selectedPaper: SuggestedPaper | undefined
  onSelectPaper: (paper: SuggestedPaper) => void
}

function CitationCard({ citation, isExpanded, onToggleExpand, selectedPaper, onSelectPaper }: CitationCardProps) {
  return (
    <Card className="overflow-hidden">
      <div className="p-4">
        {/* Citation Context */}
        <div className="flex items-start gap-3">
          <span className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-sm font-medium">
            {citation.citation_index + 1}
          </span>
          <div className="flex-1 min-w-0">
            <div className="font-mono text-sm bg-secondary/50 p-2 rounded">
              ...{citation.context.slice(0, 150)}...
            </div>
            <div className="mt-2 flex items-center gap-2 text-sm text-muted-foreground">
              <Badge variant="outline">\\{citation.cite_type}{'{}'}</Badge>
              {citation.existing_keys?.length > 0 && (
                <span>Existing keys: {citation.existing_keys.join(', ')}</span>
              )}
            </div>
          </div>
        </div>

        {/* AI Analysis */}
        {citation.analysis && (
          <div className="mt-3 p-3 bg-secondary/30 rounded border-l-4 border-l-primary">
            <div className="flex items-center gap-2 mb-1">
              <Icon icon={Sparkles} size={14} className="text-primary" />
              <span className="text-sm font-medium">AI Analysis</span>
            </div>
            <p className="text-sm text-muted-foreground">
              Looking for a{' '}
              <span className={`px-1.5 py-0.5 rounded text-white text-xs ${citationTypeColors[citation.analysis.citation_type_needed] || 'bg-gray-500'}`}>
                {citation.analysis.citation_type_needed}
              </span>{' '}
              paper about <strong>{citation.analysis.topic}</strong>
            </p>
            {citation.analysis.reasoning && (
              <p className="text-xs text-muted-foreground mt-1">{citation.analysis.reasoning}</p>
            )}
          </div>
        )}

        {/* Suggestions */}
        {citation.suggestions.length > 0 && (
          <div className="mt-4">
            <button
              onClick={onToggleExpand}
              className="flex items-center gap-2 text-sm font-medium text-primary hover:underline"
            >
              <Icon icon={isExpanded ? ChevronUp : ChevronDown} size={14} />
              {isExpanded ? 'Hide' : 'Show'} {citation.suggestions.length} suggestions
            </button>

            {isExpanded && (
              <div className="mt-3 space-y-2">
                {citation.suggestions.map((paper) => (
                  <div
                    key={paper.bibcode}
                    onClick={() => onSelectPaper(paper)}
                    className={`p-3 rounded border cursor-pointer transition-colors ${
                      selectedPaper?.bibcode === paper.bibcode
                        ? 'border-primary bg-primary/5'
                        : 'border-border hover:border-primary/50 hover:bg-secondary/30'
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <div className="flex-shrink-0">
                        <input
                          type="radio"
                          checked={selectedPaper?.bibcode === paper.bibcode}
                          onChange={() => onSelectPaper(paper)}
                          className="mt-1"
                        />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <h5 className="text-sm font-medium line-clamp-2">{paper.title}</h5>
                            <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                              <span>{paper.first_author} et al. ({paper.year})</span>
                              {paper.citation_count !== undefined && (
                                <>
                                  <span>·</span>
                                  <span>{paper.citation_count.toLocaleString()} citations</span>
                                </>
                              )}
                              {paper.in_library && (
                                <>
                                  <span>·</span>
                                  <span className="flex items-center gap-1 text-green-600">
                                    <Icon icon={Library} size={10} />
                                    In library
                                  </span>
                                </>
                              )}
                            </div>
                          </div>
                          <div className="flex-shrink-0 text-right">
                            <span className={`text-sm font-medium ${
                              paper.relevance_score >= 0.8 ? 'text-green-600' :
                              paper.relevance_score >= 0.6 ? 'text-yellow-600' : 'text-gray-600'
                            }`}>
                              {Math.round(paper.relevance_score * 100)}%
                            </span>
                          </div>
                        </div>
                        {paper.relevance_explanation && (
                          <p className="text-xs text-muted-foreground mt-2 line-clamp-2">
                            {paper.relevance_explanation}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Selected Paper Summary */}
        {selectedPaper && !isExpanded && (
          <div className="mt-3 p-2 bg-primary/5 rounded border border-primary/30 flex items-center gap-2">
            <Icon icon={Check} size={14} className="text-primary" />
            <span className="text-sm">
              Selected: <strong>{selectedPaper.first_author} et al. ({selectedPaper.year})</strong>
            </span>
            <button
              onClick={(e) => {
                e.stopPropagation()
                window.open(`https://ui.adsabs.harvard.edu/abs/${selectedPaper.bibcode}/abstract`, '_blank')
              }}
              className="ml-auto text-primary hover:underline text-xs flex items-center gap-1"
            >
              <Icon icon={ExternalLink} size={10} />
              ADS
            </button>
          </div>
        )}

        {/* Error */}
        {citation.error && (
          <div className="mt-3 p-2 bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200 rounded text-sm">
            Error: {citation.error}
          </div>
        )}
      </div>
    </Card>
  )
}
