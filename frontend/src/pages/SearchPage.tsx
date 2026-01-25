import { useState } from 'react'
import { Search, Sparkles, BookOpen, FileText } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Icon } from '@/components/ui/Icon'

type SearchMode = 'natural' | 'keywords' | 'similar'
type SearchScope = 'library' | 'ads' | 'pdf'

export function SearchPage() {
  const [query, setQuery] = useState('')
  const [mode, setMode] = useState<SearchMode>('natural')
  const [scopes, setScopes] = useState<Set<SearchScope>>(new Set(['library', 'ads']))
  const [isSearching, setIsSearching] = useState(false)

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
    setIsSearching(true)
    // TODO: Implement search
    setTimeout(() => setIsSearching(false), 1000)
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

        <Button className="w-full mt-4" onClick={handleSearch} disabled={isSearching || !query.trim()}>
          <Icon icon={Search} size={16} />
          {isSearching ? 'Searching...' : 'Search'}
        </Button>
      </Card>

      {/* Results placeholder */}
      <Card className="p-6">
        <div className="text-center py-12 text-muted-foreground">
          <Icon icon={Search} size={48} className="mx-auto mb-4 opacity-50" />
          <p>Enter a query above to search for papers</p>
        </div>
      </Card>
    </div>
  )
}
