# Search-ADS

A CLI tool for automating scientific paper citations in LaTeX documents using NASA ADS (Astrophysics Data System).

## Status

**Version**: 0.1.0 (Alpha)

| Phase | Status |
|-------|--------|
| Phase 1: Core CLI | ✅ Complete |
| Phase 2: Vector Search & LLM Ranking | ✅ Complete |
| Phase 3: PDF Handling | ✅ Complete |
| Phase 4: Web UI | 🔜 Planned |

## Features

- **Search for papers** using NASA ADS API with LLM-powered context analysis
- **Semantic search** over your local paper database using vector embeddings (ChromaDB)
- **Automatically fill** empty `\cite{}`, `\citep{}`, `\citet{}` in LaTeX files
- **Build and maintain** a local paper database with SQLite
- **Expand citation graphs** by fetching references and citations
- **PDF support** - download, parse, and search through paper PDFs
- **LLM ranking** - intelligently rank papers by relevance using Claude or OpenAI
- **Project organization** - tag papers across multiple projects
- **Generate BibTeX and AASTeX bibitem entries** automatically

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    CLI Interface (Typer)                │
│  (seed, find, get, fill, show, db, pdf, project)       │
└─────────────────┬───────────────────────────────────────┘
                  │
        ┌─────────┼──────────┐
        │         │          │
┌───────▼──┐ ┌───▼────┐ ┌──▼──────┐
│  LaTeX   │ │Citation│ │   PDF   │
│  Parser  │ │ Engine │ │ Handler │
└────┬─────┘ └───┬────┘ └──┬──────┘
     │           │         │
     └───────────┼─────────┘
            ┌────▼────────┐
            │ LLM Client  │  (Claude/OpenAI)
            └─────┬───────┘
                  │
        ┌─────────┼──────────┐
        │         │          │
┌───────▼──┐ ┌───▼────────┐ │
│  ADS API │ │ Repository │ │
│  Client  │ │ (CRUD Ops) │ │
└──────────┘ └───┬────────┘ │
                 │          │
          ┌──────▼──────────▼┐
          │  Database Layer  │
          │ SQLite + ChromaDB│
          └──────────────────┘
```

## Installation

### Using pipx (Recommended)

[pipx](https://pipx.pypa.io/) installs CLI tools in isolated environments. This is the recommended way to install search-ads.

```bash
# Install pipx if you don't have it
# macOS
brew install pipx
pipx ensurepath

# Linux/WSL
python3 -m pip install --user pipx
python3 -m pipx ensurepath

# Then install search-ads directly from GitHub
pipx install git+https://github.com/kuochuanpan/search-ads.git
```

To upgrade to the latest version:
```bash
pipx upgrade search-ads
```

To uninstall:
```bash
pipx uninstall search-ads
```

### Using pip

```bash
# Install directly from GitHub
pip install git+https://github.com/kuochuanpan/search-ads.git

# Or clone and install locally
git clone https://github.com/kuochuanpan/search-ads.git
cd search-ads
pip install .
```

### For Development

```bash
git clone https://github.com/kuochuanpan/search-ads.git
cd search-ads
pip install -e ".[dev]"
```

### Dependencies

All dependencies are automatically installed. Key dependencies include:

- `typer` & `rich` - CLI interface
- `sqlmodel` - Database ORM
- `ads` - NASA ADS API client
- `chromadb` - Vector database for semantic search
- `openai` / `anthropic` - LLM APIs for context analysis
- `pymupdf` - PDF parsing

## Configuration

After installation, run the init command to create the configuration file:

```bash
search-ads init
```

This creates `~/.search-ads/.env` with a template. Edit it to add your API keys:

```bash
# Open the config file
nano ~/.search-ads/.env
# or
code ~/.search-ads/.env
```

Required and optional API keys:

```env
# Required - NASA ADS API key
ADS_API_KEY=your_ads_api_key_here

# Recommended - For embeddings and LLM analysis
OPENAI_API_KEY=your_openai_api_key_here

# Optional - Alternative LLM backend (preferred when available)
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional - Auto-detect your papers by author name
MY_AUTHOR_NAMES="LastName, FirstInitial.,LastName, Full Name"
```

Get your API keys:

- **ADS API key**: [ui.adsabs.harvard.edu/user/settings/token](https://ui.adsabs.harvard.edu/user/settings/token)
- **OpenAI API key**: [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
- **Anthropic API key**: [console.anthropic.com](https://console.anthropic.com/)

## Usage

### Seed the database with papers

```bash
# Seed a single paper by URL or bibcode
search-ads seed "https://ui.adsabs.harvard.edu/abs/2023ApJ...XXX/abstract"
search-ads seed 2023ApJ...XXX

# Seed with automatic expansion (fetch references and citations)
search-ads seed 2023ApJ...XXX --expand --hops 2

# Seed and add to a project
search-ads seed 2023ApJ...XXX --expand --project "my-paper-2024"
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

### Fill citations in LaTeX files

```bash
# Fill a citation at a specific location
search-ads fill --tex-file paper.tex --line 42 --column 10 --bibcode 2023ApJ...XXX
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

# Delete a project (papers remain in database)
search-ads project delete "old-project"
```

### Expand citation graph

```bash
# Expand references and citations for a paper
search-ads expand 2023ApJ...XXX --hops 1
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
- Search for relevant papers based on context
- Fill citations automatically
- Manage bibliography entries

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

## Command Reference

| Command | Description |
|---------|-------------|
| `seed <bibcode>` | Add paper to database from ADS |
| `find --context "..."` | Search for papers matching context |
| `get <bibcode>` | Get citation info (key, bibitem, bibtex) |
| `show <bibcode>` | Display paper details |
| `fill` | Fill citation in LaTeX file |
| `expand <bibcode>` | Expand citation graph |
| `status` | Show database and API usage stats |
| `list-papers` | List papers in database |
| `import` | Import from BibTeX file |
| `db embed` | Embed papers for semantic search |
| `db update` | Update citation counts |
| `db status` | Show database statistics |
| `db clear` | Clear database |
| `pdf download` | Download paper PDF |
| `pdf embed` | Embed PDF for search |
| `pdf search` | Search PDF contents |
| `pdf status` | Show PDF storage stats |
| `pdf list` | List downloaded PDFs |
| `project init` | Create a new project |
| `project list` | List projects or papers in project |
| `project add-paper` | Add paper to project |
| `project delete` | Delete a project |

## License

MIT
