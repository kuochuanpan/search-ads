# Search-ADS

A CLI tool for automating scientific paper citations in LaTeX documents using NASA ADS (Astrophysics Data System).

## Features

- **Search for papers** using NASA ADS API with LLM-powered context analysis
- **Semantic search** over your local paper database using vector embeddings (ChromaDB)
- **Automatically fill** empty `\cite{}`, `\citep{}`, `\citet{}` in LaTeX files
- **Build and maintain** a local paper database with SQLite
- **Expand citation graphs** by fetching references and citations
- **PDF support** - download, parse, and search through paper PDFs
- **LLM ranking** - intelligently rank papers by relevance to your context
- **Generate BibTeX entries** automatically

## Installation

### From source

```bash
git clone https://github.com/your-username/search-ads.git
cd search-ads
pip install -e .
```

### Dependencies

All dependencies are managed via `pyproject.toml`. Key dependencies include:

- `typer` & `rich` - CLI interface
- `sqlmodel` - Database ORM
- `ads` - NASA ADS API client
- `chromadb` - Vector database for semantic search
- `openai` / `anthropic` - LLM APIs for context analysis
- `pymupdf` - PDF parsing

## Configuration

Create a `.env` file in your project root with your API keys:

```env
# Required - NASA ADS API key
ADS_API_KEY=your_ads_api_key_here

# Recommended - For embeddings and LLM analysis
OPENAI_API_KEY=your_openai_api_key_here

# Optional - Alternative LLM backend
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

Get your ADS API key at: https://ui.adsabs.harvard.edu/user/settings/token

## Usage

### Seed the database with papers

```bash
# Seed a single paper by URL or bibcode
search-ads seed "https://ui.adsabs.harvard.edu/abs/2023ApJ...XXX/abstract"
search-ads seed 2023ApJ...XXX

# Seed with automatic expansion (fetch references and citations)
search-ads seed 2023ApJ...XXX --expand --hops 2
```

### Search for papers

```bash
# Search using LLM-powered analysis (recommended)
search-ads find --context "Core-collapse supernovae are the primary mechanism for neutron star formation" --top-k 5

# Search local database only (faster, no ADS API calls)
search-ads find --context "dark matter halo mass function" --local --top-k 5

# Search without LLM analysis (basic keyword matching)
search-ads find --context "gravitational waves" --no-llm --top-k 5
```

### Show paper details

```bash
# Show detailed information about a paper
search-ads show 2023ApJ...XXX

# Fetch from ADS if not in local database
search-ads show 2023ApJ...XXX --fetch
```

### Fill citations in LaTeX

```bash
# Fill a single citation
search-ads fill --bibcode "2023ApJ...XXX" --tex-file paper.tex --line 42 --column 10

# Fill multiple citations
search-ads fill --bibcodes "2023ApJ...XXX,2022MNRAS...YYY" --tex-file paper.tex --line 42 --column 10

# Specify a custom bib file
search-ads fill --bibcode "2023ApJ...XXX" --tex-file paper.tex --bib-file refs.bib --line 42 --column 10
```

### Database management

```bash
# View overall status (database + API usage)
search-ads status

# List papers in database
search-ads list-papers --limit 20

# Embed all papers for semantic search
search-ads db embed

# Show database statistics
search-ads db status
```

### PDF features

```bash
# Download a paper's PDF
search-ads pdf download <bibcode>

# Embed PDF for full-text search
search-ads pdf embed <bibcode>

# Search through embedded PDFs
search-ads pdf search "query text" --top-k 5

# Show PDF storage status
search-ads pdf status

# List downloaded PDFs
search-ads pdf list
```

### Project management

```bash
# Initialize a project to organize papers
search-ads project init "my-paper-2024"

# Add paper to project
search-ads project add-paper <bibcode> --project "my-paper-2024"

# List all projects
search-ads project list

# List papers in a project
search-ads project list "my-paper-2024"
```

## Claude Code Integration

This tool includes a Claude Code skill for automated citation workflow. The skill is located at `.claude/skills/search-cite.md`.

To use it globally (in any project):

```bash
# Copy to your global Claude skills directory
cp .claude/skills/search-cite.md ~/.claude/skills/
```

Then Claude Code can help you:

- Find empty citations in LaTeX files
- Search for relevant papers
- Fill citations automatically

## Example Workflow

1. **Seed your database** with papers from your research area:

   ```bash
   search-ads seed 2021Natur.589...29B --expand --hops 1
   ```

2. **Embed papers** for semantic search:

   ```bash
   search-ads db embed
   ```

3. **Find relevant papers** for your LaTeX document:

   ```bash
   search-ads find --context "Core-collapse supernovae are the primary mechanism for neutron star formation" --top-k 5
   ```

4. **Fill the citation** in your LaTeX file:

   ```bash
   search-ads fill --bibcode "2021Natur.589...29B" --tex-file paper.tex --line 15 --column 28
   ```

## Data Storage

By default, data is stored in `~/.search-ads/`:

- `papers.db` - SQLite database with paper metadata
- `chroma/` - Vector embeddings for semantic search
- `pdfs/` - Downloaded PDF files

## License

MIT
