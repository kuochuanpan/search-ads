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

### Get citation information

```bash
# Get citation info for a paper (cite key, bibitem, bibtex)
search-ads get 2023ApJ...XXX

# Get only bibtex entry
search-ads get 2023ApJ...XXX --format bibtex

# Get only bibitem (aastex format)
search-ads get 2023ApJ...XXX --format bibitem

# Fetch from ADS if not in local database
search-ads get 2023ApJ...XXX --fetch
```

The `get` command returns the citation key (bibcode), bibitem in AASTeX format, and BibTeX entry as plain text. This is designed for use with Claude Code - the skill handles inserting citations into your LaTeX files.

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

# Update citation counts (batch update, efficient API usage)
search-ads db update

# Update papers in a specific project
search-ads db update --project "my-paper-2024"

# Update papers not updated in the last N days
search-ads db update --older-than 30
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

Papers can belong to multiple projects (like tags). This allows you to organize your research across different papers and topics.

```bash
# Initialize a project to organize papers
search-ads project init "my-paper-2024"

# Seed papers and add them to a project (including expanded refs/citations)
search-ads seed 2023ApJ...XXX --expand --hops 2 --project "my-paper-2024"

# Add an existing paper to a project
search-ads project add-paper <bibcode> --project "my-paper-2024"

# Add same paper to multiple projects
search-ads project add-paper <bibcode> --project "ccsn"
search-ads project add-paper <bibcode> --project "neutrinos"

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

1. **Create a project** for your paper:

   ```bash
   search-ads project init "my-ccsn-paper"
   ```

2. **Seed your database** with papers from your research area (all refs/citations added to project):

   ```bash
   search-ads seed 2021Natur.589...29B --expand --hops 1 --project "my-ccsn-paper"
   ```

3. **Embed papers** for semantic search:

   ```bash
   search-ads db embed
   ```

4. **Find relevant papers** for your LaTeX document:

   ```bash
   search-ads find --context "Core-collapse supernovae are the primary mechanism for neutron star formation" --top-k 5
   ```

5. **Get citation information** for the paper you want to cite:

   ```bash
   search-ads get 2021Natur.589...29B
   ```

   This outputs the cite key (bibcode), bibitem (aastex format), and bibtex entry as plain text. Use Claude Code skill to insert into your LaTeX file.

6. **Keep database updated** (citation counts change over time):

   ```bash
   search-ads db update --project "my-ccsn-paper"
   ```

## Data Storage

By default, data is stored in `~/.search-ads/`:

- `papers.db` - SQLite database with paper metadata
- `chroma/` - Vector embeddings for semantic search
- `pdfs/` - Downloaded PDF files

## License

MIT
