---
name: development
description: Development workflows, testing, building, and contributing to search-ads
version: 1.0.0
---

# Search-ADS Development Guide

## Development Setup

```bash
cd /Users/pan/codes/search-ads

# Install in editable mode
pipx install -e .

# Initialize config
search-ads init
# Edit ~/.search-ads/.env with your API keys

# Frontend setup
cd frontend && npm install
```

## Running in Development

### CLI only
```bash
search-ads <command>
# Changes to Python files take effect immediately (editable install)
```

### Web UI (backend + frontend)
```bash
# Option 1: Use launch script
./launch.sh

# Option 2: Run separately
search-ads web --reload     # Terminal 1: backend at http://127.0.0.1:9527
cd frontend && npm run dev  # Terminal 2: frontend at http://localhost:5173
```

### Desktop App (Tauri)
```bash
./scripts/build-sidecar.sh  # Build Python backend sidecar
cargo tauri dev              # Run in development
cargo tauri build            # Build for distribution
```

## Testing

```bash
pytest tests/
pytest tests/llm/test_client.py -v
pytest tests/web/ -v
```

Test configuration in `pyproject.toml`:
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
```

## Code Style

Configured in `pyproject.toml`:
- **Formatter:** Black (line-length: 100, target: py310)
- **Linter:** Ruff (line-length: 100, target: py310, rules: E, F, I, N, W)
- **Type Checker:** mypy (python 3.10, ignore_missing_imports)

## Adding a New CLI Command

1. Open `src/cli/main.py`
2. Add function with `@app.command()` decorator (or `@pdf_app.command()`, `@project_app.command()`, `@db_app.command()` for sub-commands)
3. Use `typer.Option()` for flags and `typer.Argument()` for positional args
4. Use `console.print()` with Rich markup for output
5. Call `ensure_data_dirs()` at the start
6. Use repository classes from `src/db/repository.py` for database access

Example pattern:
```python
@app.command()
def my_command(
    identifier: str = typer.Argument(..., help="Paper bibcode"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show details"),
):
    """One-line description shown in help."""
    ensure_data_dirs()
    paper_repo = PaperRepository()
    # ... implementation
    console.print("[green]Done![/green]")
```

## Adding a New Web API Endpoint

1. Create router in `src/web/routers/my_router.py`
2. Import and include in `src/web/main.py`: `app.include_router(my_router.router, prefix="/api/my-route")`
3. Define Pydantic schemas in `src/web/schemas/` if needed
4. Use dependency injection from `src/web/dependencies.py`

## Adding a New LLM Provider

1. Add provider case in `LLMClient` in `src/core/llm_client.py`
2. Add API key field to `Settings` in `src/core/config.py`
3. Add model name field to `Settings`
4. Update `save_models()` and `save_api_keys()` in config
5. Update CLI `config` command in `src/cli/main.py`
6. Update the `.env` template in `src/cli/main.py` (ENV_TEMPLATE)

## Adding Database Fields

1. Add field to model in `src/db/models.py` (uses SQLModel)
2. SQLite schema migration is manual — for development, you may need to delete and recreate the DB
3. Update repository methods in `src/db/repository.py` if needed

## Key Files to Know

| File | Lines | Purpose |
|------|-------|---------|
| `src/cli/main.py` | ~2000 | All CLI commands |
| `src/core/config.py` | ~380 | Settings and configuration |
| `src/core/ads_client.py` | ~480 | NASA ADS API wrapper |
| `src/core/llm_client.py` | ~574 | Multi-provider LLM client |
| `src/core/latex_parser.py` | - | LaTeX parsing and citation filling |
| `src/core/pdf_handler.py` | - | PDF download and text extraction |
| `src/db/models.py` | ~180 | SQLModel database definitions |
| `src/db/repository.py` | ~840 | All database CRUD operations |
| `src/db/vector_store.py` | - | ChromaDB vector search |
| `src/web/main.py` | - | FastAPI application setup |

## Git Workflow

- **Main branch:** `main` (stable)
- **Feature branches:** `feature-*`
- **Current branch:** `feature-llm`

## Environment Variables for Development

Required:
- `ADS_API_KEY` - Get from https://ui.adsabs.harvard.edu/user/settings/token

At least one LLM provider:
- `OPENAI_API_KEY` - For OpenAI (default provider)
- `ANTHROPIC_API_KEY` - For Claude
- `GEMINI_API_KEY` - For Gemini
- Or Ollama running locally (no key needed)
