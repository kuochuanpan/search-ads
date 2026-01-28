import { useState, useEffect } from 'react'
import { useTheme } from '@/components/ThemeProvider'
import { Check, AlertCircle, RefreshCw, Trash2, Database, Key, Palette, BookOpen, User, Save, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Icon } from '@/components/ui/Icon'
import { useStats } from '@/hooks/useStats'
import { api } from '@/lib/api'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

export function SettingsPage() {
  const { theme, setTheme } = useTheme()

  const { data: stats } = useStats()
  const { data: settings } = useQuery({
    queryKey: ['settings'],
    queryFn: () => api.getSettings(),
  })
  const { data: vectorStats } = useQuery({
    queryKey: ['vector-stats'],
    queryFn: () => api.getVectorStats(),
  })

  const queryClient = useQueryClient()

  const [testingApi, setTestingApi] = useState<string | null>(null)
  const [apiTestResult, setApiTestResult] = useState<{ service: string; valid: boolean; message: string } | null>(null)

  // Author Names State
  const [authorNames, setAuthorNames] = useState('')
  const [authorNamesSaved, setAuthorNamesSaved] = useState(false)

  // Sync author names from settings when loaded
  useEffect(() => {
    if (settings?.my_author_names) {
      setAuthorNames(settings.my_author_names)
    }
  }, [settings])

  const updateAuthorNames = useMutation({
    mutationFn: (names: string) => api.updateAuthorNames(names),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] })
      setAuthorNamesSaved(true)
      setTimeout(() => setAuthorNamesSaved(false), 2000)
    },
  })

  // API Keys state
  const [adsKey, setAdsKey] = useState('')
  const [openaiKey, setOpenaiKey] = useState('')
  const [anthropicKey, setAnthropicKey] = useState('')

  const updateApiKeys = useMutation({
    mutationFn: (keys: any) => api.updateApiKeys(keys),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] })
      // We don't clear inputs here to let user see what they typed? 
      // Actually we should clear them because they are secure fields
      // and checking 'settings' will update the placeholders.
      // But we did inline setKey('') in the onClick handlers.
    },
  })

  const handleSaveAuthorNames = () => {
    updateAuthorNames.mutate(authorNames)
  }

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

      {/* User Profile & Identity */}
      <Card className="p-6">
        <div className="flex items-center gap-2 mb-4">
          <Icon icon={User} size={20} className="text-primary" />
          <h2 className="font-medium">User Profile & Identity</h2>
        </div>
        <div className="space-y-4">
          <div>
            <label className="font-medium block mb-1">
              My Author Names
            </label>
            <p className="text-sm text-muted-foreground mb-3">
              Enter your name variations separated by semicolons (e.g., "Pan, K.-C.; Pan, Kuo-Chuan").
              These are used to automatically tag your papers in the library.
            </p>
            <textarea
              value={authorNames}
              onChange={(e) => setAuthorNames(e.target.value)}
              placeholder="Pan, K.-C.; Pan, Kuo-Chuan; Pan, K."
              className="w-full h-24 px-3 py-2 text-sm border rounded-md bg-transparent focus:outline-none focus:ring-1 focus:ring-ring resize-none"
            />
          </div>
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              {authorNamesSaved && <span className="text-green-600 flex items-center gap-1"><Check size={14} /> Saved successfully</span>}
            </p>
            <Button
              onClick={handleSaveAuthorNames}
              disabled={updateAuthorNames.isPending}
              className="gap-2"
            >
              {updateAuthorNames.isPending ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
              Save Changes
            </Button>
          </div>
        </div>
      </Card>

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
              <Button
                variant={theme === 'system' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setTheme('system')}
              >
                System
              </Button>
              <Button
                variant={theme === 'light' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setTheme('light')}
              >
                Light
              </Button>
              <Button
                variant={theme === 'dark' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setTheme('dark')}
              >
                Dark
              </Button>
            </div>
          </div>
        </div>
      </Card>

      {/* AI Models */}
      <Card className="p-6">
        <div className="flex items-center gap-2 mb-4">
          <Icon icon={Database} size={20} className="text-primary" />
          <h2 className="font-medium">AI Models</h2>
        </div>
        <div className="space-y-4">
          <div>
            <label className="font-medium block mb-1 text-sm">OpenAI Model</label>
            <div className="flex gap-2">
              <input
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                value={settings?.openai_model || 'gpt-4o-mini'}
                onChange={(e) => {
                  if (settings) {
                    api.updateModels(e.target.value, settings.anthropic_model).then(() => {
                      queryClient.invalidateQueries({ queryKey: ['settings'] })
                    })
                  }
                }}
              />
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Recommended: <code>gpt-4o-mini</code> for speed, <code>gpt-4o</code> for quality.
            </p>
          </div>

          <div>
            <label className="font-medium block mb-1 text-sm">Anthropic Model</label>
            <div className="flex gap-2">
              <input
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                value={settings?.anthropic_model || 'claude-3-haiku-20240307'}
                onChange={(e) => {
                  if (settings) {
                    api.updateModels(settings.openai_model, e.target.value).then(() => {
                      queryClient.invalidateQueries({ queryKey: ['settings'] })
                    })
                  }
                }}
              />
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Recommended: <code>claude-3-haiku-20240307</code> for speed, <code>claude-3-5-sonnet-20240620</code> for quality.
            </p>
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
          Enter your API keys below. They will be stored securely in <code>~/.search-ads/.env</code>.
        </p>

        <div className="space-y-4">
          {/* ADS Key */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium">ADS API Key</label>
              <span className={`text-xs ${settings?.has_ads_key ? 'text-green-600' : 'text-amber-600'}`}>
                {settings?.has_ads_key ? 'Configured' : 'Missing'}
              </span>
            </div>
            <div className="flex gap-2">
              <input
                type="password"
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                placeholder={settings?.has_ads_key ? "••••••••••••••••" : "Enter ADS API Key"}
                value={adsKey}
                onChange={(e) => setAdsKey(e.target.value)}
              />
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  updateApiKeys.mutate({ ads_api_key: adsKey })
                  setAdsKey('')
                }}
                disabled={!adsKey || updateApiKeys.isPending}
              >
                Save
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleTestApi('ads')}
                disabled={testingApi === 'ads' || !settings?.has_ads_key}
              >
                {testingApi === 'ads' ? '...' : 'Test'}
              </Button>
            </div>
          </div>

          {/* OpenAI Key */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium">OpenAI API Key</label>
              <span className={`text-xs ${settings?.has_openai_key ? 'text-green-600' : 'text-amber-600'}`}>
                {settings?.has_openai_key ? 'Configured' : 'Missing'}
              </span>
            </div>
            <div className="flex gap-2">
              <input
                type="password"
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                placeholder={settings?.has_openai_key ? "••••••••••••••••" : "Enter OpenAI API Key"}
                value={openaiKey}
                onChange={(e) => setOpenaiKey(e.target.value)}
              />
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  updateApiKeys.mutate({ openai_api_key: openaiKey })
                  setOpenaiKey('')
                }}
                disabled={!openaiKey || updateApiKeys.isPending}
              >
                Save
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleTestApi('openai')}
                disabled={testingApi === 'openai' || !settings?.has_openai_key}
              >
                {testingApi === 'openai' ? '...' : 'Test'}
              </Button>
            </div>
          </div>

          {/* Anthropic Key */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium">Anthropic API Key</label>
              <span className={`text-xs ${settings?.has_anthropic_key ? 'text-green-600' : 'text-amber-600'}`}>
                {settings?.has_anthropic_key ? 'Configured' : 'Missing'}
              </span>
            </div>
            <div className="flex gap-2">
              <input
                type="password"
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                placeholder={settings?.has_anthropic_key ? "••••••••••••••••" : "Enter Anthropic API Key"}
                value={anthropicKey}
                onChange={(e) => setAnthropicKey(e.target.value)}
              />
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  updateApiKeys.mutate({ anthropic_api_key: anthropicKey })
                  setAnthropicKey('')
                }}
                disabled={!anthropicKey || updateApiKeys.isPending}
              >
                Save
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleTestApi('anthropic')}
                disabled={testingApi === 'anthropic' || !settings?.has_anthropic_key}
              >
                {testingApi === 'anthropic' ? '...' : 'Test'}
              </Button>
            </div>
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
