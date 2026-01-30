import React, { useEffect, useState } from 'react';
import {
  Save,
  RotateCw,
  Trash2,
  Database,
  Server,
  Key,
  FileText,
  User,
  AlertTriangle,
  Cpu,
  CheckCircle,
  XCircle,
  HardDrive,
  Moon,
  Sun,
  Monitor
} from 'lucide-react';
import {
  api,
  ApiUsageResponse,
  SettingsResponse,
  StatsResponse
} from '../lib/api';
import { useTheme } from '../components/ThemeProvider';

export function SettingsPage() {
  const { setTheme, theme } = useTheme();
  const [settings, setSettings] = useState<SettingsResponse | null>(null);
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [apiUsage, setApiUsage] = useState<ApiUsageResponse | null>(null);
  const [vectorStats, setVectorStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Form states
  const [authorNames, setAuthorNames] = useState('');

  // Model settings
  const [llmProvider, setLlmProvider] = useState('openai');
  const [embeddingProvider, setEmbeddingProvider] = useState('openai');
  const [openaiModel, setOpenaiModel] = useState('');
  const [anthropicModel, setAnthropicModel] = useState('');
  const [geminiModel, setGeminiModel] = useState('');
  const [ollamaModel, setOllamaModel] = useState('');
  const [ollamaEmbeddingModel, setOllamaEmbeddingModel] = useState('');
  const [ollamaBaseUrl, setOllamaBaseUrl] = useState('');

  // API Keys
  const [adsKey, setAdsKey] = useState('');
  const [openaiKey, setOpenaiKey] = useState('');
  const [anthropicKey, setAnthropicKey] = useState('');
  const [geminiKey, setGeminiKey] = useState('');

  // Test states
  const [testingKey, setTestingKey] = useState<string | null>(null);
  const [keyStatus, setKeyStatus] = useState<Record<string, { valid: boolean; message: string }>>({});

  // Available models stste
  const [availableModels, setAvailableModels] = useState<Record<string, string[]>>({});

  useEffect(() => {
    fetchData();
  }, []);

  // Fetch available models for a provider
  const fetchModelsForProvider = async (provider: string, key?: string, baseUrl?: string) => {
    // Only attempt fetch if we have a key (or it's local) or we want to rely on backend settings
    // But backend will error if no key, so skipping if empty and not saved is better UX
    if (provider !== 'ollama' && !key && !['openai', 'anthropic', 'gemini'].some(p => (settings as any)?.[`has_${p}_key`])) {
      // No key provided and no key saved
      return;
    }

    try {
      // Don't send masked keys
      const safeKey = key && !key.includes('••••') ? key : undefined;

      const response = await api.getAvailableModels(provider, {
        api_key: safeKey,
        base_url: baseUrl
      });
      setAvailableModels(prev => ({
        ...prev,
        [provider]: response.models
      }));
    } catch (err) {
      console.warn(`Failed to fetch models for ${provider}:`, err);
    }
  };

  const fetchAllModels = async () => {
    fetchModelsForProvider('openai', openaiKey);
    fetchModelsForProvider('anthropic', anthropicKey);
    fetchModelsForProvider('gemini', geminiKey);
    fetchModelsForProvider('ollama', undefined, ollamaBaseUrl);
  };

  const fetchData = async () => {
    setLoading(true);
    try {
      const [settingsData, statsData, usageData, vectorData] = await Promise.all([
        api.getSettings(),
        api.getStats(),
        api.getApiUsage(),
        api.getVectorStats().catch(() => null)
      ]);

      setSettings(settingsData);
      setStats(statsData);
      setApiUsage(usageData);
      setVectorStats(vectorData);

      // Initialize form fields
      setAuthorNames(settingsData.my_author_names || '');

      setLlmProvider(settingsData.llm_provider || 'openai');
      setEmbeddingProvider(settingsData.embedding_provider || 'openai');
      setOpenaiModel(settingsData.openai_model || '');
      setAnthropicModel(settingsData.anthropic_model || '');
      setGeminiModel(settingsData.gemini_model || '');
      setOllamaModel(settingsData.ollama_model || '');
      setOllamaEmbeddingModel(settingsData.ollama_embedding_model || '');
      setOllamaBaseUrl(settingsData.ollama_base_url || '');

      setAdsKey(settingsData.has_ads_key ? '••••••••' : '');
      setOpenaiKey(settingsData.has_openai_key ? 'sk-••••••••' : '');
      setAnthropicKey(settingsData.has_anthropic_key ? 'sk-ant-••••••••' : '');
      setGeminiKey(settingsData.has_gemini_key ? '••••••••' : '');

      // Trigger model fetch
      setTimeout(() => fetchAllModels(), 100);

    } catch (err) {
      console.error('Failed to fetch settings:', err);
      setMessage({ type: 'error', text: 'Failed to load settings' });
    } finally {
      setLoading(false);
    }
  };

  const handleSaveAuthorNames = async () => {
    setSaving(true);
    setMessage(null);
    try {
      await api.updateAuthorNames(authorNames);
      setMessage({ type: 'success', text: 'Author names updated' });
      fetchData(); // Refresh to see parsed names if needed
    } catch (err) {
      setMessage({ type: 'error', text: 'Failed to update author names' });
    } finally {
      setSaving(false);
    }
  };

  const handleSaveModels = async () => {
    setSaving(true);
    setMessage(null);
    try {
      await api.updateModels({
        llm_provider: llmProvider,
        embedding_provider: embeddingProvider,
        openai_model: openaiModel,
        anthropic_model: anthropicModel,
        gemini_model: geminiModel,
        ollama_model: ollamaModel,
        ollama_embedding_model: ollamaEmbeddingModel,
        ollama_base_url: ollamaBaseUrl
      });
      setMessage({ type: 'success', text: 'Model settings updated' });
      fetchData();
    } catch (err) {
      setMessage({ type: 'error', text: 'Failed to update model settings' });
    } finally {
      setSaving(false);
    }
  };

  const handleSaveApiKeys = async () => {
    setSaving(true);
    setMessage(null);

    // Only send keys if they are not the masked placeholders
    const keysToSend: any = {};
    if (adsKey && !adsKey.includes('••••')) keysToSend.ads_api_key = adsKey;
    if (openaiKey && !openaiKey.includes('••••')) keysToSend.openai_api_key = openaiKey;
    if (anthropicKey && !anthropicKey.includes('••••')) keysToSend.anthropic_api_key = anthropicKey;
    if (geminiKey && !geminiKey.includes('••••')) keysToSend.gemini_api_key = geminiKey;

    try {
      await api.updateApiKeys(keysToSend);
      setMessage({ type: 'success', text: 'API keys updated' });
      fetchData();
    } catch (err) {
      setMessage({ type: 'error', text: 'Failed to update API keys' });
    } finally {
      setSaving(false);
    }
  };

  const handleTestKey = async (service: 'ads' | 'openai' | 'anthropic' | 'gemini' | 'ollama') => {
    setTestingKey(service);
    try {
      const result = await api.testApiKey(service);
      setKeyStatus(prev => ({
        ...prev,
        [service]: result
      }));
    } catch (err: any) {
      setKeyStatus(prev => ({
        ...prev,
        [service]: { valid: false, message: err.message || 'Test failed' }
      }));
    } finally {
      setTestingKey(null);
    }
  };

  const handleClearData = async () => {
    if (!window.confirm('Are you SURE you want to delete ALL data? This cannot be undone!')) {
      return;
    }

    setSaving(true);
    try {
      await api.clearAllData();
      setMessage({ type: 'success', text: 'All data cleared successfully' });
      fetchData();
    } catch (err) {
      setMessage({ type: 'error', text: 'Failed to clear data' });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12">
        <RotateCw className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-8 dark:text-gray-100">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold flex items-center gap-3">
          <SettingsIcon className="w-8 h-8 text-gray-700 dark:text-gray-300" />
          Settings
        </h1>
        {settings && (
          <div className="text-sm text-gray-500 dark:text-gray-400">
            Version {settings.version} • Host: {settings.web_host}:{settings.web_port}
          </div>
        )}
      </div>

      {message && (
        <div className={`p-4 rounded-lg flex items-center gap-2 ${message.type === 'success'
          ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300'
          : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300'
          }`}>
          {message.type === 'success' ? <CheckCircle className="w-5 h-5" /> : <AlertTriangle className="w-5 h-5" />}
          {message.text}
        </div>
      )}

      {/* Appearance Section */}
      <section className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border dark:border-gray-700 p-6 space-y-4">
        <h2 className="text-xl font-semibold flex items-center gap-2 text-gray-800 dark:text-gray-100">
          <Monitor className="w-5 h-5 text-gray-500" />
          Appearance
        </h2>
        <div className="flex items-center gap-4">
          <button
            onClick={() => setTheme("light")}
            className={`flex flex-col items-center gap-2 p-3 rounded-lg border-2 transition-all ${theme === 'light' ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' : 'border-transparent hover:bg-gray-100 dark:hover:bg-gray-700'
              }`}
          >
            <Sun className={`w-6 h-6 ${theme === 'light' ? 'text-blue-500' : 'text-gray-500'}`} />
            <span className="text-sm font-medium">Light</span>
          </button>
          <button
            onClick={() => setTheme("dark")}
            className={`flex flex-col items-center gap-2 p-3 rounded-lg border-2 transition-all ${theme === 'dark' ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' : 'border-transparent hover:bg-gray-100 dark:hover:bg-gray-700'
              }`}
          >
            <Moon className={`w-6 h-6 ${theme === 'dark' ? 'text-blue-500' : 'text-gray-500'}`} />
            <span className="text-sm font-medium">Dark</span>
          </button>
          <button
            onClick={() => setTheme("system")}
            className={`flex flex-col items-center gap-2 p-3 rounded-lg border-2 transition-all ${theme === 'system' ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' : 'border-transparent hover:bg-gray-100 dark:hover:bg-gray-700'
              }`}
          >
            <Monitor className={`w-6 h-6 ${theme === 'system' ? 'text-blue-500' : 'text-gray-500'}`} />
            <span className="text-sm font-medium">System</span>
          </button>
        </div>
      </section>

      {/* API Keys Section */}
      <section className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border dark:border-gray-700 p-6 space-y-4">
        <h2 className="text-xl font-semibold flex items-center gap-2 text-gray-800 dark:text-gray-100">
          <Key className="w-5 h-5 text-purple-500" />
          API Keys
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <ApiKeyInput
            label="ADS API Key"
            value={adsKey}
            onChange={setAdsKey}
            onTest={() => handleTestKey('ads')}
            testing={testingKey === 'ads'}
            status={keyStatus['ads']}
            placeholder="Required for paper search"
          />
          <ApiKeyInput
            label="OpenAI API Key"
            value={openaiKey}
            onChange={setOpenaiKey}
            onTest={() => handleTestKey('openai')}
            testing={testingKey === 'openai'}
            status={keyStatus['openai']}
            placeholder="Optional (for AI features)"
          />
          <ApiKeyInput
            label="Anthropic API Key"
            value={anthropicKey}
            onChange={setAnthropicKey}
            onTest={() => handleTestKey('anthropic')}
            testing={testingKey === 'anthropic'}
            status={keyStatus['anthropic']}
            placeholder="Optional (for Claude models)"
          />
          <ApiKeyInput
            label="Gemini API Key"
            value={geminiKey}
            onChange={setGeminiKey}
            onTest={() => handleTestKey('gemini')}
            testing={testingKey === 'gemini'}
            status={keyStatus['gemini']}
            placeholder="Optional (for Gemini models)"
          />
        </div>
        <div className="flex justify-end pt-2">
          <Button onClick={handleSaveApiKeys} disabled={saving}>
            Save API Keys
          </Button>
        </div>
      </section>

      {/* Model Selection Section */}
      <section className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border dark:border-gray-700 p-6 space-y-4">
        <h2 className="text-xl font-semibold flex items-center gap-2 text-gray-800 dark:text-gray-100">
          <Cpu className="w-5 h-5 text-blue-500" />
          AI Providers & Models
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Left Column: Provider Selection */}
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                LLM Provider (Chat & Ranking)
              </label>
              <select
                value={llmProvider}
                onChange={(e) => setLlmProvider(e.target.value)}
                className="w-full p-2 border rounded-md bg-white dark:bg-gray-700 dark:border-gray-600 focus:ring-2 focus:ring-blue-500 dark:text-white"
              >
                <option value="openai">OpenAI (GPT)</option>
                <option value="anthropic">Anthropic (Claude)</option>
                <option value="gemini">Google (Gemini)</option>
                <option value="ollama">Ollama (Local)</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Embedding Provider (Vector Search)
              </label>
              <select
                value={embeddingProvider}
                onChange={(e) => setEmbeddingProvider(e.target.value)}
                className="w-full p-2 border rounded-md bg-white dark:bg-gray-700 dark:border-gray-600 focus:ring-2 focus:ring-blue-500 dark:text-white"
              >
                <option value="openai">OpenAI</option>
                <option value="gemini">Google (Gemini)</option>
                <option value="ollama">Ollama (Local)</option>
              </select>
              <p className="text-xs text-amber-600 dark:text-amber-400 mt-1 flex items-start gap-1">
                <AlertTriangle className="w-3 h-3 mt-0.5 shrink-0" />
                Changing this will trigger a full database re-indexing.
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Ollama Base URL
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={ollamaBaseUrl}
                  onChange={(e) => setOllamaBaseUrl(e.target.value)}
                  className="w-full p-2 border rounded-md dark:bg-gray-700 dark:border-gray-600 focus:ring-2 focus:ring-blue-500 dark:text-white"
                  placeholder="http://localhost:11434"
                />
                <button
                  onClick={() => handleTestKey('ollama')}
                  disabled={testingKey === 'ollama'}
                  className="px-3 py-2 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 dark:border-gray-600 rounded-md text-sm border dark:text-gray-300"
                >
                  {testingKey === 'ollama' ? <RotateCw className="w-4 h-4 animate-spin" /> : 'Test'}
                </button>
              </div>
              {keyStatus['ollama'] && (
                <p className={`text-xs mt-1 ${keyStatus['ollama'].valid ? 'text-green-600 dark:text-green-400' : 'text-red-500 dark:text-red-400'}`}>
                  {keyStatus['ollama'].message}
                </p>
              )}
            </div>
          </div>

          {/* Right Column: Model Names */}
          <div className="space-y-4">
            <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Model Names</h3>
            <Input
              label="OpenAI Model"
              value={openaiModel}
              onChange={setOpenaiModel}
              placeholder="gpt-4o-mini"
              suggestions={availableModels['openai']}
              onFocus={() => fetchModelsForProvider('openai', openaiKey)}
            />
            <Input
              label="Anthropic Model"
              value={anthropicModel}
              onChange={setAnthropicModel}
              placeholder="claude-3-haiku-20240307"
              suggestions={availableModels['anthropic']}
              onFocus={() => fetchModelsForProvider('anthropic', anthropicKey)}
            />
            <Input
              label="Gemini Model"
              value={geminiModel}
              onChange={setGeminiModel}
              placeholder="gemini-1.5-flash"
              suggestions={availableModels['gemini']}
              onFocus={() => fetchModelsForProvider('gemini', geminiKey)}
            />
            <div className="grid grid-cols-2 gap-2">
              <Input
                label="Ollama Chat Model"
                value={ollamaModel}
                onChange={setOllamaModel}
                placeholder="llama3"
                suggestions={availableModels['ollama']}
              />
              <Input
                label="Ollama Embedding"
                value={ollamaEmbeddingModel}
                onChange={setOllamaEmbeddingModel}
                placeholder="nomic-embed-text"
                suggestions={availableModels['ollama']}
              />
            </div>
            <div className="flex justify-end pt-2">
              <button
                onClick={() => fetchAllModels()}
                className="text-xs text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 underline"
                disabled={loading}
              >
                Refresh Available Models
              </button>
            </div>
          </div>
        </div>

        <div className="flex justify-end pt-2">
          <Button onClick={handleSaveModels} disabled={saving}>
            Save Configuration
          </Button>
        </div>
      </section>

      {/* My Papers Section */}
      <section className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border dark:border-gray-700 p-6 space-y-4">
        <h2 className="text-xl font-semibold flex items-center gap-2 text-gray-800 dark:text-gray-100">
          <User className="w-5 h-5 text-green-500" />
          My Papers Configuration
        </h2>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Enter your name variations (semicolon separated) to automatically identity your papers.
        </p>
        <div>
          <input
            type="text"
            value={authorNames}
            onChange={(e) => setAuthorNames(e.target.value)}
            className="w-full p-2 border rounded-md dark:bg-gray-700 dark:border-gray-600 focus:ring-2 focus:ring-blue-500 dark:text-white"
            placeholder="Pan, K.-C.; Pan, Kuo-Chuan"
          />
        </div>
        <div className="flex justify-end">
          <Button onClick={handleSaveAuthorNames} disabled={saving}>
            Update Author Names
          </Button>
        </div>
      </section>

      {/* Info Section (Stats & Paths) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Database Stats */}
        <section className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border dark:border-gray-700 p-6 space-y-4">
          <h2 className="text-xl font-semibold flex items-center gap-2 text-gray-800 dark:text-gray-100">
            <Database className="w-5 h-5 text-indigo-500" />
            Database Stats
          </h2>
          {stats && (
            <div className="space-y-2 text-sm">
              <StatRow label="Total Papers" value={stats.total_papers} />
              <StatRow label="Projects" value={stats.total_projects} />
              <StatRow label="Notes" value={stats.total_notes} />
              <StatRow label="PDFs Stored" value={stats.papers_with_pdf} />
              <StatRow label="My Papers" value={stats.my_papers_count} />
              <div className="pt-2 border-t dark:border-gray-700 mt-2">
                <div className="font-medium text-gray-700 dark:text-gray-300 mb-2">Vector Store (Embeddings)</div>
                <StatRow label="Abstracts" value={vectorStats?.abstracts_count ?? '-'} />
                <StatRow label="PDF Chunks" value={vectorStats?.pdf_chunks_count ?? '-'} />
                <StatRow label="Notes" value={vectorStats?.notes_count ?? '-'} />
              </div>
            </div>
          )}
        </section>

        {/* System Info & Usage */}
        <section className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border dark:border-gray-700 p-6 space-y-4">
          <h2 className="text-xl font-semibold flex items-center gap-2 text-gray-800 dark:text-gray-100">
            <HardDrive className="w-5 h-5 text-gray-500" />
            System & Usage
          </h2>
          {settings && (
            <div className="space-y-2 text-sm text-gray-600 dark:text-gray-400 break-all">
              <div>
                <span className="font-semibold text-gray-700 dark:text-gray-300">Data Dir:</span> {settings.data_dir}
              </div>
              <div>
                <span className="font-semibold text-gray-700 dark:text-gray-300">PDFs Path:</span> {settings.pdfs_path}
              </div>
              <div className="pt-2 border-t dark:border-gray-700 mt-2">
                <div className="font-medium text-gray-700 dark:text-gray-300 mb-2">Today's API Usage</div>
                <StatRow label="ADS Calls" value={apiUsage?.ads_calls ?? 0} />
                <StatRow label="OpenAI Calls" value={apiUsage?.openai_calls ?? 0} />
                <StatRow label="Anthropic Calls" value={apiUsage?.anthropic_calls ?? 0} />
                <StatRow label="Gemini Calls" value={apiUsage?.gemini_calls ?? 0} />
                <StatRow label="Ollama Calls" value={apiUsage?.ollama_calls ?? 0} />
              </div>
            </div>
          )}
          <div className="pt-4 flex justify-end">
            <button
              onClick={handleClearData}
              disabled={saving}
              className="flex items-center gap-2 px-3 py-2 text-red-600 border border-red-200 dark:border-red-900 rounded-md hover:bg-red-50 dark:hover:bg-red-900/20 text-sm transition-colors"
            >
              <Trash2 className="w-4 h-4" />
              Clear All Data
            </button>
          </div>
        </section>
      </div>
    </div>
  );
}

// Helper Components

function SettingsIcon({ className }: { className?: string }) {
  return <RotateCw className={className} />; // Placeholder
}

function StatRow({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex justify-between items-center py-1 border-b border-gray-50 dark:border-gray-700 last:border-0">
      <span className="text-gray-600 dark:text-gray-400">{label}</span>
      <span className="font-mono font-medium text-gray-900 dark:text-gray-100">{value}</span>
    </div>
  );
}

function Input({ label, value, onChange, placeholder, type = "text", suggestions = [], onFocus }: any) {
  const [showSuggestions, setShowSuggestions] = useState(false);

  // Close suggestions when clicking outside would be handled by onBlur naturally
  // logic to delay hide to allow click
  const handleBlur = () => {
    // Delay hiding to allow click event to fire on the list item
    setTimeout(() => {
      setShowSuggestions(false);
    }, 200);
  };

  const handleFocus = (e: any) => {
    setShowSuggestions(true);
    if (onFocus) onFocus(e);
  };

  const handleSelect = (item: string) => {
    onChange(item);
    setShowSuggestions(false);
  };

  return (
    <div className="relative">
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onFocus={handleFocus}
        onBlur={handleBlur}
        placeholder={placeholder}
        className="w-full p-2 border rounded-md dark:bg-gray-700 dark:border-gray-600 focus:ring-2 focus:ring-blue-500 dark:text-white"
        autoComplete="off"
      />
      {suggestions.length > 0 && showSuggestions && (
        <ul className="absolute z-50 w-full mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-md shadow-lg max-h-60 overflow-y-auto">
          {suggestions.map((s: string) => (
            <li
              key={s}
              className="px-3 py-2 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 text-sm text-gray-700 dark:text-gray-200"
              onClick={() => handleSelect(s)}
            >
              {s}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function ApiKeyInput({ label, value, onChange, onTest, testing, status, placeholder }: any) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{label}</label>
      <div className="flex gap-2">
        <input
          type="password"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="w-full p-2 border rounded-md focus:ring-2 focus:ring-blue-500 font-mono text-sm dark:bg-gray-700 dark:border-gray-600 dark:text-white"
        />
        <button
          onClick={onTest}
          disabled={testing}
          className="px-3 py-2 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 dark:border-gray-600 rounded-md text-sm border font-medium text-gray-600 dark:text-gray-300"
        >
          {testing ? <RotateCw className="w-4 h-4 animate-spin" /> : 'Test'}
        </button>
      </div>
      {status && (
        <div className={`mt-1 text-xs flex items-center gap-1 ${status.valid ? 'text-green-600 dark:text-green-400' : 'text-red-500 dark:text-red-400'}`}>
          {status.valid ? <CheckCircle className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
          {status.message}
        </div>
      )}
    </div>
  );
}

function Button({ children, onClick, disabled, className }: any) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium ${className}`}
    >
      {disabled && <RotateCw className="w-4 h-4 animate-spin" />}
      {children}
    </button>
  );
}
