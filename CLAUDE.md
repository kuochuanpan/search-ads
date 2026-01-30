# Search-ADS

AI-powered reference manager for astronomers. CLI + Web UI + Desktop app for finding, organizing, and citing scientific papers via NASA ADS.

## Quick Reference

- **CLI entry point:** `src/cli/main.py` (Typer app, `search-ads` command)
- **Config:** `src/core/config.py` (Pydantic Settings, loads `~/.search-ads/.env`)
- **Database:** `src/db/models.py` (SQLModel) + `src/db/repository.py` (CRUD)
- **Vector search:** `src/db/vector_store.py` (ChromaDB)
- **ADS API:** `src/core/ads_client.py`
- **LLM providers:** `src/core/llm_client.py` (OpenAI, Anthropic, Gemini, Ollama)
- **Web API:** `src/web/main.py` (FastAPI) + `src/web/routers/`
- **Frontend:** `frontend/` (React 18 + TypeScript + Vite + Tailwind)
- **Desktop:** `src-tauri/` (Tauri v2)

## Build & Run

```bash
pipx install -e .              # Install CLI (editable)
search-ads init                # Create ~/.search-ads/.env
search-ads web --reload        # Start backend (dev)
cd frontend && npm run dev     # Start frontend (dev)
pytest tests/                  # Run tests
```

## Code Style

- Python: Black (line-length 100), Ruff, mypy
- Target: Python 3.10+
- Frontend: TypeScript strict, Tailwind CSS

## Key Patterns

- Repository pattern for all DB access
- Multi-provider LLM via strategy pattern
- Auto-embedding papers in ChromaDB on add
- Rich console output in CLI
- NDJSON streaming for long operations in web API
