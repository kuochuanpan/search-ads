import { useState } from 'react'
import { Search, Filter, X } from 'lucide-react'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { Select } from '@/components/ui/Select'
import { Icon } from '@/components/ui/Icon'

export interface LibraryFiltersState {
  search: string
  year_min: number | undefined
  year_max: number | undefined
  min_citations: number | undefined
  has_pdf: boolean | undefined
  pdf_embedded: boolean | undefined
  is_my_paper: boolean | undefined
  has_note: boolean | undefined
}

interface LibraryFiltersProps {
  filters: LibraryFiltersState
  onChange: (filters: LibraryFiltersState) => void
}

export function LibraryFilters({ filters, onChange }: LibraryFiltersProps) {
  const [showAdvanced, setShowAdvanced] = useState(false)

  const updateFilter = <K extends keyof LibraryFiltersState>(
    key: K,
    value: LibraryFiltersState[K]
  ) => {
    onChange({ ...filters, [key]: value })
  }

  const clearFilters = () => {
    onChange({
      search: '',
      year_min: undefined,
      year_max: undefined,
      min_citations: undefined,
      has_pdf: undefined,
      pdf_embedded: undefined,
      is_my_paper: undefined,
      has_note: undefined,
    })
  }

  const hasActiveFilters =
    filters.search ||
    filters.year_min ||
    filters.year_max ||
    filters.min_citations ||
    filters.has_pdf !== undefined ||
    filters.pdf_embedded !== undefined ||
    filters.is_my_paper !== undefined ||
    filters.has_note !== undefined

  return (
    <div className="space-y-3">
      {/* Search and basic filters */}
      <div className="flex gap-2 items-center">
        <div className="relative flex-1 min-w-[200px]">
          <Icon icon={Search} size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none" />
          <Input
            placeholder="Search papers..."
            value={filters.search}
            onChange={(e) => updateFilter('search', e.target.value)}
            className="pl-9"
          />
        </div>

        <Select
          value={filters.year_min?.toString() || ''}
          onChange={(e) => updateFilter('year_min', e.target.value ? parseInt(e.target.value) : undefined)}
        >
          <option value="">Year From</option>
          {Array.from({ length: 30 }, (_, i) => new Date().getFullYear() - i).map((year) => (
            <option key={year} value={year}>
              {year}
            </option>
          ))}
        </Select>

        <Select
          value={filters.year_max?.toString() || ''}
          onChange={(e) => updateFilter('year_max', e.target.value ? parseInt(e.target.value) : undefined)}
        >
          <option value="">Year To</option>
          {Array.from({ length: 30 }, (_, i) => new Date().getFullYear() - i + 30).map((year) => (
            <option key={year} value={year}>
              {year}
            </option>
          ))}
        </Select>

        <Button
          variant="outline"
          size="md"
          onClick={() => setShowAdvanced(!showAdvanced)}
          className={hasActiveFilters ? 'border-primary' : ''}
        >
          <Icon icon={Filter} size={16} />
        </Button>
      </div>

      {/* Advanced filters */}
      {showAdvanced && (
        <div className="flex gap-2 items-center flex-wrap">
          <Select
            value={filters.is_my_paper === true ? 'true' : filters.is_my_paper === false ? 'false' : ''}
            onChange={(e) =>
              updateFilter(
                'is_my_paper',
                e.target.value === 'true' ? true : e.target.value === 'false' ? false : undefined
              )
            }
          >
            <option value="">My Papers</option>
            <option value="true">Only My Papers</option>
            <option value="false">Exclude My Papers</option>
          </Select>

          <Select
            value={filters.has_pdf === true ? 'true' : filters.has_pdf === false ? 'false' : ''}
            onChange={(e) =>
              updateFilter(
                'has_pdf',
                e.target.value === 'true' ? true : e.target.value === 'false' ? false : undefined
              )
            }
          >
            <option value="">PDF Status</option>
            <option value="true">Has PDF</option>
            <option value="false">No PDF</option>
          </Select>

          <Select
            value={filters.pdf_embedded === true ? 'true' : filters.pdf_embedded === false ? 'false' : ''}
            onChange={(e) =>
              updateFilter(
                'pdf_embedded',
                e.target.value === 'true' ? true : e.target.value === 'false' ? false : undefined
              )
            }
          >
            <option value="">Embedded</option>
            <option value="true">Embedded</option>
            <option value="false">Not Embedded</option>
          </Select>

          <Select
            value={filters.has_note === true ? 'true' : filters.has_note === false ? 'false' : ''}
            onChange={(e) =>
              updateFilter(
                'has_note',
                e.target.value === 'true' ? true : e.target.value === 'false' ? false : undefined
              )
            }
          >
            <option value="">Notes</option>
            <option value="true">Has Note</option>
            <option value="false">No Note</option>
          </Select>

          <Input
            type="number"
            placeholder="Min Citations"
            value={filters.min_citations || ''}
            onChange={(e) => updateFilter('min_citations', e.target.value ? parseInt(e.target.value) : undefined)}
            className="w-32"
          />

          {hasActiveFilters && (
            <Button variant="ghost" size="sm" onClick={clearFilters}>
              <Icon icon={X} size={16} />
              Clear
            </Button>
          )}
        </div>
      )}
    </div>
  )
}