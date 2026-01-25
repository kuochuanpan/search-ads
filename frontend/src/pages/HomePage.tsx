import { useNavigate } from '@tanstack/react-router'
import { BookOpen, Search, Star, FileText, Network, TrendingUp } from 'lucide-react'
import { Card } from '@/components/ui/Card'
import { Icon } from '@/components/ui/Icon'
import { useStats } from '@/hooks/useStats'
import { usePapers } from '@/hooks/usePapers'

export function HomePage() {
  const navigate = useNavigate()
  const { data: stats } = useStats()
  const { data: recentPapers } = usePapers({ limit: 5, sort_by: 'updated_at', sort_order: 'desc' })
  const { data: myPapers } = usePapers({ limit: 5, is_my_paper: true, sort_by: 'citation_count', sort_order: 'desc' })

  const greeting = () => {
    const hour = new Date().getHours()
    if (hour < 12) return 'Good morning'
    if (hour < 18) return 'Good afternoon'
    return 'Good evening'
  }

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Greeting */}
      <div className="text-center py-8">
        <h1 className="text-2xl font-semibold mb-2">
          {greeting()}! Your library has {stats?.total_papers || 0} papers
          {stats?.total_projects ? ` across ${stats.total_projects} projects` : ''}.
        </h1>
      </div>

      {/* Quick Search */}
      <Card className="p-4">
        <div
          className="flex items-center gap-3 px-4 py-3 rounded-lg border border-input bg-background cursor-pointer hover:border-primary/50 transition-colors"
          onClick={() => navigate({ to: '/search' })}
        >
          <Icon icon={Search} size={20} className="text-muted-foreground" />
          <span className="text-muted-foreground">Search your library or discover new papers...</span>
          <kbd className="ml-auto px-2 py-1 text-xs rounded bg-secondary text-muted-foreground">Cmd+K</kbd>
        </div>
      </Card>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="p-4 cursor-pointer hover:border-primary/50 transition-colors" onClick={() => navigate({ to: '/library' })}>
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-blue-100 dark:bg-blue-900/30">
              <Icon icon={BookOpen} size={24} className="text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <p className="text-2xl font-semibold">{stats?.total_papers || 0}</p>
              <p className="text-sm text-muted-foreground">Total Papers</p>
            </div>
          </div>
        </Card>

        <Card className="p-4 cursor-pointer hover:border-primary/50 transition-colors" onClick={() => navigate({ to: '/library', search: { is_my_paper: true } as any })}>
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-yellow-100 dark:bg-yellow-900/30">
              <Icon icon={Star} size={24} className="text-yellow-600 dark:text-yellow-400" />
            </div>
            <div>
              <p className="text-2xl font-semibold">{stats?.my_papers_count || 0}</p>
              <p className="text-sm text-muted-foreground">My Papers</p>
            </div>
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-green-100 dark:bg-green-900/30">
              <Icon icon={FileText} size={24} className="text-green-600 dark:text-green-400" />
            </div>
            <div>
              <p className="text-2xl font-semibold">{stats?.total_notes || 0}</p>
              <p className="text-sm text-muted-foreground">Notes</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Recent Papers and My Papers */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Recent Papers */}
        <Card className="p-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold flex items-center gap-2">
              <Icon icon={BookOpen} size={18} />
              Recent Papers
            </h2>
            <button
              className="text-sm text-primary hover:underline"
              onClick={() => navigate({ to: '/library' })}
            >
              View All
            </button>
          </div>
          <div className="space-y-2">
            {recentPapers?.papers.length === 0 && (
              <p className="text-muted-foreground text-sm py-4 text-center">
                No papers yet. Import some papers to get started.
              </p>
            )}
            {recentPapers?.papers.map((paper) => (
              <div
                key={paper.bibcode}
                className="p-2 rounded hover:bg-secondary/50 cursor-pointer transition-colors"
                onClick={() => navigate({ to: '/library/$bibcode', params: { bibcode: paper.bibcode } })}
              >
                <p className="text-sm font-medium truncate">{paper.title}</p>
                <p className="text-xs text-muted-foreground">
                  {paper.first_author || paper.authors?.[0]} · {paper.year}
                </p>
              </div>
            ))}
          </div>
        </Card>

        {/* My Papers */}
        <Card className="p-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold flex items-center gap-2">
              <Icon icon={Star} size={18} className="text-yellow-500" />
              My Papers
            </h2>
            <button
              className="text-sm text-primary hover:underline"
              onClick={() => navigate({ to: '/library', search: { is_my_paper: true } as any })}
            >
              View All
            </button>
          </div>
          <div className="space-y-2">
            {myPapers?.papers.length === 0 && (
              <p className="text-muted-foreground text-sm py-4 text-center">
                Mark papers as yours to see them here.
              </p>
            )}
            {myPapers?.papers.map((paper) => (
              <div
                key={paper.bibcode}
                className="p-2 rounded hover:bg-secondary/50 cursor-pointer transition-colors"
                onClick={() => navigate({ to: '/library/$bibcode', params: { bibcode: paper.bibcode } })}
              >
                <p className="text-sm font-medium truncate">{paper.title}</p>
                <p className="text-xs text-muted-foreground flex items-center gap-2">
                  <span>{paper.year}</span>
                  {paper.citation_count !== undefined && (
                    <>
                      <span>·</span>
                      <span className="flex items-center gap-1">
                        <Icon icon={TrendingUp} size={12} />
                        {paper.citation_count} citations
                      </span>
                    </>
                  )}
                </p>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Knowledge Graph Preview */}
      <Card className="p-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold flex items-center gap-2">
            <Icon icon={Network} size={18} />
            Knowledge Graph
          </h2>
          <button
            className="text-sm text-primary hover:underline"
            onClick={() => navigate({ to: '/graph' })}
          >
            Explore
          </button>
        </div>
        <div className="h-32 flex items-center justify-center border-2 border-dashed rounded-lg text-muted-foreground">
          <p className="text-sm">Graph visualization coming soon...</p>
        </div>
      </Card>
    </div>
  )
}
