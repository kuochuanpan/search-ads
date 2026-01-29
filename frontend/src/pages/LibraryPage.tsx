import { useState, useCallback, useMemo, useEffect, useRef } from 'react'
import { useNavigate, useSearch, useLocation } from '@tanstack/react-router'
import { Download, AlertTriangle } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Icon } from '@/components/ui/Icon'
import { PaperTable } from '@/components/library/PaperTable'
import { LibraryFilters, LibraryFiltersState } from '@/components/library/LibraryFilters'
import { BulkActionsBar } from '@/components/library/BulkActionsBar'
import { usePapers } from '@/hooks/usePapers'
import { useActiveProject, usePaperSelection } from '@/store'
import { Paper } from '@/lib/api'
import { useStats } from '@/hooks/useStats'
import { Modal } from '@/components/ui/Modal'

export function LibraryPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const searchParams = useSearch({ strict: false })
  const { project } = useActiveProject()
  const { count: selectedCount, selectedBibcodes } = usePaperSelection()
  const { data: stats } = useStats()

  // State for Cost Warning
  const [showCostWarning, setShowCostWarning] = useState(false)
  const [pendingFilters, setPendingFilters] = useState<LibraryFiltersState | null>(null)

  const [filters, setFilters] = useState<LibraryFiltersState>({
    search: (searchParams as any).search || '',
    search_mode: (searchParams as any).search_mode || 'metadata',
    year_min: (searchParams as any).year_min ? Number((searchParams as any).year_min) : undefined,
    year_max: (searchParams as any).year_max ? Number((searchParams as any).year_max) : undefined,
    min_citations: (searchParams as any).min_citations ? Number((searchParams as any).min_citations) : undefined,
    has_pdf: (searchParams as any).has_pdf ? (searchParams as any).has_pdf === 'true' || (searchParams as any).has_pdf === true : undefined,
    pdf_embedded: (searchParams as any).pdf_embedded ? (searchParams as any).pdf_embedded === 'true' || (searchParams as any).pdf_embedded === true : undefined,
    is_my_paper: (searchParams as any).is_my_paper ? (searchParams as any).is_my_paper === 'true' || (searchParams as any).is_my_paper === true : undefined,
    has_note: (searchParams as any).has_note ? (searchParams as any).has_note === 'true' || (searchParams as any).has_note === true : undefined,
  })

  // Handle filter changes with warning interception
  const handleFilterChange = (newFilters: LibraryFiltersState) => {
    // Check if switching TO pdf mode from another mode
    if (newFilters.search_mode === 'pdf' && filters.search_mode !== 'pdf') {
      setPendingFilters(newFilters)
      setShowCostWarning(true)
      return
    }
    setFilters(newFilters)
  }

  const confirmPdfSearch = () => {
    if (pendingFilters) {
      setFilters(pendingFilters)
    }
    setShowCostWarning(false)
    setPendingFilters(null)
  }

  const cancelPdfSearch = () => {
    setShowCostWarning(false)
    setPendingFilters(null)
  }

  // Update filters when search params change (e.g. navigation from sidebar or home)
  useEffect(() => {
    if (Object.keys(searchParams).length > 0) {
      setFilters(prev => ({
        ...prev,
        search: (searchParams as any).search || '',
        search_mode: (searchParams as any).search_mode || 'metadata',
        is_my_paper: (searchParams as any).is_my_paper ? ((searchParams as any).is_my_paper === 'true' || (searchParams as any).is_my_paper === true) : undefined,
        has_note: (searchParams as any).has_note ? ((searchParams as any).has_note === 'true' || (searchParams as any).has_note === true) : undefined,
      }))
    }
  }, [searchParams])

  // Sync filters to URL
  useEffect(() => {
    navigate({
      search: (prev: any) => ({
        ...prev,
        search: filters.search || undefined,
        search_mode: filters.search_mode === 'metadata' ? undefined : filters.search_mode,
        year_min: filters.year_min,
        year_max: filters.year_max,
        min_citations: filters.min_citations,
        has_pdf: filters.has_pdf,
        pdf_embedded: filters.pdf_embedded,
        is_my_paper: filters.is_my_paper,
        has_note: filters.has_note,
      }),
      replace: true,
    })
  }, [filters, navigate])

  // Sorting state
  const [sorting, setSorting] = useState<{ id: string; desc: boolean }[]>(() => {
    const sortBy = (searchParams as any).sort_by
    const sortOrder = (searchParams as any).sort_order

    if (sortBy) {
      const id = sortBy === 'created_at' ? 'added_date' : sortBy
      return [{ id, desc: sortOrder === 'desc' }]
    }
    return [{ id: 'added_date', desc: true }]
  })

  // Sync sorting to URL
  useEffect(() => {
    const sortState = sorting[0]
    if (!sortState) return

    const sortBy = sortState.id === 'added_date' ? 'created_at' : sortState.id
    const sortOrder = sortState.desc ? 'desc' : 'asc'

    if ((searchParams as any).sort_by !== sortBy || (searchParams as any).sort_order !== sortOrder) {
      navigate({
        search: (prev: any) => ({
          ...prev,
          sort_by: sortBy,
          sort_order: sortOrder,
        }),
        replace: true,
      })
    }
  }, [sorting, navigate, searchParams])

  // API Params
  const sortState = sorting[0]
  const sortBy = sortState?.id === 'added_date' ? 'created_at' : (sortState?.id as 'title' | 'year' | 'citation_count' | 'created_at' | 'updated_at' | 'journal' | undefined)
  const sortOrder = sortState?.desc ? 'desc' : 'asc'

  const queryParams = useMemo(() => ({
    project: project || undefined,
    search: filters.search || undefined,
    search_pdf: filters.search_mode === 'pdf',
    year_min: filters.year_min,
    year_max: filters.year_max,
    min_citations: filters.min_citations,
    has_pdf: filters.has_pdf,
    pdf_embedded: filters.pdf_embedded,
    is_my_paper: filters.is_my_paper,
    has_note: filters.has_note,
    sort_by: sortBy,
    sort_order: sortOrder as 'asc' | 'desc',
  }), [
    project,
    filters.search,
    filters.search_mode,
    filters.year_min,
    filters.year_max,
    filters.min_citations,
    filters.has_pdf,
    filters.pdf_embedded,
    filters.is_my_paper,
    filters.has_note,
    sortBy,
    sortOrder
  ])

  const {
    data,
    isLoading,
    error,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage
  } = usePapers(queryParams)

  const papers = useMemo(() => {
    return data?.pages?.flatMap(page => page?.papers || []) ?? []
  }, [data])

  // Infinite scroll
  const loadMoreRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasNextPage && !isFetchingNextPage) {
          fetchNextPage()
        }
      },
      { threshold: 0.1 }
    )

    if (loadMoreRef.current) {
      observer.observe(loadMoreRef.current)
    }

    return () => observer.disconnect()
  }, [hasNextPage, isFetchingNextPage, fetchNextPage])

  // Scroll restore
  const hasRestoredScroll = useRef(false)

  useEffect(() => {
    if ((location.state as any)?.resetScroll) {
      sessionStorage.removeItem('library_scroll_y')
      return
    }

    if (!isLoading && papers.length > 0 && !hasRestoredScroll.current) {
      const savedScroll = sessionStorage.getItem('library_scroll_y')
      if (savedScroll) {
        setTimeout(() => {
          window.scrollTo(0, parseInt(savedScroll))
          hasRestoredScroll.current = true
        }, 0)
      } else {
        hasRestoredScroll.current = true
      }
    }
  }, [isLoading, papers.length, location.state])

  const handleRowClick = useCallback((paper: Paper) => {
    sessionStorage.setItem('library_scroll_y', window.scrollY.toString())
    navigate({
      to: '/library/$bibcode',
      params: { bibcode: paper.bibcode },
      state: { from: 'library' } as any
    })
  }, [navigate])

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Library</h1>
          <p className="text-muted-foreground">
            {papers.length} papers
            {project && ` in ${project}`}
            {data?.pages?.[0]?.total !== undefined && ` (filtered from ${data.pages[0].total})`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => navigate({ to: '/import' })}>
            <Icon icon={Download} size={16} />
            Import
          </Button>
        </div>
      </div>

      {/* Filters */}
      <LibraryFilters
        filters={filters}
        onChange={handleFilterChange}
        minYear={stats?.min_year}
        maxYear={stats?.max_year}
      />

      {/* Bulk Actions Bar */}
      {selectedCount() > 0 && (
        <BulkActionsBar selectedBibcodes={Array.from(selectedBibcodes)} />
      )}

      {/* Cost Warning Modal */}
      <Modal
        isOpen={showCostWarning}
        onClose={cancelPdfSearch}
        title="PDF Full-Text Search Warning"
      >
        <div className="space-y-4">
          <div className="p-4 bg-yellow-100 text-yellow-800 rounded-md text-sm">
            <p className="font-semibold flex items-center gap-2">
              <Icon icon={AlertTriangle} size={16} />
              Potential High Resource Usage
            </p>
            <p className="mt-2 text-yellow-800/90">
              Searching through full PDF text requires embedding your query and comparing it against all embedded PDF chunks.
            </p>
            <p className="mt-1 text-yellow-800/90">
              Depending on the number of embedded papers, this operation might be slower and consume more resources/tokens compared to metadata search.
            </p>
          </div>

          <p className="text-sm text-muted-foreground">
            Are you sure you want to enable PDF Full-Text search mode?
          </p>

          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={cancelPdfSearch}>
              Cancel
            </Button>
            <Button onClick={confirmPdfSearch}>
              Enable PDF Search
            </Button>
          </div>
        </div>
      </Modal>

      {/* Loading / Error States */}
      {isLoading && (
        <div className="py-8 text-center text-muted-foreground">
          Loading papers...
        </div>
      )}

      {error && (
        <div className="py-8 text-center text-destructive">
          Error loading papers: {error.message}
        </div>
      )}

      {/* Table */}
      {!isLoading && !error && (
        <>
          <PaperTable
            data={papers}
            onRowClick={handleRowClick}
            sorting={sorting}
            onSortingChange={setSorting}
          />
          {/* Load More Trigger */}
          <div ref={loadMoreRef} className="h-4 w-full flex items-center justify-center p-4">
            {isFetchingNextPage && <div className="text-muted-foreground text-sm">Loading more...</div>}
          </div>
        </>
      )}
    </div>
  )
}
