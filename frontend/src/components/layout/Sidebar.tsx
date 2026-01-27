import { useNavigate } from '@tanstack/react-router'
import { useRef, useCallback } from 'react'
import {
  Home,
  BookOpen,
  Search,
  Network,
  FileText,
  Download,
  Settings as SettingsIcon,
} from 'lucide-react'
import { useSidebar } from '@/store'
import { cn } from '@/lib/utils'

interface NavItem {
  path: string
  label: string
  icon: React.ElementType
}

const navItems: NavItem[] = [
  { path: '/', label: 'Home', icon: Home },
  { path: '/library', label: 'Library', icon: BookOpen },
  { path: '/search', label: 'Search', icon: Search },
  { path: '/graph', label: 'Graph', icon: Network },
  { path: '/writing', label: 'Writing', icon: FileText },
  { path: '/import', label: 'Import', icon: Download },
  { path: '/settings', label: 'Settings', icon: SettingsIcon },
]

export function Sidebar() {
  const navigate = useNavigate()
  const { collapsed, width, toggle, setCollapsed, setWidth } = useSidebar()
  const isResizing = useRef(false)

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    isResizing.current = true
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'

    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing.current) return
      setWidth(e.clientX)
    }

    const handleMouseUp = () => {
      isResizing.current = false
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
  }, [setWidth])

  return (
    <>
      {/* Mobile backdrop */}
      {!collapsed && (
        <div
          className="fixed inset-0 bg-background/80 backdrop-blur-sm z-40 lg:hidden"
          onClick={toggle}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed left-0 top-14 bottom-0 z-50 bg-card border-r',
          collapsed ? 'w-0 lg:w-16' : ''
        )}
        style={collapsed ? undefined : { width: `${width}px` }}
      >
        {/* Toggle button */}
        <button
          onClick={toggle}
          className="absolute -right-3 top-4 h-6 w-6 rounded-full bg-background border flex items-center justify-center text-muted-foreground hover:text-foreground lg:block hidden z-50"
        >
          {collapsed ? <>&raquo;</> : <>&laquo;</>}
        </button>

        {/* Resize handle */}
        {!collapsed && (
          <div
            onMouseDown={handleMouseDown}
            className="absolute right-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-primary/50 transition-colors hidden lg:block"
          />
        )}

        {/* Navigation */}
        <nav className="p-2 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon
            return (
              <button
                key={item.path}
                onClick={() => {
                  if (item.path === '/library') {
                    navigate({ to: item.path, state: { resetScroll: true } as any })
                  } else {
                    navigate({ to: item.path as any })
                  }
                  // Auto-collapse on mobile
                  if (window.innerWidth < 1024) {
                    setCollapsed(true)
                  }
                }}
                className={cn(
                  'w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors',
                  'hover:bg-secondary hover:text-secondary-foreground',
                  'text-muted-foreground'
                )}
                title={item.label}
              >
                <Icon size={18} />
                {!collapsed && <span>{item.label}</span>}
              </button>
            )
          })}
        </nav>
      </aside>
    </>
  )
}