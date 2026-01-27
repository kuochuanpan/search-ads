import { useState, useRef, useEffect } from 'react'
import { Sparkles, User, ChevronDown, Plus, Trash2, Check, X, FolderOpen } from 'lucide-react'
import { useActiveProject } from '@/store'
import { useProjects, useCreateProject, useDeleteProject } from '@/hooks/useProjects'
import { Button } from '@/components/ui/Button'
import { cn } from '@/lib/utils'


export function Header() {
  const { data: projects } = useProjects()
  const { project, setProject } = useActiveProject()
  const createProject = useCreateProject()
  const deleteProject = useDeleteProject()

  const [dropdownOpen, setDropdownOpen] = useState(false)
  const [isCreating, setIsCreating] = useState(false)
  const [newProjectName, setNewProjectName] = useState('')
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)

  // User menu state
  const [userMenuOpen, setUserMenuOpen] = useState(false)

  const dropdownRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const userMenuRef = useRef<HTMLDivElement>(null)

  // Close dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false)
        setIsCreating(false)
        setNewProjectName('')
        setDeleteConfirm(null)
      }
    }
    if (dropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [dropdownOpen])

  // Focus input when creating
  useEffect(() => {
    if (isCreating && inputRef.current) {
      inputRef.current.focus()
    }
  }, [isCreating])

  // Close user menu on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setUserMenuOpen(false)
      }
    }
    if (userMenuOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [userMenuOpen])

  const handleCreate = async () => {
    const name = newProjectName.trim()
    if (!name) return

    try {
      await createProject.mutateAsync({ name })
      setNewProjectName('')
      setIsCreating(false)
      setProject(name)
      setDropdownOpen(false)
    } catch (e) {
      console.error('Failed to create project:', e)
    }
  }

  const handleDelete = async (name: string, e: React.MouseEvent) => {
    e.stopPropagation()
    try {
      await deleteProject.mutateAsync({ name, deletePapers: false })
      setDeleteConfirm(null)
      if (project === name) {
        setProject(null)
      }
    } catch (e) {
      console.error('Failed to delete project:', e)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleCreate()
    } else if (e.key === 'Escape') {
      setIsCreating(false)
      setNewProjectName('')
    }
  }

  const selectedProjectName = project || 'All Projects'

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
          <FolderOpen size={16} className="text-muted-foreground" />
          <div className="relative" ref={dropdownRef}>
            <button
              onClick={() => setDropdownOpen(!dropdownOpen)}
              className="flex items-center gap-2 h-8 px-3 rounded-md border border-input bg-background text-sm hover:bg-secondary transition-colors min-w-[140px]"
            >
              <span className="truncate">{selectedProjectName}</span>
              <ChevronDown size={14} className="shrink-0 text-muted-foreground" />
            </button>

            {dropdownOpen && (
              <div className="absolute right-0 top-full mt-1 w-64 bg-card border rounded-lg shadow-lg py-1 z-50">
                {/* All Projects option */}
                <button
                  onClick={() => {
                    setProject(null)
                    setDropdownOpen(false)
                  }}
                  className={cn(
                    'w-full flex items-center justify-between px-3 py-2 text-sm text-left hover:bg-secondary transition-colors',
                    project === null && 'bg-primary/10 text-primary'
                  )}
                >
                  <span>All Projects</span>
                </button>

                {/* Divider */}
                {projects?.projects && projects.projects.length > 0 && (
                  <div className="border-t my-1" />
                )}

                {/* Project list */}
                {projects?.projects.map((p) => (
                  <div key={p.name} className="group relative">
                    {deleteConfirm === p.name ? (
                      <div className="px-3 py-2">
                        <p className="text-xs text-muted-foreground mb-2">Delete "{p.name}"?</p>
                        <div className="flex gap-1">
                          <Button
                            variant="destructive"
                            size="sm"
                            className="h-6 text-xs flex-1"
                            onClick={(e) => handleDelete(p.name, e)}
                          >
                            <Check size={12} />
                            Yes
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            className="h-6 text-xs flex-1"
                            onClick={(e) => {
                              e.stopPropagation()
                              setDeleteConfirm(null)
                            }}
                          >
                            <X size={12} />
                            No
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <button
                        onClick={() => {
                          setProject(p.name)
                          setDropdownOpen(false)
                        }}
                        className={cn(
                          'w-full flex items-center justify-between px-3 py-2 text-sm text-left hover:bg-secondary transition-colors',
                          project === p.name && 'bg-primary/10 text-primary'
                        )}
                      >
                        <span className="truncate">{p.name}</span>
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-muted-foreground">{p.paper_count}</span>
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              setDeleteConfirm(p.name)
                            }}
                            className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-destructive/10 text-destructive transition-opacity"
                            title="Delete project"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </button>
                    )}
                  </div>
                ))}

                {/* Divider */}
                <div className="border-t my-1" />

                {/* Create new project */}
                {isCreating ? (
                  <div className="px-3 py-2">
                    <div className="flex items-center gap-1">
                      <input
                        ref={inputRef}
                        type="text"
                        value={newProjectName}
                        onChange={(e) => setNewProjectName(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="Project name..."
                        className="flex-1 h-7 px-2 text-sm border rounded bg-background focus:outline-none focus:ring-1 focus:ring-ring"
                      />
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 w-7 p-0"
                        onClick={handleCreate}
                        disabled={!newProjectName.trim()}
                      >
                        <Check size={14} />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 w-7 p-0"
                        onClick={() => {
                          setIsCreating(false)
                          setNewProjectName('')
                        }}
                      >
                        <X size={14} />
                      </Button>
                    </div>
                  </div>
                ) : (
                  <button
                    onClick={() => setIsCreating(true)}
                    className="w-full flex items-center gap-2 px-3 py-2 text-sm text-left hover:bg-secondary transition-colors text-muted-foreground"
                  >
                    <Plus size={14} />
                    Create new project
                  </button>
                )}
              </div>
            )}
          </div>
        </div>

        {/* User Menu */}
        <div className="relative" ref={userMenuRef}>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setUserMenuOpen(!userMenuOpen)}
            className={cn(userMenuOpen && 'bg-secondary')}
          >
            <User size={18} />
          </Button>

          {userMenuOpen && (
            <div className="absolute right-0 top-full mt-1 w-48 bg-card border rounded-lg shadow-lg py-1 z-50">
              <a
                href="/settings"
                onClick={() => setUserMenuOpen(false)}
                className="block w-full px-4 py-2 text-sm text-left hover:bg-secondary transition-colors"
              >
                Profile Settings
              </a>
              <a
                href="/settings"
                onClick={() => setUserMenuOpen(false)}
                className="block w-full px-4 py-2 text-sm text-left hover:bg-secondary transition-colors"
              >
                API Keys
              </a>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}