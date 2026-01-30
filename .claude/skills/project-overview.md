---
name: project-overview
description: Overview of the search-ads project architecture and codebase
version: 1.0.0
---

# Search-ADS Project Overview

Search-ADS is an AI-powered reference manager for astronomers and astrophysicists. It helps researchers find, organize, and cite scientific papers using NASA's Astrophysics Data System (ADS) API.

**Version:** 0.7.0-beta
**License:** MIT
**Repository:** github.com/kuochuanpan/search-ads

## Architecture

This is a full-stack Python/TypeScript application with three interfaces:

1. **CLI** (`search-ads`) - Typer-based command-line tool (primary interface)
2. **Web UI** - FastAPI backend + React frontend
3. **Desktop App** - Tauri v2 wrapper around the web UI

### Source Layout

```
src/
  cli/main.py          # All CLI commands (Typer, ~2000 lines)
  core/
    config.py          # Settings (Pydantic), env management
    ads_client.py      # NASA ADS API wrapper
    llm_client.py      # Multi-provider LLM abstraction (OpenAI, Anthropic, Gemini, Ollama)
    latex_parser.py    # LaTeX file parsing and citation filling
    pdf_handler.py     # PDF download (arXiv/ADS) and text extraction
    citation_engine.py # Citation graph analysis
  db/
    models.py          # SQLModel definitions (Paper, Citation, Project, Note, etc.)
    repository.py      # Repository classes (CRUD operations)
    vector_store.py    # ChromaDB vector store for semantic search
  web/
    main.py            # FastAPI app entry point
    dependencies.py    # FastAPI dependency injection
    routers/           # API endpoints (papers, search, projects, pdf, ai, etc.)
    schemas/           # Pydantic request/response models

frontend/              # React 18 + TypeScript + Vite + Tailwind CSS
src-tauri/             # Tauri v2 desktop app (Rust)
scripts/               # Build and utility scripts
tests/                 # Pytest test suite
```

### Data Storage

All user data lives in `~/.search-ads/`:
- `.env` - Configuration (API keys, provider settings)
- `papers.db` - SQLite database (via SQLModel/SQLAlchemy)
- `chroma/` - ChromaDB vector embeddings
- `pdfs/` - Downloaded paper PDFs

### Database Models (src/db/models.py)

- **Paper** (PK: bibcode) - title, abstract, authors (JSON array), year, journal, citation_count, bibtex, pdf_path, is_my_paper
- **Citation** (PK: citing_bibcode + cited_bibcode) - citation relationships
- **Project** (PK: name) - research project groupings
- **PaperProject** - many-to-many Paper-Project association
- **Note** (PK: id, FK: bibcode) - user notes attached to papers
- **ApiUsage** (PK: date) - daily API call tracking
- **Search** - search history cache

### Key Design Patterns

- **Repository Pattern**: `PaperRepository`, `ProjectRepository`, `CitationRepository`, `NoteRepository`, `ApiUsageRepository`
- **Strategy Pattern**: Multiple LLM providers (OpenAI, Anthropic, Gemini, Ollama) via `LLMClient`
- **Lazy Loading**: Vector store and LLM clients initialized on demand
- **Auto-embedding**: Papers automatically embedded in vector store on add (configurable)

### Configuration (src/core/config.py)

`Settings` class uses Pydantic BaseSettings, loads from `~/.search-ads/.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| ADS_API_KEY | NASA ADS API token (required) | - |
| LLM_PROVIDER | openai, anthropic, gemini, ollama | openai |
| EMBEDDING_PROVIDER | openai, gemini, ollama | openai |
| OPENAI_API_KEY | OpenAI API key | - |
| ANTHROPIC_API_KEY | Anthropic API key | - |
| GEMINI_API_KEY | Google Gemini API key | - |
| OPENAI_MODEL | OpenAI model name | gpt-4o-mini |
| ANTHROPIC_MODEL | Anthropic model name | claude-3-haiku-20240307 |
| GEMINI_MODEL | Gemini model name | gemini-1.5-flash |
| OLLAMA_MODEL | Ollama model name | llama3 |
| OLLAMA_EMBEDDING_MODEL | Ollama embedding model | nomic-embed-text |
| OLLAMA_BASE_URL | Ollama server URL | http://localhost:11434 |
| MY_AUTHOR_NAMES | Author name variations (semicolon-separated) | - |
| WEB_HOST | Web server host | 127.0.0.1 |
| WEB_PORT | Web server port | 9527 |

### Dependencies

**Python** (pyproject.toml):
- CLI: typer, rich
- DB: sqlmodel, sqlalchemy (SQLite)
- API: ads, openai, anthropic, google-genai, requests
- Vector: chromadb
- PDF: pymupdf
- Web: fastapi, uvicorn
- Config: pydantic, pydantic-settings, python-dotenv

**Frontend** (frontend/package.json):
- React 18, TypeScript 5.2, Vite 5
- TanStack (Router, Query, Table)
- Zustand, Tailwind CSS, Lucide React
- Tauri v2 APIs

### Build & Run

```bash
# Install CLI (editable for development)
pipx install -e .

# Run CLI
search-ads <command>

# Development (CLI + Web UI)
./launch.sh  # or separately:
search-ads web --reload  # backend
cd frontend && npm run dev  # frontend at localhost:5173

# Tests
pytest tests/

# Desktop build
./scripts/build-sidecar.sh
cargo tauri build
```

### Entry Point

Defined in `pyproject.toml`: `search-ads = "src.cli.main:app"`
