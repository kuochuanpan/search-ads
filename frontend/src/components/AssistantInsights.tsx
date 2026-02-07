import { useQuery } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { Sparkles, Lightbulb, BookOpen } from 'lucide-react'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Icon } from '@/components/ui/Icon'
import { api } from '@/lib/api'
import type { AssistantInsightsData } from '@/lib/api'

async function fetchInsights(): Promise<AssistantInsightsData> {
  return api.getAssistantInsights()
}

export function AssistantInsights({ assistantName = 'OpenClaw' }: { assistantName?: string }) {
  const navigate = useNavigate();
  const { data, isLoading, isError } = useQuery({
    queryKey: ['assistant-insights'],
    queryFn: fetchInsights,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });

  const handleRecommendationClick = (bibcode: string) => {
    // Navigate to paper detail page with state
    navigate({ 
      to: '/library/$bibcode', 
      params: { bibcode },
      state: ({ from: 'home' } as any),
    });
  };

  if (isLoading) {
    return (
      <Card className="p-6 border-blue-500/20 bg-blue-50/50 dark:bg-blue-900/10 animate-pulse">
        <div className="h-6 w-1/3 bg-blue-200 dark:bg-blue-800 rounded mb-4"></div>
        <div className="h-4 w-full bg-blue-100 dark:bg-blue-900/50 rounded mb-2"></div>
        <div className="h-4 w-2/3 bg-blue-100 dark:bg-blue-900/50 rounded"></div>
      </Card>
    );
  }

  if (isError || !data) {
    return null; // Don't show anything if failed
  }

  if (!data.last_updated) {
    return (
        <Card className="p-6 border-blue-500/20 bg-blue-50/50 dark:bg-blue-900/10">
            <div className="flex items-center gap-3 mb-4">
                <div className="p-2 rounded-lg bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400">
                    <Icon icon={Sparkles} size={24} />
                </div>
                <h2 className="text-lg font-semibold text-blue-900 dark:text-blue-100">{assistantName}'s Insights</h2>
            </div>
            <p className="text-muted-foreground text-sm">No insights generated yet. Ask {assistantName} to sync!</p>
        </Card>
    )
  }

  const insights = data.insights ?? []
  const recommendations = data.recommendations ?? []

  return (
    <Card className="p-6 border-blue-500/20 bg-blue-50/50 dark:bg-blue-900/10 transition-all hover:border-blue-500/40">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400">
            <Icon icon={Sparkles} size={24} />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-blue-900 dark:text-blue-100">{assistantName}'s Insights</h2>
            <p className="text-xs text-blue-700/60 dark:text-blue-300/60">
              Updated: {new Date(data.last_updated).toLocaleString()}
            </p>
          </div>
        </div>
      </div>

      <div className="space-y-4">
        {/* Summary */}
        <div className="prose dark:prose-invert text-sm max-w-none text-blue-900/80 dark:text-blue-100/80 font-medium">
          <p>{data.summary}</p>
        </div>

        {/* Key Insights */}
        {insights.length > 0 && (
          <div className="space-y-2">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-blue-700 dark:text-blue-300 flex items-center gap-1">
              <Icon icon={Lightbulb} size={14} /> Key Takeaways
            </h3>
            <ul className="list-disc list-inside text-sm space-y-1 text-muted-foreground ml-1">
              {insights.map((insight, idx) => (
                <li key={idx}>{insight}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Recommendations */}
        {recommendations.length > 0 && (
          <div className="space-y-2 pt-2 border-t border-blue-200 dark:border-blue-800/50">
             <h3 className="text-xs font-semibold uppercase tracking-wider text-blue-700 dark:text-blue-300 flex items-center gap-1">
              <Icon icon={BookOpen} size={14} /> Recommended Reading
            </h3>
            <div className="grid gap-2">
              {recommendations.map((rec) => (
                <div 
                    key={rec.bibcode} 
                    className="flex flex-col gap-1 p-2 rounded bg-white/50 dark:bg-black/20 hover:bg-white/80 dark:hover:bg-black/40 transition-colors cursor-pointer group"
                    onClick={() => handleRecommendationClick(rec.bibcode)}
                >
                    <div className="flex items-center justify-between">
                        <span className="font-medium text-sm group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">{rec.title}</span>
                        <Badge variant="outline" className="text-[10px] h-5">{rec.bibcode}</Badge>
                    </div>
                    <p className="text-xs text-muted-foreground">{rec.reason}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}
