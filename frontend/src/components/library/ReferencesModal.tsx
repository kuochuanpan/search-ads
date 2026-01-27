import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Loader2, Check, Plus, ChevronLeft, ChevronRight, BookOpen, Quote } from 'lucide-react'
import { Modal } from '@/components/ui/Modal'
import { Button } from '@/components/ui/Button'
import { Icon } from '@/components/ui/Icon'
import { api, PaperSummary } from '@/lib/api'
import { formatAuthorList, cn } from '@/lib/utils'

interface ReferencesModalProps {
  isOpen: boolean
  onClose: () => void
  bibcode: string
  title?: string
  type: 'references' | 'citations'
}

function PaperRow({
  paper,
  onAdd,
  isAdding,
}: {
  paper: PaperSummary
  onAdd: (bibcode: string) => void
  isAdding: boolean
}) {
  // Parse authors if it's a JSON string
  let authorDisplay = ''
  if (paper.authors) {
    try {
      const authorList = JSON.parse(paper.authors)
      authorDisplay = formatAuthorList(authorList)
    } catch {
      authorDisplay = paper.authors
    }
  }

  return (
    <div className="flex items-center justify-between py-3 px-4 hover:bg-secondary/50 transition-colors border-b last:border-b-0">
      <div className="flex-1 min-w-0 mr-4">
        <div className="font-medium text-sm truncate" title={paper.title || paper.bibcode}>
          {paper.title || paper.bibcode}
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground mt-1">
          {paper.year && <span>{paper.year}</span>}
          {authorDisplay && (
            <>
              <span className="text-muted-foreground/50">|</span>
              <span className="truncate max-w-[200px]">{authorDisplay}</span>
            </>
          )}
          {paper.journal && (
            <>
              <span className="text-muted-foreground/50">|</span>
              <span className="truncate max-w-[100px]">{paper.journal}</span>
            </>
          )}
          {paper.citation_count !== undefined && paper.citation_count > 0 && (
            <>
              <span className="text-muted-foreground/50">|</span>
              <span>{paper.citation_count} cit.</span>
            </>
          )}
        </div>
      </div>
      <div className="flex-shrink-0">
        {paper.in_library ? (
          <span className="flex items-center gap-1 text-xs text-green-500">
            <Icon icon={Check} size={14} />
            In library
          </span>
        ) : (
          <Button
            size="sm"
            variant="outline"
            onClick={() => onAdd(paper.bibcode)}
            disabled={isAdding}
          >
            {isAdding ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <>
                <Icon icon={Plus} size={14} />
                Add
              </>
            )}
          </Button>
        )}
      </div>
    </div>
  )
}

export function ReferencesModal({
  isOpen,
  onClose,
  bibcode,
  title,
  type,
}: ReferencesModalProps) {
  const [page, setPage] = useState(1)
  const [addingBibcode, setAddingBibcode] = useState<string | null>(null)
  const queryClient = useQueryClient()

  const isReferences = type === 'references'
  const modalTitle = isReferences ? 'References' : 'Citations'
  const description = isReferences
    ? 'Papers cited by this paper'
    : 'Papers that cite this paper'

  const { data, isLoading, error } = useQuery({
    queryKey: ['paper-references', bibcode, type, page],
    queryFn: () =>
      isReferences
        ? api.getReferences(bibcode, { fetch_from_ads: true, limit: 50, page })
        : api.getCitations(bibcode, { fetch_from_ads: true, limit: 50, page }),
    enabled: isOpen,
  })

  const addToLibrary = useMutation({
    mutationFn: (targetBibcode: string) =>
      api.importFromAds(targetBibcode),
    onMutate: (targetBibcode) => {
      setAddingBibcode(targetBibcode)
    },
    onSuccess: () => {
      // Invalidate queries to refresh data
      queryClient.invalidateQueries({ queryKey: ['paper-references', bibcode, type] })
      queryClient.invalidateQueries({ queryKey: ['papers'] })
    },
    onSettled: () => {
      setAddingBibcode(null)
    },
  })

  const papers = isReferences
    ? (data as any)?.references || []
    : (data as any)?.citations || []

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={modalTitle} size="lg">
      <div className="space-y-4">
        {/* Header info */}
        <div className="pb-4 border-b">
          <div className="flex items-center gap-2 text-muted-foreground text-sm mb-1">
            <Icon icon={isReferences ? BookOpen : Quote} size={16} />
            {description}
          </div>
          {title && (
            <p className="text-sm font-medium truncate" title={title}>
              {title}
            </p>
          )}
        </div>

        {/* Loading state */}
        {isLoading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 size={24} className="animate-spin text-muted-foreground" />
            <span className="ml-2 text-muted-foreground">
              Fetching {type} from ADS...
            </span>
          </div>
        )}

        {/* Error state */}
        {error && (
          <div className="py-8 text-center text-destructive">
            Error loading {type}: {(error as Error).message}
          </div>
        )}

        {/* Results */}
        {!isLoading && !error && (
          <>
            {papers.length === 0 ? (
              <div className="py-8 text-center text-muted-foreground">
                No {type} found
              </div>
            ) : (
              <>
                {/* Count */}
                <div className="text-sm text-muted-foreground">
                  Showing {papers.length} {type}
                  {data?.total && ` of ${data.total}`}
                </div>

                {/* Paper list */}
                <div className="border rounded-lg max-h-[400px] overflow-y-auto">
                  {papers.map((paper: PaperSummary) => (
                    <PaperRow
                      key={paper.bibcode}
                      paper={paper}
                      onAdd={(b) => addToLibrary.mutate(b)}
                      isAdding={addingBibcode === paper.bibcode}
                    />
                  ))}
                </div>

                {/* Pagination */}
                {(data?.has_more || page > 1) && (
                  <div className="flex items-center justify-between pt-4 border-t">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((p) => p - 1)}
                      disabled={page === 1}
                    >
                      <Icon icon={ChevronLeft} size={14} />
                      Previous
                    </Button>
                    <span className="text-sm text-muted-foreground">
                      Page {page}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((p) => p + 1)}
                      disabled={!data?.has_more}
                    >
                      Next
                      <Icon icon={ChevronRight} size={14} />
                    </Button>
                  </div>
                )}
              </>
            )}
          </>
        )}
      </div>
    </Modal>
  )
}
