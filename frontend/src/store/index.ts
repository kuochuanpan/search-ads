import { create } from 'zustand'

interface PaperSelectionState {
  selectedBibcodes: Set<string>
  toggleSelection: (bibcode: string) => void
  selectAll: (bibcodes: string[]) => void
  deselectAll: () => void
  isSelected: (bibcode: string) => boolean
  count: () => number
}

export const usePaperSelection = create<PaperSelectionState>((set, get) => ({
  selectedBibcodes: new Set(),
  toggleSelection: (bibcode) => set((state) => {
    const newSelection = new Set(state.selectedBibcodes)
    if (newSelection.has(bibcode)) {
      newSelection.delete(bibcode)
    } else {
      newSelection.add(bibcode)
    }
    return { selectedBibcodes: newSelection }
  }),
  selectAll: (bibcodes) => set({ selectedBibcodes: new Set(bibcodes) }),
  deselectAll: () => set({ selectedBibcodes: new Set() }),
  isSelected: (bibcode) => get().selectedBibcodes.has(bibcode),
  count: () => get().selectedBibcodes.size,
}))

interface SidebarState {
  collapsed: boolean
  width: number
  toggle: () => void
  setCollapsed: (collapsed: boolean) => void
  setWidth: (width: number) => void
}

const MIN_SIDEBAR_WIDTH = 180
const MAX_SIDEBAR_WIDTH = 400
const DEFAULT_SIDEBAR_WIDTH = 256

export const useSidebar = create<SidebarState>((set) => ({
  collapsed: false,
  width: DEFAULT_SIDEBAR_WIDTH,
  toggle: () => set((state) => ({ collapsed: !state.collapsed })),
  setCollapsed: (collapsed) => set({ collapsed }),
  setWidth: (width) => set({ width: Math.max(MIN_SIDEBAR_WIDTH, Math.min(MAX_SIDEBAR_WIDTH, width)) }),
}))

interface ActiveProjectState {
  project: string | null
  setProject: (project: string | null) => void
}

export const useActiveProject = create<ActiveProjectState>((set) => ({
  project: null,
  setProject: (project) => set({ project }),
}))