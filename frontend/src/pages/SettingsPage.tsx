import { useState } from 'react'
import { Check, AlertCircle, RefreshCw, Trash2, Database, Key, Palette, BookOpen } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Icon } from '@/components/ui/Icon'
import { useStats } from '@/hooks/useStats'
import { api } from '@/lib/api'
import { useQuery } from '@tanstack/react-query'

export function SettingsPage() {
  const { data: stats } = useStats()
  const { data: settings } = useQuery({
    queryKey: ['settings'],
    queryFn: () => api.getSettings(),
  })
  const { data: vectorStats } = useQuery({
    queryKey: ['vector-stats'],
    queryFn: () => api.getVectorStats(),
  })

  const [testingApi, setTestingApi] = useState<string | null>(null)
  const [apiTestResult, setApiTestResult] = useState<{ service: string; valid: boolean; message: string } | null>(null)

  const handleTestApi = async (service: 'ads' | 'openai' | 'anthropic') => {
    setTestingApi(service)
    setApiTestResult(null)
    try {
      const result = await api.testApiKey(service)
      setApiTestResult({ service, ...result })
    } catch (e: any) {
      setApiTestResult({ service, valid: false, message: e.message || 'Test failed' })
    } finally {
      setTestingApi(null)
    }
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="py-4">
        <h1 className="text-2xl font-semibold">Settings</h1>
        <p className="text-muted-foreground">Configure your Search-ADS preferences</p>
      </div>

      {/* General */}
      <Card className="p-6">
        <div className="flex items-center gap-2 mb-4">
          <Icon icon={Palette} size={20} className="text-primary" />
          <h2 className="font-medium">General</h2>
        </div>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">Theme</p>
              <p className="text-sm text-muted-foreground">Choose your preferred color scheme</p>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" size="sm">System</Button>
              <Button variant="outline" size="sm">Light</Button>
              <Button variant="outline" size="sm">Dark</Button>
            </div>
          </div>
        </div>
      </Card>

      {/* API Keys */}
      <Card className="p-6">
        <div className="flex items-center gap-2 mb-4">
          <Icon icon={Key} size={20} className="text-primary" />
          <h2 className="font-medium">API Keys</h2>
        </div>
        <p className="text-sm text-muted-foreground mb-4">
          API keys are configured via environment variables. Use the Test button to verify they work.
        </p>

        <div className="space-y-3">
          <div className="flex items-center justify-between p-3 border rounded-lg">
            <div>
              <p className="font-medium">ADS API Key</p>
              <p className="text-sm text-muted-foreground">
                {settings?.has_ads_key ? 'Configured' : 'Not configured'}
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleTestApi('ads')}
              disabled={testingApi === 'ads' || !settings?.has_ads_key}
            >
              {testingApi === 'ads' ? 'Testing...' : 'Test'}
            </Button>
          </div>

          <div className="flex items-center justify-between p-3 border rounded-lg">
            <div>
              <p className="font-medium">OpenAI API Key</p>
              <p className="text-sm text-muted-foreground">
                {settings?.has_openai_key ? 'Configured' : 'Not configured'}
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleTestApi('openai')}
              disabled={testingApi === 'openai' || !settings?.has_openai_key}
            >
              {testingApi === 'openai' ? 'Testing...' : 'Test'}
            </Button>
          </div>

          <div className="flex items-center justify-between p-3 border rounded-lg">
            <div>
              <p className="font-medium">Anthropic API Key</p>
              <p className="text-sm text-muted-foreground">
                {settings?.has_anthropic_key ? 'Configured' : 'Not configured'}
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleTestApi('anthropic')}
              disabled={testingApi === 'anthropic' || !settings?.has_anthropic_key}
            >
              {testingApi === 'anthropic' ? 'Testing...' : 'Test'}
            </Button>
          </div>
        </div>

        {apiTestResult && (
          <div className={`mt-3 p-3 rounded flex items-center gap-2 ${apiTestResult.valid ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-200' : 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200'}`}>
            <Icon icon={apiTestResult.valid ? Check : AlertCircle} size={16} />
            {apiTestResult.service.toUpperCase()}: {apiTestResult.message}
          </div>
        )}
      </Card>

      {/* Citation Style */}
      <Card className="p-6">
        <div className="flex items-center gap-2 mb-4">
          <Icon icon={BookOpen} size={20} className="text-primary" />
          <h2 className="font-medium">Citation Style</h2>
        </div>
        <div className="space-y-4">
          <div>
            <p className="font-medium mb-2">Citation Key Format</p>
            <div className="flex gap-2">
              <Button variant={settings?.citation_key_format === 'bibcode' ? 'secondary' : 'outline'} size="sm">
                bibcode
              </Button>
              <Button variant={settings?.citation_key_format === 'author_year' ? 'secondary' : 'outline'} size="sm">
                author_year
              </Button>
              <Button variant={settings?.citation_key_format === 'author_year_title' ? 'secondary' : 'outline'} size="sm">
                author_year_title
              </Button>
            </div>
          </div>
        </div>
      </Card>

      {/* Database Stats */}
      <Card className="p-6">
        <div className="flex items-center gap-2 mb-4">
          <Icon icon={Database} size={20} className="text-primary" />
          <h2 className="font-medium">Database</h2>
        </div>

        <div className="grid grid-cols-2 gap-4 text-sm">
          <div className="p-3 border rounded-lg">
            <p className="text-muted-foreground">Papers in database</p>
            <p className="text-xl font-semibold">{stats?.total_papers || 0}</p>
          </div>
          <div className="p-3 border rounded-lg">
            <p className="text-muted-foreground">Vector embeddings</p>
            <p className="text-xl font-semibold">{vectorStats?.abstracts_count || 0}</p>
          </div>
          <div className="p-3 border rounded-lg">
            <p className="text-muted-foreground">PDFs downloaded</p>
            <p className="text-xl font-semibold">
              {stats?.papers_with_pdf || 0}
              <span className="text-sm font-normal text-muted-foreground ml-1">
                ({stats?.total_papers ? Math.round((stats.papers_with_pdf / stats.total_papers) * 100) : 0}%)
              </span>
            </p>
          </div>
          <div className="p-3 border rounded-lg">
            <p className="text-muted-foreground">PDFs embedded</p>
            <p className="text-xl font-semibold">
              {stats?.papers_with_embedded_pdf || 0}
              <span className="text-sm font-normal text-muted-foreground ml-1">
                ({stats?.papers_with_pdf ? Math.round((stats.papers_with_embedded_pdf / stats.papers_with_pdf) * 100) : 0}% of PDFs)
              </span>
            </p>
          </div>
        </div>

        <div className="flex gap-2 mt-4">
          <Button variant="outline" size="sm">
            <Icon icon={RefreshCw} size={14} />
            Re-embed All Papers
          </Button>
          <Button variant="outline" size="sm">
            Export Database
          </Button>
        </div>
      </Card>

      {/* Danger Zone */}
      <Card className="p-6 border-destructive/50">
        <h2 className="font-medium text-destructive mb-4">Danger Zone</h2>
        <p className="text-sm text-muted-foreground mb-4">
          These actions are irreversible. Please be careful.
        </p>
        <Button variant="destructive" size="sm">
          <Icon icon={Trash2} size={14} />
          Clear All Data
        </Button>
      </Card>
    </div>
  )
}
