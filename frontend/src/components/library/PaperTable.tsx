import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  useReactTable,
  SortingState,
  getSortedRowModel,
} from '@tanstack/react-table'
import { useState, useRef, useEffect } from 'react'
import { useNavigate } from '@tanstack/react-router'
import {
  ArrowUpDown,
  MoreHorizontal,
  Check,
  Download,
  Star,
  FileText,
  File,
  Eye,
  BookOpen,
  Quote,
  Copy,
  Trash2,
  Network,
} from 'lucide-react'
import { Paper, api } from '@/lib/api'
import { formatAuthorList, cn } from '@/lib/utils'
import { Icon } from '@/components/ui/Icon'
import { usePaperSelection } from '@/store'
import { useToggleMyPaper, useDeletePaper, useDownloadPdf, useOpenPdf, useEmbedPdf } from '@/hooks/usePapers'
import { useNote } from '@/hooks/useNotes'
import { Loader2 } from 'lucide-react'

interface PaperTableProps {
  data: Paper[]
  onRowClick?: (paper: Paper) => void
}

interface ContextMenuState {
  isOpen: boolean
  x: number
  y: number
  paper: Paper | null
}

function CitationSort({ sorted }: { sorted: boolean | undefined }) {
  return <ArrowUpDown size={14} className={cn(sorted && 'text-foreground')} />
}

// Note preview tooltip component
function NotePreview({ bibcode }: { bibcode: string }) {
  const [isHovered, setIsHovered] = useState(false)
  const { data: note, isLoading } = useNote(bibcode)

  return (
    <div
      className="relative inline-block"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <Icon icon={FileText} size={16} className="text-primary cursor-pointer" />
      {isHovered && (
        <div className="absolute z-50 left-full ml-2 top-1/2 -translate-y-1/2 w-64 max-h-48 overflow-auto bg-popover border rounded-lg shadow-lg p-3 text-sm">
          {isLoading ? (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Loader2 size={14} className="animate-spin" />
              Loading...
            </div>
          ) : note?.content ? (
            <div className="whitespace-pre-wrap">{note.content}</div>
          ) : (
            <div className="text-muted-foreground italic">No note content</div>
          )}
        </div>
      )}
    </div>
  )
}

export function PaperTable({ data, onRowClick }: PaperTableProps) {
  const navigate = useNavigate()
  const { isSelected, toggleSelection, selectAll, deselectAll } = usePaperSelection()
  const toggleMyPaper = useToggleMyPaper()
  const deletePaper = useDeletePaper()
  const downloadPdf = useDownloadPdf()
  const openPdf = useOpenPdf()
  const embedPdf = useEmbedPdf()

  const [sorting, setSorting] = useState<SortingState>([
    { id: 'updated_at', desc: true },
  ])

  const [contextMenu, setContextMenu] = useState<ContextMenuState>({
    isOpen: false,
    x: 0,
    y: 0,
    paper: null,
  })

  const menuRef = useRef<HTMLDivElement>(null)

  const [menuPosition, setMenuPosition] = useState({ x: 0, y: 0 })

  // Close context menu on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setContextMenu({ ...contextMenu, isOpen: false })
      }
    }

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setContextMenu({ ...contextMenu, isOpen: false })
    }

    if (contextMenu.isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
      document.addEventListener('keydown', handleEscape)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleEscape)
    }
  }, [contextMenu.isOpen])

  // Adjust menu position to stay within viewport
  useEffect(() => {
    if (contextMenu.isOpen && menuRef.current) {
      const menu = menuRef.current
      const rect = menu.getBoundingClientRect()
      const viewportWidth = window.innerWidth
      const viewportHeight = window.innerHeight

      let newX = contextMenu.x
      let newY = contextMenu.y

      // Adjust horizontal position if menu goes off right edge
      if (newX + rect.width > viewportWidth) {
        newX = viewportWidth - rect.width - 10
      }
      // Ensure menu doesn't go off left edge
      if (newX < 10) {
        newX = 10
      }

      // Adjust vertical position if menu goes off bottom edge
      if (newY + rect.height > viewportHeight) {
        newY = viewportHeight - rect.height - 10
      }
      // Ensure menu doesn't go off top edge
      if (newY < 10) {
        newY = 10
      }

      setMenuPosition({ x: newX, y: newY })
    }
  }, [contextMenu.isOpen, contextMenu.x, contextMenu.y])

  const handleContextMenu = (e: React.MouseEvent, paper: Paper) => {
    e.preventDefault()
    e.stopPropagation()
    const x = e.clientX
    const y = e.clientY
    setMenuPosition({ x, y })
    setContextMenu({
      isOpen: true,
      x,
      y,
      paper,
    })
  }

  const closeContextMenu = () => {
    setContextMenu({ ...contextMenu, isOpen: false })
  }

  const handleContextAction = async (action: string) => {
    const paper = contextMenu.paper
    if (!paper) return

    closeContextMenu()

    switch (action) {
      case 'view':
        navigate({ to: '/library/$bibcode', params: { bibcode: paper.bibcode } })
        break
      case 'graph':
        navigate({ to: '/graph/$bibcode', params: { bibcode: paper.bibcode } })
        break
      case 'toggle_mine':
        toggleMyPaper.mutate({ bibcode: paper.bibcode, isMyPaper: !paper.is_my_paper })
        break
      case 'download_pdf':
        await api.downloadPdf(paper.bibcode)
        break
      case 'open_pdf':
        await api.openPdf(paper.bibcode)
        break
      case 'embed_pdf':
        await api.embedPdf(paper.bibcode)
        break
      case 'copy_bibtex':
        if (paper.bibtex) {
          await navigator.clipboard.writeText(paper.bibtex)
        }
        break
      case 'copy_citekey':
        await navigator.clipboard.writeText(paper.bibcode)
        break
      case 'delete':
        if (confirm('Are you sure you want to delete this paper?')) {
          await deletePaper.mutateAsync(paper.bibcode)
        }
        break
    }
  }

  const columns: ColumnDef<Paper>[] = [
    {
      id: 'select',
      header: () => (
        <input
          type="checkbox"
          checked={data.length > 0 && data.every(p => isSelected(p.bibcode))}
          onChange={(e) => {
            if (e.target.checked) {
              selectAll(data.map(p => p.bibcode))
            } else {
              deselectAll()
            }
          }}
          className="h-4 w-4 rounded border border-input"
        />
      ),
      cell: ({ row }) => (
        <input
          type="checkbox"
          checked={isSelected(row.original.bibcode)}
          onChange={() => toggleSelection(row.original.bibcode)}
          className="h-4 w-4 rounded border border-input"
        />
      ),
      size: 40,
    },
    {
      accessorKey: 'title',
      header: ({ column }) => (
        <button
          onClick={column.getToggleSortingHandler()}
          className="flex items-center gap-1"
        >
          Title <CitationSort sorted={column.getIsSorted() === 'asc' || column.getIsSorted() === 'desc'} />
        </button>
      ),
      cell: (info) => (
        <div className="max-w-md truncate" title={info.getValue<string>()}>
          {info.getValue<string>()}
        </div>
      ),
      size: 400,
    },
    {
      accessorKey: 'year',
      header: ({ column }) => (
        <button
          onClick={column.getToggleSortingHandler()}
          className="flex items-center gap-1"
        >
          Year <CitationSort sorted={column.getIsSorted() === 'asc' || column.getIsSorted() === 'desc'} />
        </button>
      ),
      cell: (info) => info.getValue<number>() ?? '-',
      size: 60,
    },
    {
      accessorKey: 'authors',
      header: ({ column }) => (
        <button
          onClick={column.getToggleSortingHandler()}
          className="flex items-center gap-1"
        >
          Authors <CitationSort sorted={column.getIsSorted() === 'asc' || column.getIsSorted() === 'desc'} />
        </button>
      ),
      cell: (info) => {
        const authors = info.getValue<string[]>()
        return formatAuthorList(authors)
      },
      size: 150,
    },
    {
      accessorKey: 'citation_count',
      header: ({ column }) => (
        <button
          onClick={column.getToggleSortingHandler()}
          className="flex items-center gap-1"
        >
          Cited <CitationSort sorted={column.getIsSorted() === 'asc' || column.getIsSorted() === 'desc'} />
        </button>
      ),
      cell: (info) => info.getValue<number>() ?? '-',
      size: 60,
    },
    {
      id: 'is_my_paper',
      header: 'Mine',
      cell: (info) => {
        const paper = info.row.original
        const isMyPaper = paper.is_my_paper
        return (
          <button
            onClick={(e) => {
              e.stopPropagation()
              toggleMyPaper.mutate({ bibcode: paper.bibcode, isMyPaper: !isMyPaper })
            }}
            className="hover:scale-110 transition-transform"
            title={isMyPaper ? 'Unmark as my paper' : 'Mark as my paper'}
          >
            <Icon
              icon={Star}
              size={16}
              className={cn(
                'transition-colors',
                isMyPaper ? 'text-yellow-500 fill-yellow-500' : 'text-muted-foreground hover:text-yellow-500'
              )}
            />
          </button>
        )
      },
      size: 40,
    },
    {
      id: 'has_note',
      header: 'Note',
      cell: (info) => {
        const paper = info.row.original
        if (!paper.has_note) return <span className="text-muted-foreground">-</span>
        return <NotePreview bibcode={paper.bibcode} />
      },
      size: 40,
    },
    {
      id: 'pdf_status',
      header: 'PDF',
      cell: (info) => {
        const paper = info.row.original
        const { pdf_path, pdf_url } = paper

        if (pdf_path) {
          // Has local PDF - click to open
          return (
            <button
              onClick={(e) => {
                e.stopPropagation()
                openPdf.mutate(paper.bibcode)
              }}
              className="hover:scale-110 transition-transform"
              title="Open PDF"
            >
              <Icon icon={Check} size={16} className="text-green-500 hover:text-green-600" />
            </button>
          )
        } else if (pdf_url) {
          // Has URL but not downloaded - click to download
          return (
            <button
              onClick={(e) => {
                e.stopPropagation()
                downloadPdf.mutate(paper.bibcode)
              }}
              className="hover:scale-110 transition-transform"
              title="Download PDF"
              disabled={downloadPdf.isPending}
            >
              {downloadPdf.isPending ? (
                <Loader2 size={16} className="animate-spin text-muted-foreground" />
              ) : (
                <Icon icon={Download} size={16} className="text-muted-foreground hover:text-primary" />
              )}
            </button>
          )
        }
        // No PDF available
        return (
          <span title="No PDF available">
            <Icon icon={File} size={16} className="text-muted-foreground opacity-50" />
          </span>
        )
      },
      size: 40,
    },
    {
      id: 'embedded',
      header: 'Embed',
      cell: (info) => {
        const paper = info.row.original
        const { pdf_embedded, pdf_path } = paper

        if (pdf_embedded) {
          return (
            <span title="PDF embedded">
              <Icon icon={Check} size={16} className="text-green-500" />
            </span>
          )
        }

        if (pdf_path) {
          // Has PDF but not embedded - click to embed
          return (
            <button
              onClick={(e) => {
                e.stopPropagation()
                embedPdf.mutate(paper.bibcode)
              }}
              className="hover:scale-110 transition-transform"
              title="Embed PDF for search"
              disabled={embedPdf.isPending}
            >
              {embedPdf.isPending ? (
                <Loader2 size={16} className="animate-spin text-muted-foreground" />
              ) : (
                <Icon icon={BookOpen} size={16} className="text-muted-foreground hover:text-primary" />
              )}
            </button>
          )
        }

        // No PDF to embed
        return <span className="text-muted-foreground">-</span>
      },
      size: 40,
    },
    {
      id: 'actions',
      header: '',
      cell: ({ row }) => (
        <button
          className="p-1 hover:bg-secondary rounded"
          onClick={(e) => handleContextMenu(e, row.original)}
        >
          <MoreHorizontal size={16} />
        </button>
      ),
      size: 40,
    },
  ]

  const [columnSizing, setColumnSizing] = useState({})

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    state: { sorting, columnSizing },
    onSortingChange: setSorting,
    onColumnSizingChange: setColumnSizing,
    columnResizeMode: 'onChange',
    enableColumnResizing: true,
  })

  return (
    <div className="border rounded-lg overflow-hidden">
      <table className="w-full">
        <thead className="bg-secondary/50">
          {table.getHeaderGroups().map((headerGroup) => (
            <tr key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <th
                  key={header.id}
                  className="px-3 py-2 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider relative group"
                  style={{ width: header.getSize() }}
                >
                  {header.isPlaceholder
                    ? null
                    : flexRender(header.column.columnDef.header, header.getContext())}
                  {header.column.getCanResize() && (
                    <div
                      onMouseDown={header.getResizeHandler()}
                      onTouchStart={header.getResizeHandler()}
                      className={cn(
                        'absolute right-0 top-0 h-full w-1 cursor-col-resize select-none touch-none',
                        'opacity-0 group-hover:opacity-100 hover:bg-primary/50 transition-opacity',
                        header.column.getIsResizing() && 'bg-primary opacity-100'
                      )}
                    />
                  )}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody className="divide-y">
          {table.getRowModel().rows.map((row) => (
            <tr
              key={row.id}
              className={cn(
                'hover:bg-secondary/50 transition-colors cursor-pointer',
                isSelected(row.original.bibcode) && 'bg-secondary/70'
              )}
              onClick={() => onRowClick?.(row.original)}
              onContextMenu={(e) => handleContextMenu(e, row.original)}
            >
              {row.getVisibleCells().map((cell) => (
                <td
                  key={cell.id}
                  className="px-3 py-2 text-sm"
                  onClick={(e) => {
                    // Don't trigger row click when clicking checkbox or actions
                    if (cell.column.id === 'select' || cell.column.id === 'actions') {
                      e.stopPropagation()
                    }
                  }}
                >
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {data.length === 0 && (
        <div className="p-8 text-center text-muted-foreground">
          No papers found. Try adjusting your filters or import some papers.
        </div>
      )}

      {/* Context Menu */}
      {contextMenu.isOpen && contextMenu.paper && (
        <div
          ref={menuRef}
          className="fixed z-50 min-w-[200px] bg-card border rounded-lg shadow-lg py-1"
          style={{ left: menuPosition.x, top: menuPosition.y }}
        >
          <button
            onClick={() => handleContextAction('view')}
            className="w-full flex items-center gap-2 px-3 py-1.5 text-sm text-left hover:bg-secondary"
          >
            <Icon icon={Eye} size={16} />
            View Paper Details
          </button>

          <div className="my-1 border-t" />

          <button
            onClick={() => handleContextAction('graph')}
            className="w-full flex items-center gap-2 px-3 py-1.5 text-sm text-left hover:bg-secondary"
          >
            <Icon icon={Network} size={16} />
            View in Graph
          </button>

          <div className="my-1 border-t" />

          <button
            onClick={() => handleContextAction('toggle_mine')}
            className="w-full flex items-center gap-2 px-3 py-1.5 text-sm text-left hover:bg-secondary"
          >
            <Icon icon={Star} size={16} className={contextMenu.paper.is_my_paper ? 'text-yellow-500' : ''} />
            {contextMenu.paper.is_my_paper ? 'Unmark as My Paper' : 'Mark as My Paper'}
          </button>

          <div className="my-1 border-t" />

          {contextMenu.paper.pdf_path ? (
            <button
              onClick={() => handleContextAction('open_pdf')}
              className="w-full flex items-center gap-2 px-3 py-1.5 text-sm text-left hover:bg-secondary"
            >
              <Icon icon={FileText} size={16} />
              Open PDF
            </button>
          ) : contextMenu.paper.pdf_url ? (
            <button
              onClick={() => handleContextAction('download_pdf')}
              className="w-full flex items-center gap-2 px-3 py-1.5 text-sm text-left hover:bg-secondary"
            >
              <Icon icon={Download} size={16} />
              Download PDF
            </button>
          ) : null}

          {contextMenu.paper.pdf_path && !contextMenu.paper.pdf_embedded && (
            <button
              onClick={() => handleContextAction('embed_pdf')}
              className="w-full flex items-center gap-2 px-3 py-1.5 text-sm text-left hover:bg-secondary"
            >
              <Icon icon={BookOpen} size={16} />
              Embed PDF
            </button>
          )}

          <div className="my-1 border-t" />

          <button
            onClick={() => handleContextAction('copy_bibtex')}
            disabled={!contextMenu.paper.bibtex}
            className="w-full flex items-center gap-2 px-3 py-1.5 text-sm text-left hover:bg-secondary disabled:opacity-50"
          >
            <Icon icon={Copy} size={16} />
            Copy BibTeX
          </button>

          <button
            onClick={() => handleContextAction('copy_citekey')}
            className="w-full flex items-center gap-2 px-3 py-1.5 text-sm text-left hover:bg-secondary"
          >
            <Icon icon={Quote} size={16} />
            Copy Cite Key
          </button>

          <div className="my-1 border-t" />

          <button
            onClick={() => handleContextAction('delete')}
            className="w-full flex items-center gap-2 px-3 py-1.5 text-sm text-left hover:bg-secondary text-destructive"
          >
            <Icon icon={Trash2} size={16} />
            Remove from Library
          </button>
        </div>
      )}
    </div>
  )
}
