import { ReactNode, useState, useEffect, useRef } from 'react'
import { cn } from '@/lib/utils'

interface ContextMenuProps {
  children: ReactNode
  items: ContextMenuItem[]
  onAction: (action: string) => void
}

export interface ContextMenuItem {
  label: string
  action: string
  icon?: ReactNode
  separator?: boolean
  disabled?: boolean
  danger?: boolean
}

interface ContextMenuState {
  isOpen: boolean
  x: number
  y: number
}

export function ContextMenu({ children, items, onAction }: ContextMenuProps) {
  const [menuState, setMenuState] = useState<ContextMenuState>({
    isOpen: false,
    x: 0,
    y: 0,
  })
  const menuRef = useRef<HTMLDivElement>(null)

  const handleContextMenu = (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()

    // Position the menu
    const x = e.clientX
    const y = e.clientY

    setMenuState({ isOpen: true, x, y })
  }

  const handleClose = () => {
    setMenuState({ ...menuState, isOpen: false })
  }

  const handleAction = (action: string) => {
    onAction(action)
    handleClose()
  }

  // Close menu on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        handleClose()
      }
    }

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') handleClose()
    }

    if (menuState.isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
      document.addEventListener('keydown', handleEscape)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleEscape)
    }
  }, [menuState.isOpen])

  // Adjust position if menu goes off screen
  useEffect(() => {
    if (menuState.isOpen && menuRef.current) {
      const menu = menuRef.current
      const rect = menu.getBoundingClientRect()
      const viewportWidth = window.innerWidth
      const viewportHeight = window.innerHeight

      let newX = menuState.x
      let newY = menuState.y

      if (rect.right > viewportWidth) {
        newX = viewportWidth - rect.width - 10
      }
      if (rect.bottom > viewportHeight) {
        newY = viewportHeight - rect.height - 10
      }

      if (newX !== menuState.x || newY !== menuState.y) {
        setMenuState({ ...menuState, x: newX, y: newY })
      }
    }
  }, [menuState.isOpen])

  return (
    <>
      <div onContextMenu={handleContextMenu}>{children}</div>

      {menuState.isOpen && (
        <div
          ref={menuRef}
          className="fixed z-50 min-w-[180px] bg-card border rounded-lg shadow-lg py-1"
          style={{ left: menuState.x, top: menuState.y }}
        >
          {items.map((item, index) => (
            item.separator ? (
              <div key={index} className="my-1 border-t" />
            ) : (
              <button
                key={item.action}
                onClick={() => handleAction(item.action)}
                disabled={item.disabled}
                className={cn(
                  'w-full flex items-center gap-2 px-3 py-1.5 text-sm text-left transition-colors',
                  'hover:bg-secondary',
                  item.disabled && 'opacity-50 cursor-not-allowed',
                  item.danger && 'text-destructive hover:text-destructive'
                )}
              >
                {item.icon}
                {item.label}
              </button>
            )
          ))}
        </div>
      )}
    </>
  )
}
