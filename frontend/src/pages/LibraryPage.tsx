import { useState, useCallback, useMemo } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { Plus, Download } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Icon } from '@/components/ui/Icon'
import { PaperTable } from '@/components/library/PaperTable'
import { LibraryFilters, LibraryFiltersState } from '@/components/library/LibraryFilters'
import { BulkActionsBar } from '@/components/library/BulkActionsBar'
import { usePapers } from '@/hooks/usePapers'
import { useActiveProject, usePaperSelection } from '@/store'
import { Paper } from '@/lib/api'

export function LibraryPage() {
  const navigate = useNavigate()
  const { project } = useActiveProject()
  const { count: selectedCount, selectedBibcodes } = usePaperSelection()

  const [filters, setFilters] = useState<LibraryFiltersState>({
    search: '',
    year_min: undefined,
    year_max: undefined,
    min_citations: undefined,
    has_pdf: undefined,
    pdf_embedded: undefined,
    is_my_paper: undefined,
    has_note: undefined,
  })

  const [sorting, setSorting] = useState<{ id: string; desc: boolean }[]>([
    { id: 'updated_at', desc: true },
  ])

  // Map react-table sorting to API params
  const sortState = sorting[0]
  const sortBy = sortState?.id as 'title' | 'year' | 'citation_count' | 'created_at' | 'updated_at' | undefined
  const sortOrder = sortState?.desc ? 'desc' : 'asc'

  // Memoize params to ensure we don't trigger any react-query overhead while typing search
  const queryParams = useMemo(() => ({
    project: project || undefined,
    // search: filters.search || undefined, // Disabled server-side search
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

  const { data, isLoading, error } = usePapers(queryParams)

  // Client-side filtering
  const filteredPapers = useMemo(() => {
    if (!data?.papers) return []
    if (!filters.search) return data.papers

    const query = filters.search.toLowerCase()

    const result = data.papers.filter((paper) => {
      // Search by title
      if (paper.title?.toLowerCase().includes(query)) return true

      // Search by bibcode
      if (paper.bibcode.toLowerCase().includes(query)) return true

      // Search by abstract
      if (paper.abstract?.toLowerCase().includes(query)) return true

      // Search by authors
      if (paper.authors) {
        try {
          const authorsList = Array.isArray(paper.authors) ? paper.authors : [paper.authors]
          // Join with space to match partial names
          const authorsStr = authorsList.join(' ').toLowerCase()
          if (authorsStr.includes(query)) return true
        } catch {
          // ignore error
        }
      }

      // Search by year
      if (paper.year?.toString().includes(query)) return true

      return false
    })

    return result
  }, [data?.papers, filters.search])

  const handleRowClick = useCallback((paper: Paper) => {
    navigate({ to: '/library/$bibcode', params: { bibcode: paper.bibcode } })
  }, [navigate])

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Library</h1>
          <p className="text-muted-foreground">
            {filteredPapers.length} papers
            {project && ` in ${project}`}
            {data?.total !== filteredPapers.length && ` (filtered from ${data?.total})`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => navigate({ to: '/import' })}>
            <Icon icon={Download} size={16} />
            Import
          </Button>
          <Button onClick={() => navigate({ to: '/import' })}>
            <Icon icon={Plus} size={16} />
            Add Paper
          </Button>
        </div>
      </div>

      {/* Filters */}
      <LibraryFilters filters={filters} onChange={setFilters} />

      {/* Bulk Actions Bar */}
      {selectedCount() > 0 && (
        <BulkActionsBar selectedBibcodes={Array.from(selectedBibcodes)} />
      )}

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
      {!isLoading && !error && data && (
        <PaperTable
          data={filteredPapers}
          onRowClick={handleRowClick}
          sorting={sorting}
          onSortingChange={setSorting}
        />
      )}
    </div>
  )
}
