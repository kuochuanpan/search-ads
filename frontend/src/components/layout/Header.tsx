import { Sparkles, Settings, User, ChevronDown } from 'lucide-react'
import { useActiveProject } from '@/store'
import { useProjects } from '@/hooks/useProjects'
import { Button } from '@/components/ui/Button'

export function Header() {
  const { data: projects } = useProjects()
  const { project, setProject } = useActiveProject()

  return (
    <header className="fixed top-0 left-0 right-0 z-50 h-14 border-b bg-background flex items-center justify-between px-4">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <Sparkles size={24} className="text-primary" />
          <span className="font-semibold text-lg">Search-ADS</span>
        </div>
      </div>

      <div className="flex items-center gap-4">
        {/* Project Dropdown */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Project:</span>
          <div className="relative">
            <select
              value={project || ''}
              onChange={(e) => setProject(e.target.value || null)}
              className="flex items-center gap-1 h-8 px-3 rounded-md border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring appearance-none pr-8 cursor-pointer"
            >
              <option value="">All Projects</option>
              {projects?.projects.map((p) => (
                <option key={p.name} value={p.name}>
                  {p.name} ({p.paper_count})
                </option>
              ))}
            </select>
            <ChevronDown size={14} className="absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none" />
          </div>
        </div>

        {/* Settings Button */}
        <Button variant="ghost" size="sm">
          <Settings size={18} />
        </Button>

        {/* User Menu */}
        <Button variant="ghost" size="sm">
          <User size={18} />
        </Button>
      </div>
    </header>
  )
}