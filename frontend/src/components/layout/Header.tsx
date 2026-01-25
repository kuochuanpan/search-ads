import { useState, useRef, useEffect } from 'react'
import { Sparkles, Settings, User, ChevronDown, Plus, Trash2, Check, X, FolderOpen, Save, Loader2 } from 'lucide-react'
import { useActiveProject } from '@/store'
import { useProjects, useCreateProject, useDeleteProject } from '@/hooks/useProjects'
import { Button } from '@/components/ui/Button'
import { cn } from '@/lib/utils'
import { api } from '@/lib/api'

export function Header() {
  const { data: projects } = useProjects()
  const { project, setProject } = useActiveProject()
  const createProject = useCreateProject()
  const deleteProject = useDeleteProject()

  const [dropdownOpen, setDropdownOpen] = useState(false)
  const [isCreating, setIsCreating] = useState(false)
  const [newProjectName, setNewProjectName] = useState('')
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)

  // User profile panel state
  const [userPanelOpen, setUserPanelOpen] = useState(false)
  const [authorNames, setAuthorNames] = useState('')
  const [authorNamesLoading, setAuthorNamesLoading] = useState(false)
  const [authorNamesSaving, setAuthorNamesSaving] = useState(false)
  const [authorNamesSaved, setAuthorNamesSaved] = useState(false)

  const dropdownRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const userPanelRef = useRef<HTMLDivElement>(null)

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

  // Close user panel on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (userPanelRef.current && !userPanelRef.current.contains(e.target as Node)) {
        setUserPanelOpen(false)
      }
    }
    if (userPanelOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [userPanelOpen])

  // Fetch author names when panel opens
  useEffect(() => {
    if (userPanelOpen) {
      setAuthorNamesLoading(true)
      api.getAuthorNames()
        .then((data) => {
          setAuthorNames(data.author_names)
        })
        .catch((e) => {
          console.error('Failed to fetch author names:', e)
        })
        .finally(() => {
          setAuthorNamesLoading(false)
        })
    }
  }, [userPanelOpen])

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

  const handleSaveAuthorNames = async () => {
    setAuthorNamesSaving(true)
    setAuthorNamesSaved(false)
    try {
      await api.updateAuthorNames(authorNames)
      setAuthorNamesSaved(true)
      setTimeout(() => setAuthorNamesSaved(false), 2000)
    } catch (e) {
      console.error('Failed to save author names:', e)
    } finally {
      setAuthorNamesSaving(false)
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

        {/* Settings Button */}
        <Button variant="ghost" size="sm">
          <Settings size={18} />
        </Button>

        {/* User Menu */}
        <div className="relative" ref={userPanelRef}>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setUserPanelOpen(!userPanelOpen)}
            className={cn(userPanelOpen && 'bg-secondary')}
          >
            <User size={18} />
          </Button>

          {userPanelOpen && (
            <div className="absolute right-0 top-full mt-1 w-80 bg-card border rounded-lg shadow-lg p-4 z-50">
              <h3 className="font-medium text-sm mb-3">Author Profile</h3>

              <div className="space-y-3">
                <div>
                  <label className="text-xs text-muted-foreground block mb-1">
                    Your Author Names
                  </label>
                  <p className="text-xs text-muted-foreground mb-2">
                    Enter your name variations separated by semicolons for auto-detection of your papers.
                  </p>
                  {authorNamesLoading ? (
                    <div className="flex items-center justify-center py-4">
                      <Loader2 size={16} className="animate-spin text-muted-foreground" />
                    </div>
                  ) : (
                    <textarea
                      value={authorNames}
                      onChange={(e) => setAuthorNames(e.target.value)}
                      placeholder="Pan, K.-C.; Pan, Kuo-Chuan; Pan, K."
                      className="w-full h-20 px-2 py-1.5 text-sm border rounded bg-background focus:outline-none focus:ring-1 focus:ring-ring resize-none"
                    />
                  )}
                </div>

                <div className="flex items-center justify-between">
                  <p className="text-xs text-muted-foreground">
                    {authorNamesSaved && (
                      <span className="text-green-600">Saved successfully!</span>
                    )}
                  </p>
                  <Button
                    variant="default"
                    size="sm"
                    onClick={handleSaveAuthorNames}
                    disabled={authorNamesLoading || authorNamesSaving}
                    className="gap-1"
                  >
                    {authorNamesSaving ? (
                      <Loader2 size={14} className="animate-spin" />
                    ) : (
                      <Save size={14} />
                    )}
                    Save
                  </Button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}