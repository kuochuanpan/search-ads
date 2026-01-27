import { useState } from 'react'
import { Search, Sparkles, BookOpen, FileText, Library, Plus, Check, ChevronDown, ChevronUp, ExternalLink, Copy, FileCode } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Icon } from '@/components/ui/Icon'
import { Badge } from '@/components/ui/Badge'
import { Modal } from '@/components/ui/Modal'
import { useAISearch } from '@/hooks/useSearch'
import { useProjects, useAddPapersToProject } from '@/hooks/useProjects'
import { api, SearchResultItem } from '@/lib/api'

type CopiedType = 'bibtex' | 'aastex' | null

type SearchMode = 'natural' | 'keywords' | 'similar'
type SearchScope = 'library' | 'ads' | 'pdf'

// Citation type colors and descriptions
const citationTypeInfo: Record<string, { color: string; description: string }> = {
  foundational: { color: 'bg-purple-500', description: 'Seminal papers establishing fundamental concepts' },
  review: { color: 'bg-blue-500', description: 'Review articles summarizing a field' },
  methodological: { color: 'bg-green-500', description: 'Papers describing methods/techniques' },
  supporting: { color: 'bg-yellow-500', description: 'Papers with supporting evidence' },
  contrasting: { color: 'bg-orange-500', description: 'Papers to contrast against' },
  general: { color: 'bg-gray-500', description: 'General reference' },
}

export function SearchPage() {
  const [query, setQuery] = useState('')
  const [mode, setMode] = useState<SearchMode>('natural')
  const [scopes, setScopes] = useState<Set<SearchScope>>(new Set(['library']))
  const [minYear, setMinYear] = useState<number | undefined>()
  const [minCitations, setMinCitations] = useState<number | undefined>()
  const [expandedResults, setExpandedResults] = useState<Set<string>>(new Set())
  const [showAddModal, setShowAddModal] = useState(false)
  const [selectedForAdd, setSelectedForAdd] = useState<SearchResultItem | null>(null)
  const [selectedProjects, setSelectedProjects] = useState<Set<string>>(new Set())
  const [copiedState, setCopiedState] = useState<{ bibcode: string; type: CopiedType } | null>(null)
  const [addedToLibrary, setAddedToLibrary] = useState<Set<string>>(new Set())

  // Streaming state
  const [streamResults, setStreamResults] = useState<SearchResultItem[]>([])
  const [aiAnalysis, setAiAnalysis] = useState<any>(null)
  const [isStreaming, setIsStreaming] = useState(false)
  const [searchProgress, setSearchProgress] = useState<{
    ads?: { current: number, total?: number, message: string },
    library?: { current: number, total?: number, message: string },
    natural?: { message: string }
  }>({})

  const { data: projects } = useProjects()
  const addToProject = useAddPapersToProject()
  const aiSearch = useAISearch()

  const toggleScope = (scope: SearchScope) => {
    const newScopes = new Set(scopes)
    if (newScopes.has(scope)) {
      newScopes.delete(scope)
    } else {
      newScopes.add(scope)
    }
    setScopes(newScopes)
  }

  const handleSearch = async () => {
    if (!query.trim()) return

    // Clear locally tracked additions when performing a new search
    setAddedToLibrary(new Set())
    setExpandedResults(new Set())

    // If Natural Language mode, use Streaming AI search
    if (mode === 'natural') {
      setIsStreaming(true)
      setStreamResults([])
      setAiAnalysis(null)
      setSearchProgress({})

      const params = {
        query: query.trim(),
        limit: 20,
        search_library: scopes.has('library'),
        search_ads: scopes.has('ads'),
        search_pdf: scopes.has('pdf'),
        min_year: minYear,
        min_citations: minCitations,
        use_llm: true,
      }

      try {
        for await (const event of api.streamAISearch(params)) {
          if (event.type === 'progress') {
            setSearchProgress(prev => ({ ...prev, natural: { message: event.message || 'Processing...' } }))
          } else if (event.type === 'analysis' && event.data) {
            setAiAnalysis(event.data)
          } else if (event.type === 'result' && event.data) {
            // The result event currently allows sending the whole response object
            // But my backend sends 'AISearchResponse' as data for 'result' type
            if (event.data.results) {
              setStreamResults(event.data.results)
            }
            if (event.data.ai_analysis) {
              setAiAnalysis(event.data.ai_analysis)
            }
          } else if (event.type === 'log') {
            // Optional: show logs? For now just ignore or log to console
            console.log('[Search Log]', event.message)
          }
        }
      } catch (e) {
        console.error('AI Search stream failed', e)
        // Fallback or show error?
      } finally {
        setIsStreaming(false)
        setSearchProgress({})
      }
      return
    }

    // Keyword/Similar mode: Use Streaming
    setIsStreaming(true)
    setStreamResults([])
    setSearchProgress({})

    // Create promises for each scope
    const tasks = []

    if (scopes.has('ads')) {
      tasks.push((async () => {
        try {
          setSearchProgress(prev => ({ ...prev, ads: { current: 0, message: 'Starting ADS search...' } }))
          for await (const event of api.streamSearchAds(query.trim(), 20)) {
            if (event.type === 'progress') {
              setSearchProgress(prev => ({ ...prev, ads: { current: event.current || 0, total: event.total, message: event.message || '' } }))
            } else if (event.type === 'result' && event.data) {
              setStreamResults(prev => {
                // Deduplicate
                if (prev.some(p => p.bibcode === event.data?.bibcode)) return prev
                return [...prev, { ...event.data, source: 'ads' } as SearchResultItem]
              })
            }
          }
        } catch (e) {
          console.error('ADS stream failed', e)
        } finally {
          setSearchProgress(prev => ({ ...prev, ads: undefined }))
        }
      })())
    }

    if (scopes.has('library')) {
      tasks.push((async () => {
        try {
          setSearchProgress(prev => ({ ...prev, library: { current: 0, message: 'Starting library search...' } }))
          for await (const event of api.streamSearchSemantic(query.trim(), 20, minYear, minCitations)) {
            if (event.type === 'progress') {
              setSearchProgress(prev => ({ ...prev, library: { current: event.current || 0, total: event.total, message: event.message || '' } }))
            } else if (event.type === 'result' && event.data) {
              setStreamResults(prev => {
                // Deduplicate
                if (prev.some(p => p.bibcode === event.data?.bibcode)) return prev
                return [...prev, { ...event.data, source: 'library' } as SearchResultItem]
              })
            }
          }
        } catch (e) {
          console.error('Library stream failed', e)
        } finally {
          setSearchProgress(prev => ({ ...prev, library: undefined }))
        }
      })())
    }

    await Promise.all(tasks)
    setIsStreaming(false)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSearch()
    }
  }

  const toggleExpanded = (bibcode: string) => {
    const newExpanded = new Set(expandedResults)
    if (newExpanded.has(bibcode)) {
      newExpanded.delete(bibcode)
    } else {
      newExpanded.add(bibcode)
    }
    setExpandedResults(newExpanded)
  }

  const openAddModal = (paper: SearchResultItem) => {
    setSelectedForAdd(paper)
    setSelectedProjects(new Set())
    setShowAddModal(true)
  }

  const handleAddToLibrary = async () => {
    if (!selectedForAdd) return

    try {
      // Import the paper first
      await api.importFromAds(selectedForAdd.bibcode)

      // Add to selected projects
      for (const projectName of selectedProjects) {
        await addToProject.mutateAsync({
          projectName,
          bibcodes: [selectedForAdd.bibcode],
        })
      }

      // Mark the paper as added locally to update the UI without re-running search
      setAddedToLibrary(prev => new Set(prev).add(selectedForAdd.bibcode))

      setShowAddModal(false)
      setSelectedForAdd(null)
    } catch (error) {
      console.error('Failed to add paper:', error)
    }
  }

  const copyBibTeX = async (paper: SearchResultItem) => {
    try {
      const result = await api.generateBibliography([paper.bibcode], 'bibtex')
      await navigator.clipboard.writeText(result.combined)
      setCopiedState({ bibcode: paper.bibcode, type: 'bibtex' })
      setTimeout(() => setCopiedState(null), 2000)
    } catch (error) {
      console.error('Failed to copy BibTeX:', error)
    }
  }

  const copyAASTeX = async (paper: SearchResultItem) => {
    try {
      const result = await api.generateBibliography([paper.bibcode], 'aastex')
      await navigator.clipboard.writeText(result.combined)
      setCopiedState({ bibcode: paper.bibcode, type: 'aastex' })
      setTimeout(() => setCopiedState(null), 2000)
    } catch (error) {
      console.error('Failed to copy AASTeX:', error)
    }
  }

  const getRelevanceColor = (score: number) => {
    if (score >= 0.8) return 'text-green-600 dark:text-green-400'
    if (score >= 0.6) return 'text-yellow-600 dark:text-yellow-400'
    return 'text-gray-600 dark:text-gray-400'
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="text-center py-8">
        <h1 className="text-2xl font-semibold mb-2">Discover Papers</h1>
        <p className="text-muted-foreground">
          Search your library and ADS using natural language or keywords
        </p>
      </div>

      {/* Search Input */}
      <Card className="p-6">
        <label className="block text-sm font-medium mb-2">What are you looking for?</label>
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="e.g., I need a paper that established the connection between AGN feedback and quenching of star formation in massive galaxies"
          className="w-full h-24 p-3 border rounded-lg bg-background resize-none focus:outline-none focus:ring-2 focus:ring-ring"
        />

        {/* Search Mode */}
        <div className="flex items-center gap-4 mt-4">
          <span className="text-sm text-muted-foreground">Search mode:</span>
          <div className="flex gap-2">
            <Button
              variant={mode === 'natural' ? 'secondary' : 'outline'}
              size="sm"
              onClick={() => setMode('natural')}
            >
              <Icon icon={Sparkles} size={14} />
              Natural Language
            </Button>
            <Button
              variant={mode === 'keywords' ? 'secondary' : 'outline'}
              size="sm"
              onClick={() => setMode('keywords')}
            >
              Keywords
            </Button>
            <Button
              variant={mode === 'similar' ? 'secondary' : 'outline'}
              size="sm"
              onClick={() => setMode('similar')}
            >
              Similar to Paper
            </Button>
          </div>
        </div>

        {/* Search Scope */}
        <div className="flex items-center gap-4 mt-3">
          <span className="text-sm text-muted-foreground">Search in:</span>
          <div className="flex gap-2">
            <Button
              variant={scopes.has('library') ? 'secondary' : 'outline'}
              size="sm"
              onClick={() => toggleScope('library')}
            >
              <Icon icon={BookOpen} size={14} />
              Your Library
            </Button>
            <Button
              variant={scopes.has('ads') ? 'secondary' : 'outline'}
              size="sm"
              onClick={() => toggleScope('ads')}
            >
              <Icon icon={Search} size={14} />
              ADS
            </Button>
            <Button
              variant={scopes.has('pdf') ? 'secondary' : 'outline'}
              size="sm"
              onClick={() => toggleScope('pdf')}
            >
              <Icon icon={FileText} size={14} />
              PDF Full-text
            </Button>
          </div>
        </div>

        {/* Advanced Filters */}
        <div className="flex items-center gap-4 mt-3">
          <span className="text-sm text-muted-foreground">Filters:</span>
          <div className="flex gap-4">
            <div className="flex items-center gap-2">
              <label className="text-sm">Min Year:</label>
              <input
                type="number"
                value={minYear || ''}
                onChange={(e) => setMinYear(e.target.value ? parseInt(e.target.value) : undefined)}
                placeholder="2000"
                className="w-20 h-8 px-2 text-sm border rounded bg-background"
              />
            </div>
            <div className="flex items-center gap-2">
              <label className="text-sm">Min Citations:</label>
              <input
                type="number"
                value={minCitations || ''}
                onChange={(e) => setMinCitations(e.target.value ? parseInt(e.target.value) : undefined)}
                placeholder="0"
                className="w-20 h-8 px-2 text-sm border rounded bg-background"
              />
            </div>
          </div>
        </div>

        <Button
          className="w-full mt-4"
          onClick={handleSearch}
          disabled={(aiSearch.isPending || isStreaming) || !query.trim()}
        >
          <Icon icon={Search} size={16} />
          {aiSearch.isPending || isStreaming ? 'Searching...' : 'Search'}
        </Button>

        {/* Progress Bars for Streaming */}
        {isStreaming && (
          <div className="mt-4 space-y-2">
            {searchProgress.natural && (
              <div className="text-sm">
                <div className="flex justify-between mb-1">
                  <span>{searchProgress.natural.message}</span>
                </div>
                <div className="w-full bg-secondary rounded-full h-1.5 overflow-hidden">
                  <div className="bg-primary h-full transition-all duration-300 animate-pulse" style={{ width: '100%' }}></div>
                </div>
              </div>
            )}
            {searchProgress.ads && (
              <div className="text-sm">
                <div className="flex justify-between mb-1">
                  <span>ADS: {searchProgress.ads.message}</span>
                  {searchProgress.ads.total && <span>{Math.round((searchProgress.ads.current / searchProgress.ads.total) * 100)}%</span>}
                </div>
                <div className="w-full bg-secondary rounded-full h-1.5 overflow-hidden">
                  <div className="bg-blue-500 h-full transition-all duration-300 animate-pulse" style={{ width: '100%' }}></div>
                </div>
              </div>
            )}
            {searchProgress.library && (
              <div className="text-sm">
                <div className="flex justify-between mb-1">
                  <span>Library: {searchProgress.library.message}</span>
                  {searchProgress.library.total ? (
                    <span>{Math.round((searchProgress.library.current / searchProgress.library.total) * 100)}%</span>
                  ) : null}
                </div>
                <div className="w-full bg-secondary rounded-full h-1.5">
                  <div
                    className="bg-green-500 h-full transition-all duration-300"
                    style={{ width: searchProgress.library.total ? `${(searchProgress.library.current / searchProgress.library.total) * 100}%` : '100%' }}
                  ></div>
                </div>
              </div>
            )}
          </div>
        )}
      </Card>

      {/* AI Analysis */}
      {(aiSearch.data?.ai_analysis || aiAnalysis) && (
        <Card className="p-6 border-l-4 border-l-primary">
          <div className="flex items-center gap-2 mb-3">
            <Icon icon={Sparkles} size={18} className="text-primary" />
            <h3 className="font-medium">AI Analysis</h3>
          </div>
          <div className="space-y-2 text-sm">
            <p>
              <span className="font-medium">Looking for:</span>{' '}
              <span className={`px-2 py-0.5 rounded ${citationTypeInfo[(aiSearch.data?.ai_analysis || aiAnalysis).citation_type_needed]?.color || 'bg-gray-500'} text-white`}>
                {(aiSearch.data?.ai_analysis || aiAnalysis).citation_type_needed}
              </span>{' '}
              paper about <strong>{(aiSearch.data?.ai_analysis || aiAnalysis).topic}</strong>
            </p>
            <p className="text-muted-foreground">{(aiSearch.data?.ai_analysis || aiAnalysis).reasoning}</p>
            {(aiSearch.data?.ai_analysis || aiAnalysis).keywords.length > 0 && (
              <div className="flex items-center gap-2 mt-2">
                <span className="text-muted-foreground">Keywords:</span>
                {(aiSearch.data?.ai_analysis || aiAnalysis).keywords.map((kw: string) => (
                  <Badge key={kw} variant="outline">{kw}</Badge>
                ))}
              </div>
            )}
          </div>
        </Card>
      )}

      {/* Results (Unified Display) */}
      {(
        (aiSearch.data?.results && aiSearch.data.results.length > 0) ||
        (streamResults.length > 0)
      ) && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-medium">
                Results ({aiSearch.data?.total_count || streamResults.length} papers)
              </h3>
            </div>

            {(aiSearch.data?.results || streamResults).map((paper, index) => (
              <Card key={`${paper.bibcode}-${index}`} className="overflow-hidden">
                <div className="p-4">
                  {/* Header row */}
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      {/* Rank and Title */}
                      <div className="flex items-start gap-3">
                        <span className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-sm font-medium">
                          {index + 1}
                        </span>
                        <div className="flex-1 min-w-0">
                          <button
                            onClick={() => toggleExpanded(paper.bibcode)}
                            className="text-left w-full group"
                          >
                            <h4 className="font-medium group-hover:text-primary transition-colors line-clamp-2">
                              {paper.title}
                            </h4>
                          </button>
                          <div className="flex items-center gap-2 mt-1 text-sm text-muted-foreground">
                            <span>{paper.first_author}{paper.year ? ` et al. (${paper.year})` : ''}</span>
                            {paper.citation_count !== undefined && (
                              <>
                                <span>·</span>
                                <span>{paper.citation_count.toLocaleString()} citations</span>
                              </>
                            )}
                            {(paper.in_library || addedToLibrary.has(paper.bibcode)) && (
                              <>
                                <span>·</span>
                                <span className="flex items-center gap-1 text-green-600 dark:text-green-400">
                                  <Icon icon={Library} size={12} />
                                  In library
                                </span>
                              </>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Relevance Score */}
                    <div className="flex-shrink-0 text-right">
                      <div className={`text-lg font-semibold ${getRelevanceColor(paper.relevance_score)}`}>
                        {Math.round(paper.relevance_score * 100)}%
                      </div>
                      <Badge
                        className={`${citationTypeInfo[paper.citation_type]?.color || 'bg-gray-500'} text-white`}
                      >
                        {paper.citation_type}
                      </Badge>
                    </div>
                  </div>

                  {/* Why this paper? */}
                  {paper.relevance_explanation && (
                    <div className="mt-3 p-3 bg-secondary/50 rounded text-sm">
                      <span className="font-medium">Why this paper: </span>
                      {paper.relevance_explanation}
                    </div>
                  )}

                  {/* Expanded content */}
                  {expandedResults.has(paper.bibcode) && (
                    <div className="mt-4 pt-4 border-t">
                      {paper.abstract && (
                        <div className="mb-4">
                          <h5 className="text-sm font-medium mb-2">Abstract</h5>
                          <p className="text-sm text-muted-foreground">{paper.abstract}</p>
                        </div>
                      )}

                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Badge variant="outline">
                          Source: {paper.source === 'library' ? 'Library' : paper.source === 'ads' ? 'ADS' : 'PDF'}
                        </Badge>
                        {paper.has_pdf && <Badge variant="outline">Has PDF</Badge>}
                        {paper.pdf_embedded && <Badge variant="outline">Searchable PDF</Badge>}
                      </div>
                    </div>
                  )}

                  {/* Actions */}
                  <div className="flex items-center justify-between mt-4 pt-4 border-t">
                    <div className="flex items-center gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => toggleExpanded(paper.bibcode)}
                      >
                        <Icon icon={expandedResults.has(paper.bibcode) ? ChevronUp : ChevronDown} size={14} />
                        {expandedResults.has(paper.bibcode) ? 'Less' : 'More'}
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => window.open(`https://ui.adsabs.harvard.edu/abs/${paper.bibcode}/abstract`, '_blank')}
                      >
                        <Icon icon={ExternalLink} size={14} />
                        ADS
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => copyBibTeX(paper)}
                      >
                        <Icon icon={copiedState?.bibcode === paper.bibcode && copiedState?.type === 'bibtex' ? Check : Copy} size={14} />
                        {copiedState?.bibcode === paper.bibcode && copiedState?.type === 'bibtex' ? 'Copied!' : 'BibTeX'}
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => copyAASTeX(paper)}
                      >
                        <Icon icon={copiedState?.bibcode === paper.bibcode && copiedState?.type === 'aastex' ? Check : FileCode} size={14} />
                        {copiedState?.bibcode === paper.bibcode && copiedState?.type === 'aastex' ? 'Copied!' : 'AASTeX'}
                      </Button>
                    </div>

                    <div>
                      {(paper.in_library || addedToLibrary.has(paper.bibcode)) ? (
                        <Button variant="outline" size="sm" disabled>
                          <Icon icon={Check} size={14} />
                          In Library
                        </Button>
                      ) : (
                        <Button
                          variant="default"
                          size="sm"
                          onClick={() => openAddModal(paper)}
                        >
                          <Icon icon={Plus} size={14} />
                          Add to Library
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}

      {/* Empty state */}
      {!aiSearch.isPending && !isStreaming && !aiSearch.data?.results?.length && !streamResults.length && (
        <Card className="p-6">
          <div className="text-center py-12 text-muted-foreground">
            <Icon icon={Search} size={48} className="mx-auto mb-4 opacity-50" />
            <p>Enter a query above to search for papers</p>
          </div>
        </Card>
      )}

      {/* Error state */}
      {aiSearch.isError && (
        <Card className="p-6 border-red-500">
          <div className="text-center py-4 text-red-600 dark:text-red-400">
            <p>Search failed: {aiSearch.error?.message || 'Unknown error'}</p>
          </div>
        </Card>
      )}

      {/* Add to Library Modal */}
      <Modal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        title="Add to Library"
        size="sm"
      >
        {selectedForAdd && (
          <div className="space-y-4">
            <div>
              <h4 className="font-medium line-clamp-2">{selectedForAdd.title}</h4>
              <p className="text-sm text-muted-foreground mt-1">
                {selectedForAdd.first_author} et al. ({selectedForAdd.year})
              </p>
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
              <Button onClick={handleAddToLibrary}>
                <Icon icon={Plus} size={14} />
                Add Paper
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}
