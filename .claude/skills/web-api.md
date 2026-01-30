---
name: web-api
description: FastAPI web server endpoints and React frontend architecture for search-ads
version: 1.0.0
---

# Search-ADS Web API & Frontend

The web UI is started via `search-ads web` (FastAPI + uvicorn). The React frontend connects to it.

## Backend: FastAPI

**Entry point:** `src/web/main.py`
**Base URL:** `http://127.0.0.1:9527` (configurable via WEB_HOST/WEB_PORT)
**Interactive docs:** `http://127.0.0.1:9527/docs` (Swagger UI)

### API Endpoints (48 total)

#### Papers (`/api/papers`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | List papers (supports limit, offset, project, year_min, year_max, min_citations, has_pdf, is_my_paper, has_note, search, sort_by, sort_order) |
| GET | `/count` | Count papers |
| GET | `/mine` | List user's papers |
| GET | `/{bibcode}` | Get paper by bibcode |
| DELETE | `/{bibcode}` | Delete paper |
| PATCH | `/{bibcode}/mine` | Toggle my paper status |
| GET | `/{bibcode}/citations-export` | Get citation export (BibTeX/bibitem) |
| POST | `/bulk/delete` | Bulk delete papers |
| POST | `/bulk/mine` | Bulk mark/unmark my papers |

#### Search (`/api/search`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/local` | Text search local database |
| POST | `/semantic` | Vector similarity search |
| POST | `/pdf` | Search PDF content |
| POST | `/ads` | Search NASA ADS |
| POST | `/ads/stream` | Streaming ADS search |
| POST | `/semantic/stream` | Streaming semantic search |

#### AI (`/api/ai`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/search` | AI-powered search (LLM analysis + ranking) |
| POST | `/search/stream` | Streaming AI search |
| POST | `/ask` | Ask LLM a question about a paper |

#### Projects (`/api/projects`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | List all projects |
| POST | `/` | Create project |
| GET | `/{name}` | Get project |
| DELETE | `/{name}` | Delete project |
| POST | `/{name}/papers` | Add paper to project |
| POST | `/{name}/papers/bulk` | Bulk add papers |
| GET | `/{name}/papers` | Get project papers |

#### Citations (`/api/citations`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/{bibcode}/references` | Get references (papers this paper cites) |
| GET | `/{bibcode}/citations` | Get citations (papers citing this paper) |
| GET | `/{bibcode}/has-references` | Check if references exist |
| GET | `/{bibcode}/has-citations` | Check if citations exist |

#### Notes (`/api/notes`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | List all notes |
| GET | `/{bibcode}` | Get note for paper |
| PUT | `/{bibcode}` | Create/update note |
| DELETE | `/{bibcode}` | Delete note |
| GET | `/search/text` | Search notes |

#### Import (`/api/import`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/ads` | Import paper from ADS |
| POST | `/ads/stream` | Streaming import |
| POST | `/batch` | Batch import |
| POST | `/batch/stream` | Streaming batch import |
| POST | `/bibtex` | Import from BibTeX content |

#### PDF (`/api/pdf`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/{bibcode}/status` | PDF status for a paper |
| POST | `/{bibcode}/download` | Download PDF |
| POST | `/{bibcode}/embed` | Embed PDF for search |
| DELETE | `/{bibcode}/embed` | Delete PDF embedding |
| GET | `/{bibcode}/open` | Open/serve PDF file |
| GET | `/stats` | Overall PDF statistics |

#### Settings (`/api/settings`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Get current settings |
| GET | `/author-names` | Get author names |
| PUT | `/author-names` | Update author names |
| PUT | `/models` | Update LLM/embedding models |
| PUT | `/api-keys` | Update API keys |
| GET | `/stats` | Database statistics |
| GET | `/api-usage` | API usage stats |
| GET | `/vector-stats` | Vector store stats |
| POST | `/test-api-key/{service}` | Test an API key |
| POST | `/clear-data` | Clear all data |
| GET | `/models/{provider}` | List available models for provider |

#### LaTeX (`/api/latex`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/parse` | Parse LaTeX text for citations |
| POST | `/suggest` | Get citation suggestions for LaTeX |
| POST | `/bibliography` | Generate bibliography from bibcodes |

### CORS Configuration

Allows:
- `localhost:5173` and `127.0.0.1:5173` (Vite dev server)
- `localhost:3000` and `127.0.0.1:3000`
- `tauri.localhost` (Tauri desktop app)

### Streaming Endpoints

Several endpoints return NDJSON (newline-delimited JSON) for real-time progress updates. Used by the frontend for import progress, search results, etc.

## Frontend: React

**Location:** `frontend/`
**Dev server:** `npm run dev` at `http://localhost:5173`
**Build:** `npm run build` outputs to `frontend/dist/`

### Tech Stack
- React 18, TypeScript 5.2, Vite 5
- TanStack Router (file-based routing)
- TanStack React Query (data fetching/caching)
- TanStack React Table (sortable/filterable tables)
- Zustand (state management)
- Tailwind CSS 3.4 (styling)
- Lucide React (icons)
- Tauri v2 APIs (desktop integration)

### Pages

| Page | Description |
|------|-------------|
| `HomePage` | Dashboard, recent papers, statistics |
| `LibraryPage` | Paper table with sorting/filtering |
| `SearchPage` | AI-powered search interface |
| `WritingPage` | Paste LaTeX, get citation suggestions |
| `ImportPage` | Add papers from ADS URLs, BibTeX, clipboard |
| `PaperDetailPage` | Full paper details, notes, citations |
| `SettingsPage` | API keys, LLM provider configuration |
| `GraphPage` | Citation network visualization |

### Frontend Structure
```
frontend/src/
  pages/       # Page components
  components/  # Reusable UI components
  hooks/       # Custom React hooks (data fetching)
  store/       # Zustand state stores
  lib/         # Utility functions, API client
  index.css    # Global styles (Tailwind)
```

## Development

```bash
# Backend only (with auto-reload)
search-ads web --reload

# Frontend only
cd frontend && npm run dev

# Both together
./launch.sh
```

The backend serves the API on port 9527, the frontend dev server on port 5173 proxies API calls to the backend.
