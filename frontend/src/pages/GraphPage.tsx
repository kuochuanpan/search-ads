import { useParams } from '@tanstack/react-router'
import { Network, ZoomIn, ZoomOut, RotateCcw, Maximize } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Icon } from '@/components/ui/Icon'

export function GraphPage() {
  // Note: This will be undefined on /graph route, defined on /graph/$bibcode
  const params = useParams({ strict: false })
  const bibcode = (params as { bibcode?: string })?.bibcode

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Knowledge Graph</h1>
          <p className="text-muted-foreground">
            {bibcode
              ? `Viewing citation network for ${bibcode}`
              : 'Explore connections between papers in your library'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm">
            Filter
          </Button>
          <Button variant="outline" size="sm">
            Layout
          </Button>
          <Button variant="outline" size="sm">
            Export
          </Button>
        </div>
      </div>

      {/* Graph Container */}
      <Card className="relative" style={{ height: 'calc(100vh - 200px)' }}>
        {/* Graph Controls */}
        <div className="absolute top-4 left-4 z-10 flex flex-col gap-1">
          <Button variant="outline" size="sm">
            <Icon icon={ZoomIn} size={16} />
          </Button>
          <Button variant="outline" size="sm">
            <Icon icon={ZoomOut} size={16} />
          </Button>
          <Button variant="outline" size="sm">
            <Icon icon={RotateCcw} size={16} />
          </Button>
          <Button variant="outline" size="sm">
            <Icon icon={Maximize} size={16} />
          </Button>
        </div>

        {/* Legend */}
        <div className="absolute top-4 right-4 z-10 bg-card border rounded-lg p-3 text-xs">
          <h4 className="font-medium mb-2">Legend</h4>
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-green-500" />
              <span>Your paper</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-blue-500" />
              <span>In library</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full border-2 border-gray-400 bg-transparent" />
              <span>Not in library</span>
            </div>
          </div>
        </div>

        {/* Placeholder */}
        <div className="flex items-center justify-center h-full text-muted-foreground">
          <div className="text-center">
            <Icon icon={Network} size={64} className="mx-auto mb-4 opacity-50" />
            <p className="text-lg font-medium">Graph Visualization</p>
            <p className="text-sm mt-2">
              Coming soon: Interactive citation network powered by vis.js
            </p>
            {bibcode && (
              <p className="text-sm mt-4 text-primary">
                Selected paper: {bibcode}
              </p>
            )}
          </div>
        </div>
      </Card>

      {/* Selected Paper Info */}
      {bibcode && (
        <Card className="p-4">
          <p className="text-sm text-muted-foreground mb-2">Selected Paper</p>
          <p className="font-medium">{bibcode}</p>
          <div className="flex gap-2 mt-3">
            <Button variant="outline" size="sm">View Paper</Button>
            <Button variant="outline" size="sm">Expand +1 Hop</Button>
            <Button variant="outline" size="sm">Expand +2 Hops</Button>
            <Button variant="outline" size="sm">Add All Refs to Library</Button>
          </div>
        </Card>
      )}
    </div>
  )
}
