const API_BASE = '/api'

export interface Paper {
  bibcode: string
  title: string
  abstract?: string
  authors?: string[]
  year?: number
  journal?: string
  volume?: string
  pages?: string
  doi?: string
  arxiv_id?: string
  citation_count?: number
  bibtex?: string
  bibitem_aastex?: string
  pdf_url?: string
  pdf_path?: string
  pdf_embedded: boolean
  is_my_paper: boolean
  created_at: string
  updated_at: string
  has_note: boolean
  projects: string[]
  first_author?: string
}

export interface PaperListResponse {
  papers: Paper[]
  total: number
  limit: number
  offset: number
}

export interface Project {
  name: string
  description?: string
  created_at: string
  paper_count: number
}

export interface ProjectListResponse {
  projects: Project[]
  total: number
}

export interface Note {
  id: number
  bibcode: string
  content: string
  created_at: string
  updated_at: string
}

export interface StatsResponse {
  total_papers: number
  total_projects: number
  total_notes: number
  papers_with_pdf: number
  papers_with_embedded_pdf: number
  my_papers_count: number
  min_year?: number
  max_year?: number
}

export interface ApiUsageResponse {
  date: string
  ads_calls: number
  openai_calls: number
  anthropic_calls: number
}

export interface SettingsResponse {
  data_dir: string
  db_path: string
  pdfs_path: string
  max_hops: number
  top_k: number
  min_citation_count: number
  web_host: string
  web_port: number
  citation_key_format: string
  has_ads_key: boolean
  has_openai_key: boolean
  has_anthropic_key: boolean
  my_author_names: string
}

export interface AuthorNamesResponse {
  author_names: string
  parsed_names: string[]
}

// AI Search types
export interface AIAnalysis {
  topic: string
  claim: string
  citation_type_needed: string
  keywords: string[]
  reasoning: string
}

export interface SearchResultItem {
  bibcode: string
  title: string
  year?: number
  first_author?: string
  authors?: string[]
  abstract?: string
  citation_count?: number
  relevance_score: number
  relevance_explanation: string
  citation_type: string
  in_library: boolean
  has_pdf: boolean
  pdf_embedded: boolean
  source: 'library' | 'ads' | 'pdf'
}

export interface AISearchResponse {
  query: string
  results: SearchResultItem[]
  ai_analysis?: AIAnalysis
  total_count: number
}

export interface AskPaperResponse {
  bibcode: string
  question: string
  answer: string
  sources_used: string[]
}

// LaTeX types
export interface EmptyCitationInfo {
  index: number
  cite_type: string
  context: string
  full_match: string
  line_number: number
  existing_keys: string[]
}

export interface ParseLaTeXResponse {
  empty_citations: EmptyCitationInfo[]
  total_count: number
}

export interface SuggestedPaper {
  bibcode: string
  title: string
  year?: number
  first_author?: string
  authors?: string[]
  abstract?: string
  citation_count?: number
  relevance_score: number
  relevance_explanation: string
  citation_type: string
  bibtex?: string
  bibitem_aastex?: string
  in_library: boolean
}

export interface CitationAnalysis {
  topic: string
  claim: string
  citation_type_needed: string
  keywords: string[]
  reasoning: string
}

export interface CitationSuggestion {
  citation_index: number
  cite_type: string
  context: string
  existing_keys: string[]
  analysis?: CitationAnalysis
  suggestions: SuggestedPaper[]
  error?: string
}

export interface GetSuggestionsResponse {
  suggestions: CitationSuggestion[]
  total_citations: number
}

export interface BibliographyEntry {
  bibcode: string
  cite_key: string
  entry: string
  format: string
}

export interface GenerateBibliographyResponse {
  entries: BibliographyEntry[]
  combined: string
}

// References/Citations types
export interface PaperSummary {
  bibcode: string
  title?: string
  authors?: string
  year?: number
  journal?: string
  citation_count?: number
  in_library: boolean
}

export interface ReferencesResponse {
  bibcode: string
  title?: string
  references: PaperSummary[]
  count: number
  total?: number
  page: number
  has_more: boolean
}

export interface CitationsResponse {
  bibcode: string
  title?: string
  citations: PaperSummary[]
  count: number
  total?: number
  page: number
  has_more: boolean
}

export interface NDJSONStreamResult<T> {
  type: 'progress' | 'result' | 'error' | 'done' | 'log' | 'analysis'
  message?: string
  data?: T
  current?: number
  total?: number
  count?: number
  level?: 'info' | 'warning' | 'error' | 'success'
  imported?: number
  failed?: number
  errors?: string[]
}

// API Client
async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${path}`
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: response.statusText }))
    throw new Error(error.error || error.detail || 'Request failed')
  }

  return response.json()
}

async function* streamRequest<T>(path: string, options: RequestInit = {}): AsyncGenerator<NDJSONStreamResult<T>> {
  const url = `${API_BASE}${path}`
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  })

  if (!response.ok || !response.body) {
    const error = await response.json().catch(() => ({ error: response.statusText }))
    throw new Error(error.error || error.detail || 'Request failed')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      if (!line.trim()) continue
      try {
        yield JSON.parse(line)
      } catch (e) {
        console.warn('Failed to parse NDJSON line:', line)
      }
    }
  }
}

export const api = {
  // Papers
  getPapers: (params?: {
    limit?: number
    offset?: number
    project?: string
    year_min?: number
    year_max?: number
    min_citations?: number
    has_pdf?: boolean
    pdf_embedded?: boolean
    is_my_paper?: boolean
    has_note?: boolean
    search?: string
    sort_by?: 'title' | 'year' | 'citation_count' | 'created_at' | 'updated_at'
    sort_order?: 'asc' | 'desc'
  }) => {
    const searchParams = new URLSearchParams()
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          searchParams.append(key, String(value))
        }
      })
    }
    return request<PaperListResponse>(
      `/papers?${searchParams.toString()}`
    )
  },

  getPaper: (bibcode: string) =>
    request<Paper>(`/papers/${encodeURIComponent(bibcode)}`),

  deletePaper: (bibcode: string) =>
    request<{ message: string; success: boolean }>(
      `/papers/${encodeURIComponent(bibcode)}`,
      { method: 'DELETE' }
    ),

  toggleMyPaper: (bibcode: string, isMyPaper: boolean) =>
    request<{ message: string; success: boolean }>(
      `/papers/${encodeURIComponent(bibcode)}/mine`,
      {
        method: 'PATCH',
        body: JSON.stringify({ is_my_paper: isMyPaper }),
      }
    ),

  bulkDeletePapers: (bibcodes: string[]) =>
    request<{ success: boolean; processed: number; failed: number; errors: string[] }>(
      '/papers/bulk/delete',
      {
        method: 'POST',
        body: JSON.stringify({ bibcodes }),
      }
    ),

  bulkMarkMyPapers: (bibcodes: string[], isMyPaper: boolean) =>
    request<{ success: boolean; processed: number; failed: number; errors: string[] }>(
      `/papers/bulk/mine?is_my_paper=${isMyPaper}`,
      {
        method: 'POST',
        body: JSON.stringify({ bibcodes }),
      }
    ),

  getMyPapers: (limit = 100) =>
    request<PaperListResponse>(`/papers/mine?limit=${limit}`),

  getCitationExport: (bibcode: string) =>
    request<{ bibcode: string; bibtex?: string; bibitem_aastex?: string }>(
      `/papers/${encodeURIComponent(bibcode)}/citations-export`
    ),

  // Projects
  getProjects: () =>
    request<ProjectListResponse>('/projects'),

  getProject: (name: string) =>
    request<Project>(`/projects/${encodeURIComponent(name)}`),

  createProject: (name: string, description?: string) =>
    request<Project>('/projects', {
      method: 'POST',
      body: JSON.stringify({ name, description }),
    }),

  deleteProject: (name: string, deletePapers = false) =>
    request<{ message: string; success: boolean }>(
      `/projects/${encodeURIComponent(name)}?delete_papers=${deletePapers}`,
      { method: 'DELETE' }
    ),

  addPaperToProject: (projectName: string, bibcode: string) =>
    request<{ message: string; success: boolean }>(
      `/projects/${encodeURIComponent(projectName)}/papers`,
      {
        method: 'POST',
        body: JSON.stringify({ bibcode }),
      }
    ),

  addPapersToProject: (projectName: string, bibcodes: string[]) =>
    request<{ message: string; success: boolean }>(
      `/projects/${encodeURIComponent(projectName)}/papers/bulk`,
      {
        method: 'POST',
        body: JSON.stringify({ bibcodes }),
      }
    ),

  getProjectPapers: (name: string) =>
    request<{ project: string; bibcodes: string[]; count: number }>(
      `/projects/${encodeURIComponent(name)}/papers`
    ),

  // Notes
  getNotes: (limit = 100) =>
    request<{ notes: Note[]; total: number }>(`/notes/?limit=${limit}`),

  getNote: (bibcode: string) =>
    request<Note | null>(`/notes/${encodeURIComponent(bibcode)}`),

  createOrUpdateNote: (bibcode: string, content: string, replace = true) =>
    request<Note>(`/notes/${encodeURIComponent(bibcode)}?replace=${replace}`, {
      method: 'PUT',
      body: JSON.stringify({ content }),
    }),

  deleteNote: (bibcode: string) =>
    request<{ message: string; success: boolean }>(
      `/notes/${encodeURIComponent(bibcode)}`,
      { method: 'DELETE' }
    ),

  searchNotes: (query: string, limit = 20) =>
    request<{ query: string; notes: Note[]; count: number }>(
      `/notes/search/text?query=${encodeURIComponent(query)}&limit=${limit}`
    ),

  // Citations
  getReferences: (bibcode: string, options?: {
    fetch_from_ads?: boolean
    limit?: number
    page?: number
    save?: boolean
  }) => {
    const params = new URLSearchParams()
    if (options?.fetch_from_ads) params.append('fetch_from_ads', 'true')
    if (options?.limit) params.append('limit', String(options.limit))
    if (options?.page) params.append('page', String(options.page))
    if (options?.save) params.append('save', 'true')
    const query = params.toString()
    return request<ReferencesResponse>(
      `/citations/${encodeURIComponent(bibcode)}/references${query ? `?${query}` : ''}`
    )
  },

  getCitations: (bibcode: string, options?: {
    fetch_from_ads?: boolean
    limit?: number
    page?: number
    save?: boolean
  }) => {
    const params = new URLSearchParams()
    if (options?.fetch_from_ads) params.append('fetch_from_ads', 'true')
    if (options?.limit) params.append('limit', String(options.limit))
    if (options?.page) params.append('page', String(options.page))
    if (options?.save) params.append('save', 'true')
    const query = params.toString()
    return request<CitationsResponse>(
      `/citations/${encodeURIComponent(bibcode)}/citations${query ? `?${query}` : ''}`
    )
  },

  // Search
  searchLocal: (query: string, limit = 20) =>
    request<{ query: string; results: Array<any>; count: number }>('/search/local', {
      method: 'POST',
      body: JSON.stringify({ query, limit }),
    }),

  searchSemantic: (
    query: string,
    limit = 20,
    minYear?: number,
    minCitations?: number
  ) => {
    const params = new URLSearchParams()
    params.append('limit', String(limit))
    if (minYear !== undefined) params.append('min_year', String(minYear))
    if (minCitations !== undefined) params.append('min_citations', String(minCitations))

    return request<{ query: string; results: Array<any>; count: number }>(
      `/search/semantic?${params.toString()}`,
      {
        method: 'POST',
        body: JSON.stringify({ query }),
      }
    )
  },

  streamSearchSemantic: (
    query: string,
    limit = 20,
    minYear?: number,
    minCitations?: number
  ) => {
    const params = new URLSearchParams()
    params.append('limit', String(limit))
    if (minYear !== undefined) params.append('min_year', String(minYear))
    if (minCitations !== undefined) params.append('min_citations', String(minCitations))

    return streamRequest<SearchResultItem>(
      `/search/semantic/stream?${params.toString()}`,
      {
        method: 'POST',
        body: JSON.stringify({ query }),
      }
    )
  },

  searchPdf: (query: string, limit = 20, bibcode?: string) =>
    request<{ query: string; results: Array<any>; count: number }>(
      `/search/pdf?limit=${limit}${bibcode ? `&bibcode=${encodeURIComponent(bibcode)}` : ''}`,
      {
        method: 'POST',
        body: JSON.stringify({ query, limit }),
      }
    ),

  searchAds: (query: string, limit = 20) =>
    request<{ query: string; results: Array<any>; count: number }>('/search/ads', {
      method: 'POST',
      body: JSON.stringify({ query, limit }),
    }),

  streamSearchAds: (query: string, limit = 20) =>
    streamRequest<SearchResultItem>('/search/ads/stream', {
      method: 'POST',
      body: JSON.stringify({ query, limit }),
    }),

  // Import
  importFromAds: (
    identifier: string,
    options?: {
      project?: string
      expand_references?: boolean
      expand_citations?: boolean
      max_hops?: number
    }
  ) =>
    request<{
      success: boolean
      bibcode?: string
      title?: string
      message: string
      papers_added: number
    }>('/import/ads', {
      method: 'POST',
      body: JSON.stringify({ identifier, ...options }),
    }),

  streamImportFromAds: (
    identifier: string,
    options?: {
      project?: string
      expand_references?: boolean
      expand_citations?: boolean
      max_hops?: number
    }
  ) =>
    streamRequest<{
      success: boolean
      bibcode?: string
      title?: string
      message: string
      papers_added: number
    }>(
      '/import/ads/stream',
      {
        method: 'POST',
        body: JSON.stringify({ identifier, ...options }),
      }
    ),

  batchImport: (identifiers: string[], project?: string) =>
    request<{ success: boolean; imported: number; failed: number; errors: string[] }>(
      '/import/batch',
      {
        method: 'POST',
        body: JSON.stringify({ identifiers, project }),
      }
    ),

  streamBatchImport: (identifiers: string[], project?: string) =>
    streamRequest<{ success: boolean; imported: number; failed: number; errors: string[] }>(
      '/import/batch/stream',
      {
        method: 'POST',
        body: JSON.stringify({ identifiers, project }),
      }
    ),

  importBibtex: (bibtexContent: string, project?: string, fetchFromAds = true) => {
    const formData = new FormData()
    formData.append('bibtex_content', bibtexContent)
    if (project !== undefined) formData.append('project', project)
    formData.append('fetch_from_ads', String(fetchFromAds))

    return request<{ success: boolean; imported: number; failed: number; errors: string[] }>(
      '/import/bibtex',
      {
        method: 'POST',
        body: formData,
        headers: {}, // Let browser set Content-Type for FormData
      }
    )
  },

  // PDF
  getPdfStatus: (bibcode: string) =>
    request<{
      bibcode: string
      has_pdf: boolean
      pdf_path?: string
      pdf_url?: string
      pdf_embedded: boolean
    }>(`/pdf/${encodeURIComponent(bibcode)}/status`),

  downloadPdf: (bibcode: string) =>
    request<{ message: string; success: boolean }>(`/pdf/${encodeURIComponent(bibcode)}/download`, {
      method: 'POST',
    }),

  embedPdf: (bibcode: string) =>
    request<{ message: string; success: boolean }>(`/pdf/${encodeURIComponent(bibcode)}/embed`, {
      method: 'POST',
    }),

  openPdf: (bibcode: string) =>
    request<{ message: string; success: boolean }>(`/pdf/${encodeURIComponent(bibcode)}/open`),

  getPdfStats: () =>
    request<{
      total_papers: number
      papers_with_pdf: number
      papers_with_embedded_pdf: number
      pdf_chunks_count: number
    }>('/pdf/stats'),

  // Settings
  getSettings: () => request<SettingsResponse>('/settings'),

  getStats: () => request<StatsResponse>('/settings/stats'),

  getApiUsage: () => request<ApiUsageResponse>('/settings/api-usage'),

  getVectorStats: () =>
    request<{
      abstracts_count: number
      pdf_chunks_count: number
      pdf_papers_count: number
      notes_count: number
    }>('/settings/vector-stats'),

  testApiKey: (service: 'ads' | 'openai' | 'anthropic') =>
    request<{ valid: boolean; message: string }>(`/settings/test-api-key/${service}`),

  getAuthorNames: () => request<AuthorNamesResponse>('/settings/author-names'),

  updateAuthorNames: (authorNames: string) =>
    request<{ message: string; success: boolean }>('/settings/author-names', {
      method: 'PUT',
      body: JSON.stringify({ author_names: authorNames }),
    }),

  // AI-powered Search
  streamAISearch: (params: {
    query: string
    limit?: number
    search_library?: boolean
    search_ads?: boolean
    search_pdf?: boolean
    min_year?: number
    min_citations?: number
    use_llm?: boolean
  }) =>
    streamRequest<{
      query: string
      results: SearchResultItem[]
      ai_analysis?: {
        topic: string
        claim: string
        citation_type_needed: string
        keywords: string[]
        reasoning: string
      }
      total_count: number
      // Also supports 'analysis' event with just analysis data
      type?: string
      data?: any
    }>('/ai/search/stream', {
      method: 'POST',
      body: JSON.stringify(params),
    }),

  aiSearch: (params: {
    query: string
    limit?: number
    search_library?: boolean
    search_ads?: boolean
    search_pdf?: boolean
    min_year?: number
    min_citations?: number
    use_llm?: boolean
  }) =>
    request<AISearchResponse>('/ai/search', {
      method: 'POST',
      body: JSON.stringify(params),
    }),

  askPaper: (bibcode: string, question: string) =>
    request<AskPaperResponse>('/ai/ask', {
      method: 'POST',
      body: JSON.stringify({ bibcode, question }),
    }),

  // LaTeX parsing and citation suggestions
  parseLaTeX: (latexText: string) =>
    request<ParseLaTeXResponse>('/latex/parse', {
      method: 'POST',
      body: JSON.stringify({ latex_text: latexText }),
    }),

  getCitationSuggestions: (params: {
    latex_text: string
    limit?: number
    use_library?: boolean
    use_ads?: boolean
  }) =>
    request<GetSuggestionsResponse>('/latex/suggest', {
      method: 'POST',
      body: JSON.stringify(params),
    }),

  generateBibliography: (bibcodes: string[], format: 'bibtex' | 'aastex' = 'bibtex') =>
    request<GenerateBibliographyResponse>('/latex/bibliography', {
      method: 'POST',
      body: JSON.stringify({ bibcodes, format }),
    }),
}