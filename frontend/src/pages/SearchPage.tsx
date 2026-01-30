import { useState, useEffect, useRef, useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import {
  Search, Sparkles, BookOpen, FileText, Globe,
  Plus, Check, ChevronDown, ChevronUp, ExternalLink, Copy, FileCode, Library, Loader2,
} from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Icon } from '@/components/ui/Icon'
import { Badge } from '@/components/ui/Badge'
import { Modal } from '@/components/ui/Modal'
import { useUnifiedSearch, UnifiedSearchParams } from '@/hooks/useSearch'
import { useProjects, useAddPapersToProject } from '@/hooks/useProjects'
import { api, SearchMode, SearchScope, UnifiedSearchResultItem } from '@/lib/api'

type CopiedType = 'bibtex' | 'aastex' | 'bibcode' | null

const VISIBLE_PAGE_SIZE = 20

const SEARCH_STATE_KEY = 'search-page-state'

// Citation type colors
const citationTypeInfo: Record<string, { color: string }> = {
  foundational: { color: 'bg-purple-500' },
  review: { color: 'bg-blue-500' },
  methodological: { color: 'bg-green-500' },
  supporting: { color: 'bg-yellow-500' },
  contrasting: { color: 'bg-orange-500' },
  general: { color: 'bg-gray-500' },
}

export function SearchPage() {
  const navigate = useNavigate()

  // Search state
  const [query, setQuery] = useState('')
  const [mode, setMode] = useState<SearchMode>('natural')
  const [scope, setScope] = useState<SearchScope>('library')
  const [minYear, setMinYear] = useState<number | undefined>()
  const [maxYear, setMaxYear] = useState<number | undefined>()
  const [minCitations, setMinCitations] = useState<number | undefined>()

  // Submitted search params (triggers query)
  const [searchParams, setSearchParams] = useState<UnifiedSearchParams | null>(null)
  const searchIdRef = useRef(0)

  // UI state
  const [visibleCount, setVisibleCount] = useState(VISIBLE_PAGE_SIZE)
  const [expandedResults, setExpandedResults] = useState<Set<string>>(new Set())
  const [showAddModal, setShowAddModal] = useState(false)
  const [selectedForAdd, setSelectedForAdd] = useState<UnifiedSearchResultItem | null>(null)
  const [selectedProjects, setSelectedProjects] = useState<Set<string>>(new Set())
  const [copiedState, setCopiedState] = useState<{ bibcode: string; type: CopiedType } | null>(null)
  const [addedToLibrary, setAddedToLibrary] = useState<Set<string>>(new Set())
  const [isAddingPaper, setIsAddingPaper] = useState(false)

  // Refs
  const sentinelRef = useRef<HTMLDivElement>(null)
  const hasRestoredState = useRef(false)

  const queryClient = useQueryClient()
  const { data: projects } = useProjects()
  const addToProject = useAddPapersToProject()

  // Unified search query
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isFetching,
    isLoading,
    isError,
    error,
  } = useUnifiedSearch(searchParams)

  // Flatten all pages into one results array
  const allResults = data?.pages.flatMap(p => p.results) ?? []
  const displayedResults = allResults.slice(0, visibleCount)
  const aiAnalysis = data?.pages[0]?.ai_analysis
  const totalAvailable = data?.pages[0]?.total_available ?? 0

  // Scroll restoration on mount
  useEffect(() => {
    if (hasRestoredState.current) return
    hasRestoredState.current = true

    const saved = sessionStorage.getItem(SEARCH_STATE_KEY)
    if (!saved) return

    try {
      const state = JSON.parse(saved)
      setQuery(state.query || '')
      setMode(state.mode || 'natural')
      setScope(state.scope || 'library')
      setMinYear(state.minYear)
      setMaxYear(state.maxYear)
      setMinCitations(state.minCitations)
      setVisibleCount(state.visibleCount || VISIBLE_PAGE_SIZE)
      setAddedToLibrary(new Set(state.addedToLibrary || []))

      // Trigger the search to restore results
      if (state.query) {
        searchIdRef.current = state.searchId || 1
        setSearchParams({
          query: state.query,
          mode: state.mode || 'natural',
          scope: state.scope || 'library',
          min_year: state.minYear,
          max_year: state.maxYear,
          min_citations: state.minCitations,
          searchId: searchIdRef.current,
        })
      }

      // Restore scroll after results load
      if (state.scrollY) {
        const scrollY = state.scrollY
        const tryRestore = () => {
          requestAnimationFrame(() => {
            window.scrollTo(0, scrollY)
          })
        }
        // Wait a bit for results to render
        setTimeout(tryRestore, 100)
        setTimeout(tryRestore, 300)
        setTimeout(tryRestore, 600)
      }
    } catch {
      // ignore
    }
    sessionStorage.removeItem(SEARCH_STATE_KEY)
  }, [])

  // IntersectionObserver for infinite scroll
  useEffect(() => {
    const sentinel = sentinelRef.current
    if (!sentinel) return

    const observer = new IntersectionObserver(
      (entries) => {
        if (!entries[0].isIntersecting) return

        if (visibleCount < allResults.length) {
          // Reveal more from client cache
          setVisibleCount(prev => prev + VISIBLE_PAGE_SIZE)
        } else if (hasNextPage && !isFetchingNextPage) {
          // Need to fetch next batch from backend
          fetchNextPage()
        }
      },
      { rootMargin: '400px' } // Start loading well before user reaches bottom
    )

    observer.observe(sentinel)
    return () => observer.disconnect()
  }, [visibleCount, allResults.length, hasNextPage, isFetchingNextPage, fetchNextPage])

  // Background prefetch: when user is within 80% of cached results, prefetch next batch
  useEffect(() => {
    if (
      visibleCount >= allResults.length * 0.6 &&
      hasNextPage &&
      !isFetchingNextPage
    ) {
      fetchNextPage()
    }
  }, [visibleCount, allResults.length, hasNextPage, isFetchingNextPage, fetchNextPage])

  // Handlers
  const handleSearch = () => {
    if (!query.trim()) return

    setAddedToLibrary(new Set())
    setExpandedResults(new Set())
    setVisibleCount(VISIBLE_PAGE_SIZE)

    searchIdRef.current += 1
    setSearchParams({
      query: query.trim(),
      mode,
      scope,
      min_year: minYear,
      max_year: maxYear,
      min_citations: minCitations,
      searchId: searchIdRef.current,
    })
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSearch()
    }
  }

  const toggleExpanded = (bibcode: string) => {
    setExpandedResults(prev => {
      const next = new Set(prev)
      if (next.has(bibcode)) next.delete(bibcode)
      else next.add(bibcode)
      return next
    })
  }

  const handlePaperClick = useCallback((paper: UnifiedSearchResultItem) => {
    if (!paper.in_library && !addedToLibrary.has(paper.bibcode)) return

    // Save state for scroll restoration
    sessionStorage.setItem(SEARCH_STATE_KEY, JSON.stringify({
      query,
      mode,
      scope,
      minYear,
      maxYear,
      minCitations,
      visibleCount,
      scrollY: window.scrollY,
      addedToLibrary: Array.from(addedToLibrary),
      searchId: searchIdRef.current,
    }))

    navigate({
      to: '/library/$bibcode',
      params: { bibcode: paper.bibcode },
      state: { from: 'search' } as any,
    })
  }, [query, mode, scope, minYear, maxYear, minCitations, visibleCount, addedToLibrary, navigate])

  const openAddModal = (paper: UnifiedSearchResultItem) => {
    setSelectedForAdd(paper)
    setSelectedProjects(new Set())
    setShowAddModal(true)
  }

  const handleAddToLibrary = async () => {
    if (!selectedForAdd) return

    setIsAddingPaper(true)
    try {
      await api.importFromAds(selectedForAdd.bibcode)

      for (const projectName of selectedProjects) {
        await addToProject.mutateAsync({
          projectName,
          bibcodes: [selectedForAdd.bibcode],
        })
      }

      setAddedToLibrary(prev => new Set(prev).add(selectedForAdd.bibcode))
      queryClient.invalidateQueries({ queryKey: ['papers'] })
      queryClient.invalidateQueries({ queryKey: ['stats'] })
      setShowAddModal(false)
      setSelectedForAdd(null)
    } catch (error) {
      console.error('Failed to add paper:', error)
    } finally {
      setIsAddingPaper(false)
    }
  }

  const copyBibTeX = async (paper: UnifiedSearchResultItem) => {
    try {
      const result = await api.generateBibliography([paper.bibcode], 'bibtex')
      await navigator.clipboard.writeText(result.combined)
      setCopiedState({ bibcode: paper.bibcode, type: 'bibtex' })
      setTimeout(() => setCopiedState(null), 2000)
    } catch (error) {
      console.error('Failed to copy BibTeX:', error)
    }
  }

  const copyAASTeX = async (paper: UnifiedSearchResultItem) => {
    try {
      const result = await api.generateBibliography([paper.bibcode], 'aastex')
      await navigator.clipboard.writeText(result.combined)
      setCopiedState({ bibcode: paper.bibcode, type: 'aastex' })
      setTimeout(() => setCopiedState(null), 2000)
    } catch (error) {
      console.error('Failed to copy AASTeX:', error)
    }
  }

  const copyBibcode = async (paper: UnifiedSearchResultItem) => {
    try {
      await navigator.clipboard.writeText(paper.bibcode)
      setCopiedState({ bibcode: paper.bibcode, type: 'bibcode' })
      setTimeout(() => setCopiedState(null), 2000)
    } catch (error) {
      console.error('Failed to copy Bibcode:', error)
    }
  }

  const getRelevanceColor = (score: number) => {
    if (score >= 0.8) return 'text-green-600 dark:text-green-400'
    if (score >= 0.6) return 'text-yellow-600 dark:text-yellow-400'
    return 'text-gray-600 dark:text-gray-400'
  }

  const isSearching = isLoading || (isFetching && !isFetchingNextPage)

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
          placeholder={
            scope === 'ads' && mode === 'keywords'
              ? 'e.g., author:"Einstein" title:"relativity" year:1905'
              : 'e.g., I need a paper about AGN feedback and quenching of star formation in massive galaxies'
          }
          className="w-full h-24 p-3 border rounded-lg bg-background resize-none focus:outline-none focus:ring-2 focus:ring-ring"
        />

        {/* Search Mode */}
        <div className="flex items-center gap-4 mt-4">
          <span className="text-sm text-muted-foreground">Mode:</span>
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
          </div>
        </div>

        {/* Search Scope */}
        <div className="flex items-center gap-4 mt-3">
          <span className="text-sm text-muted-foreground">Search in:</span>
          <div className="flex gap-2">
            <Button
              variant={scope === 'library' ? 'secondary' : 'outline'}
              size="sm"
              onClick={() => setScope('library')}
            >
              <Icon icon={BookOpen} size={14} />
              Your Library
            </Button>
            <Button
              variant={scope === 'pdf' ? 'secondary' : 'outline'}
              size="sm"
              onClick={() => setScope('pdf')}
            >
              <Icon icon={FileText} size={14} />
              PDF Full-text
            </Button>
            <Button
              variant={scope === 'ads' ? 'secondary' : 'outline'}
              size="sm"
              onClick={() => setScope('ads')}
            >
              <Icon icon={Globe} size={14} />
              ADS
            </Button>
          </div>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-4 mt-3 flex-wrap">
          <span className="text-sm text-muted-foreground">Filters:</span>
          <div className="flex gap-4 flex-wrap">
            <div className="flex items-center gap-2">
              <label className="text-sm">Min Year:</label>
              <input
                type="number"
                value={minYear ?? ''}
                onChange={(e) => setMinYear(e.target.value ? parseInt(e.target.value) : undefined)}
                placeholder="2000"
                className="w-20 h-8 px-2 text-sm border rounded bg-background"
              />
            </div>
            <div className="flex items-center gap-2">
              <label className="text-sm">Max Year:</label>
              <input
                type="number"
                value={maxYear ?? ''}
                onChange={(e) => setMaxYear(e.target.value ? parseInt(e.target.value) : undefined)}
                placeholder="2025"
                className="w-20 h-8 px-2 text-sm border rounded bg-background"
              />
            </div>
            <div className="flex items-center gap-2">
              <label className="text-sm">Min Citations:</label>
              <input
                type="number"
                value={minCitations ?? ''}
                onChange={(e) => setMinCitations(e.target.value ? parseInt(e.target.value) : undefined)}
                placeholder="0"
                className="w-20 h-8 px-2 text-sm border rounded bg-background"
              />
            </div>
          </div>
        </div>

        <Button
          className="w-full mt-4 bg-pink-500 hover:bg-pink-600 text-white"
          onClick={handleSearch}
          disabled={isSearching || !query.trim()}
        >
          <Icon icon={Search} size={16} />
          {isSearching ? 'Searching...' : 'Search'}
        </Button>

        {/* Animated progress bar */}
        {isSearching && (
          <div className="mt-4 space-y-2">
            <div className="text-sm text-muted-foreground">
              {mode === 'natural'
                ? 'Analyzing query with AI and searching...'
                : `Searching ${scope === 'library' ? 'your library' : scope === 'pdf' ? 'PDF full-text' : 'NASA ADS'}...`}
            </div>
            <div className="w-full bg-pink-100 dark:bg-pink-950 rounded-full h-2 overflow-hidden">
              <div
                className="h-full rounded-full"
                style={{
                  background: 'linear-gradient(90deg, transparent, rgba(244,114,182,0.3), rgba(244,114,182,0.8), rgba(251,113,133,0.9), rgba(244,114,182,0.8), rgba(244,114,182,0.3), transparent)',
                  backgroundSize: '200% 100%',
                  animation: 'shimmer 1.5s ease-in-out infinite',
                  width: '100%',
                  boxShadow: '0 0 12px rgba(244,114,182,0.5)',
                }}
              />
            </div>
            <style>{`
              @keyframes shimmer {
                0% { background-position: 200% 0; }
                100% { background-position: -200% 0; }
              }
            `}</style>
          </div>
        )}
      </Card>

      {/* AI Analysis */}
      {mode === 'natural' && aiAnalysis && (
        <Card className="p-6 relative overflow-hidden border-l-4 border-l-pink-400">
          <div className="flex items-center gap-2 mb-3">
            <Icon icon={Sparkles} size={18} className="text-pink-500" />
            <h3 className="font-medium">AI Analysis</h3>
          </div>
          <div className="space-y-2 text-sm">
            <p>
              <span className="font-medium">Looking for:</span>{' '}
              <span className={`px-2 py-0.5 rounded ${citationTypeInfo[aiAnalysis.citation_type_needed]?.color || 'bg-gray-500'} text-white`}>
                {aiAnalysis.citation_type_needed}
              </span>{' '}
              paper about <strong>{aiAnalysis.topic}</strong>
            </p>
            <p className="text-muted-foreground">{aiAnalysis.reasoning}</p>
            {aiAnalysis.keywords.length > 0 && (
              <div className="flex items-center gap-2 mt-2 flex-wrap">
                <span className="text-muted-foreground">Keywords:</span>
                {aiAnalysis.keywords.map((kw: string) => (
                  <Badge key={kw} variant="outline">{kw}</Badge>
                ))}
              </div>
            )}
          </div>
        </Card>
      )}

      {/* Results */}
      {displayedResults.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-medium">
              Results ({totalAvailable > allResults.length ? `${allResults.length}+` : allResults.length} papers)
            </h3>
          </div>

          {displayedResults.map((paper, index) => {
            const isInLibrary = paper.in_library || addedToLibrary.has(paper.bibcode)
            const isExpanded = expandedResults.has(paper.bibcode)
            const showRelevance = mode === 'natural' && paper.relevance_score != null

            return (
              <Card key={`${paper.bibcode}-${index}`} className="overflow-hidden">
                <div className="p-4">
                  {/* Header row */}
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start gap-3">
                        <span className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-sm font-medium">
                          {index + 1}
                        </span>
                        <div className="flex-1 min-w-0">
                          <button
                            onClick={() => isInLibrary ? handlePaperClick(paper) : toggleExpanded(paper.bibcode)}
                            className={`text-left w-full group ${isInLibrary ? 'cursor-pointer' : ''}`}
                            title={isInLibrary ? 'View paper details' : undefined}
                          >
                            <h4 className="font-medium group-hover:text-primary transition-colors line-clamp-2">
                              {paper.title}
                            </h4>
                          </button>
                          <div className="flex items-center gap-2 mt-1 text-sm text-muted-foreground flex-wrap">
                            <span>{paper.first_author}{paper.year ? ` et al. (${paper.year})` : ''}</span>
                            {paper.citation_count != null && (
                              <>
                                <span>·</span>
                                <span>{paper.citation_count.toLocaleString()} citations</span>
                              </>
                            )}
                            {paper.journal && (
                              <>
                                <span>·</span>
                                <span>{paper.journal}</span>
                              </>
                            )}
                            {isInLibrary && (
                              <>
                                <span>·</span>
                                <span className="flex items-center gap-1 text-green-600 dark:text-green-400">
                                  <Icon icon={Library} size={12} />
                                  In Library
                                </span>
                              </>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Relevance Score (natural mode only) */}
                    {showRelevance && (
                      <div className="flex-shrink-0 text-right">
                        <div className={`text-lg font-semibold ${getRelevanceColor(paper.relevance_score!)}`}>
                          {Math.round(paper.relevance_score! * 100)}%
                        </div>
                        {paper.citation_type && (
                          <Badge
                            className={`${citationTypeInfo[paper.citation_type]?.color || 'bg-gray-500'} text-white`}
                          >
                            {paper.citation_type}
                          </Badge>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Relevance explanation */}
                  {showRelevance && paper.relevance_explanation && (
                    <div className="mt-3 p-3 bg-secondary/50 rounded text-sm">
                      <span className="font-medium">Why this paper: </span>
                      {paper.relevance_explanation}
                    </div>
                  )}

                  {/* Expanded content */}
                  {isExpanded && (
                    <div className="mt-4 pt-4 border-t">
                      {paper.abstract && (
                        <div className="mb-4">
                          <h5 className="text-sm font-medium mb-2">Abstract</h5>
                          <p className="text-sm text-muted-foreground">{paper.abstract}</p>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Actions */}
                  <div className="flex items-center justify-between mt-4 pt-4 border-t">
                    <div className="flex items-center gap-1 flex-wrap">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => toggleExpanded(paper.bibcode)}
                      >
                        <Icon icon={isExpanded ? ChevronUp : ChevronDown} size={14} />
                        {isExpanded ? 'Less' : 'More'}
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => api.openUrl(`https://ui.adsabs.harvard.edu/abs/${paper.bibcode}/abstract`)}
                      >
                        <Icon icon={ExternalLink} size={14} />
                        ADS
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => copyBibcode(paper)}
                      >
                        <Icon icon={copiedState?.bibcode === paper.bibcode && copiedState?.type === 'bibcode' ? Check : Copy} size={14} />
                        {copiedState?.bibcode === paper.bibcode && copiedState?.type === 'bibcode' ? 'Copied!' : 'Bibcode'}
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
                      {isInLibrary ? (
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
            )
          })}

          {/* Scroll sentinel / loading more */}
          <div ref={sentinelRef} className="py-4 flex justify-center">
            {isFetchingNextPage && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Icon icon={Loader2} size={16} className="animate-spin" />
                Loading more results...
              </div>
            )}
            {!hasNextPage && visibleCount >= allResults.length && allResults.length > 0 && (
              <p className="text-sm text-muted-foreground">No more results</p>
            )}
          </div>
        </div>
      )}

      {/* Empty state */}
      {!isSearching && !displayedResults.length && searchParams && (
        <Card className="p-6">
          <div className="text-center py-12 text-muted-foreground">
            <Icon icon={Search} size={48} className="mx-auto mb-4 opacity-50" />
            <p>No papers found. Try different keywords or a broader search.</p>
          </div>
        </Card>
      )}

      {/* Initial state */}
      {!searchParams && !isSearching && (
        <Card className="p-6">
          <div className="text-center py-12 text-muted-foreground">
            <Icon icon={Search} size={48} className="mx-auto mb-4 opacity-50" />
            <p>Enter a query to search for papers</p>
          </div>
        </Card>
      )}

      {/* Error state */}
      {isError && (
        <Card className="p-6 border-red-500">
          <div className="text-center py-4 text-red-600 dark:text-red-400">
            <p>Search failed: {(error as Error)?.message || 'Unknown error'}</p>
            <Button variant="outline" className="mt-2" onClick={handleSearch}>
              Retry
            </Button>
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
              <Button onClick={handleAddToLibrary} disabled={isAddingPaper}>
                {isAddingPaper ? (
                  <Icon icon={Loader2} size={14} className="animate-spin" />
                ) : (
                  <Icon icon={Plus} size={14} />
                )}
                {isAddingPaper ? 'Adding...' : 'Add Paper'}
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}
