import { useState, useCallback } from 'react'
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

  // TODO: Add sort controls to the UI
  const sortBy = 'updated_at' as const
  const sortOrder = 'desc' as const

  const { data, isLoading, error } = usePapers({
    project: project || undefined,
    search: filters.search || undefined,
    year_min: filters.year_min,
    year_max: filters.year_max,
    min_citations: filters.min_citations,
    has_pdf: filters.has_pdf,
    pdf_embedded: filters.pdf_embedded,
    is_my_paper: filters.is_my_paper,
    has_note: filters.has_note,
    sort_by: sortBy,
    sort_order: sortOrder,
  })

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
              {data?.total || 0} papers
              {project && ` in ${project}`}
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
          <PaperTable data={data.papers} onRowClick={handleRowClick} />
        )}
    </div>
  )
}
