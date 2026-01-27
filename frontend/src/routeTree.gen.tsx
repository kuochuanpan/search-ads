import {
  createRootRoute,
  createRoute,
  Outlet,
  ScrollRestoration,
} from '@tanstack/react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Header } from '@/components/layout/Header'
import { Sidebar } from '@/components/layout/Sidebar'
import { useSidebar } from '@/store'
import { cn } from '@/lib/utils'

// Pages
import { HomePage } from '@/pages/HomePage'
import { LibraryPage } from '@/pages/LibraryPage'
import { PaperDetailPage } from '@/pages/PaperDetailPage'
import { SearchPage } from '@/pages/SearchPage'
import { GraphPage } from '@/pages/GraphPage'
import { WritingPage } from '@/pages/WritingPage'
import { ImportPage } from '@/pages/ImportPage'
import { SettingsPage } from '@/pages/SettingsPage'

// Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60, // 1 minute
      retry: 1,
    },
  },
})

// Root layout component
function RootLayout() {
  const { collapsed, width } = useSidebar()

  return (
    <QueryClientProvider client={queryClient}>
      <div className="min-h-screen bg-background text-foreground">
        <Header />
        <Sidebar />
        <main
          className="pt-14 min-h-screen transition-[padding] duration-100"
          style={{ paddingLeft: collapsed ? undefined : `${width}px` }}
        >
          <div className={cn('p-6', collapsed && 'lg:pl-16')}>
            <Outlet />
          </div>
        </main>
        <ScrollRestoration />
      </div>
    </QueryClientProvider>
  )
}

// Root route
const rootRoute = createRootRoute({
  component: RootLayout,
})

// Home route
const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  component: HomePage,
})

// Library route
const libraryRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/library',
  component: LibraryPage,
})

// Paper detail route
const paperDetailRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/library/$bibcode',
  component: PaperDetailPage,
})

// Search route
const searchRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/search',
  component: SearchPage,
})

// Graph route
const graphRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/graph',
  component: GraphPage,
})

// Graph with paper route
const graphPaperRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/graph/$bibcode',
  component: GraphPage,
})

// Writing route
const writingRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/writing',
  component: WritingPage,
})

// Import route
const importRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/import',
  component: ImportPage,
})

// Settings route
const settingsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/settings',
  component: SettingsPage,
})

// Route tree
export const routeTree = rootRoute.addChildren([
  indexRoute,
  libraryRoute,
  paperDetailRoute,
  searchRoute,
  graphRoute,
  graphPaperRoute,
  writingRoute,
  importRoute,
  settingsRoute,
])
