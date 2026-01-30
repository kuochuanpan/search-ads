---
name: cli-commands
description: Complete reference for all search-ads CLI commands, options, and usage patterns
version: 1.0.0
---

# Search-ADS CLI Command Reference

The CLI is built with Typer (Python) and uses Rich for terminal output. All commands are defined in `src/cli/main.py`. Entry point: `search-ads = "src.cli.main:app"` (pyproject.toml).

## Top-Level Commands

### `search-ads init`
Initialize configuration. Creates `~/.search-ads/` directory and `.env` template.

```bash
search-ads init
search-ads init --force  # Overwrite existing .env
```

### `search-ads config`
View or update configuration (LLM providers, API keys, embedding providers).

```bash
search-ads config                              # Show current config
search-ads config --llm-provider anthropic     # Set LLM provider
search-ads config --embedding-provider ollama  # Set embedding provider
search-ads config --openai-key "sk-..."        # Set OpenAI key
search-ads config --anthropic-key "sk-..."     # Set Anthropic key
search-ads config --gemini-key "..."           # Set Gemini key
search-ads config --ads-key "..."              # Set ADS key
search-ads config --ollama-url "http://..."    # Set Ollama URL
```

### `search-ads seed`
Add a paper from ADS to the local database.

```bash
search-ads seed <bibcode-or-url>
search-ads seed 2021Natur.589...29B
search-ads seed "https://ui.adsabs.harvard.edu/abs/2021Natur.589...29B"
search-ads seed <bibcode> --expand --hops 2     # Fetch refs & citations
search-ads seed <bibcode> --project "my-paper"  # Add to specific project
```

**Options:**
- `--expand / -e` - Also fetch references and citations
- `--hops / -h` (default: 1) - Number of expansion hops
- `--project / -p` - Add to a specific project (creates if needed)

### `search-ads expand`
Expand citation graph for a paper or all papers.

```bash
search-ads expand <bibcode>
search-ads expand --all                # Expand all papers in database
search-ads expand <bibcode> --hops 2   # Multiple hops
search-ads expand --min-citations 10   # Filter by citation count
```

### `search-ads find`
Search for papers using LLM-powered analysis and ranking. **Primary search command.**

```bash
search-ads find --context "Core-collapse supernovae neutron star formation"
search-ads find -c "dark matter" --top-k 10
search-ads find -c "AGN feedback" --local          # Local DB only (no ADS API)
search-ads find -c "galaxy formation" --no-llm     # Basic keyword matching
search-ads find -c "stellar evolution" --author "Pan"
search-ads find -c "black holes" --year 2020
search-ads find -c "cosmology" --year 2018-2022
search-ads find -c "text with \\cite{,}" --num-refs 2  # Multiple refs needed
search-ads find --author "Pan"                      # Search by author only
search-ads find --author "Pan" --year 2020-2024     # Author + year, no context
```

**Options:**
- `--context / -c` - Text context for the citation (required unless `--author` or `--year` is provided)
- `--author / -a` - Filter by author name
- `--year / -y` - Filter by year (single: `2020`, range: `2018-2022`)
- `--max-hops` (default: 2) - Maximum hops for graph expansion
- `--top-k / -k` (default: 5) - Number of results
- `--no-llm` - Disable LLM analysis/ranking
- `--local / -l` - Search local DB only (no ADS API calls)
- `--num-refs / -n` (default: 1) - Number of references needed

**Search Pipeline:**
1. LLM analyzes context -> extracts topic, keywords, search query
2. Searches ADS or local DB (vector similarity + text search)
3. LLM ranks results by relevance
4. Displays papers with relevance scores and explanations

### `search-ads fill`
Fill an empty LaTeX citation with paper reference(s).

```bash
search-ads fill --bibcode "2023ApJ...XXX" --tex-file paper.tex --line 15 --column 28
search-ads fill --bibcodes "bib1,bib2" --tex-file paper.tex --line 15 --column 28
search-ads fill --bibcode "2023ApJ...XXX" -t paper.tex -l 15 -c 28 --bib-file refs.bib
```

**Options:**
- `--bibcode / -b` - Single paper bibcode
- `--bibcodes` - Comma-separated bibcodes for multiple references
- `--tex-file / -t` (required) - LaTeX file to modify
- `--bib-file` - BibTeX file (auto-detected if not specified)
- `--line / -l` (required) - Line number of the citation
- `--column / -c` (required) - Column position of the citation

### `search-ads get`
Get citation info (BibTeX, AASTeX bibitem, cite key) for a paper.

```bash
search-ads get <bibcode>
search-ads get <bibcode> --format bibtex
search-ads get <bibcode> --format bibitem
search-ads get <bibcode> --fetch  # Fetch from ADS if not in local DB
```

### `search-ads show`
Display detailed paper information.

```bash
search-ads show <bibcode>
search-ads show <bibcode> --fetch         # Fetch from ADS if missing
search-ads show <bibcode> --refs          # Show papers cited by this paper
search-ads show <bibcode> --citations     # Show papers citing this paper
search-ads show <bibcode> --refs --limit 50
```

### `search-ads status`
Show database and API usage stats.

```bash
search-ads status
```

### `search-ads list-papers`
List papers in the database.

```bash
search-ads list-papers
search-ads list-papers --limit 50
search-ads list-papers --project "my-paper"
```

### `search-ads import`
Import papers from a BibTeX file.

```bash
search-ads import --bib-file refs.bib
search-ads import --bib-file refs.bib --project "imported"
```

### `search-ads mine`
Mark/list papers authored by the user.

```bash
search-ads mine <bibcode>           # Mark as my paper
search-ads mine <bibcode> --unmark  # Unmark
search-ads mine --list              # List all my papers
```

### `search-ads note`
Manage paper notes.

```bash
search-ads note <bibcode>                          # View note
search-ads note <bibcode> --add "Important paper"  # Add/append note
search-ads note <bibcode> --delete                 # Delete note
```

### `search-ads web`
Start the web UI server.

```bash
search-ads web                    # Default: 127.0.0.1:9527
search-ads web --port 8080
search-ads web --host 0.0.0.0
search-ads web --reload           # Auto-reload for development
```

## Sub-Commands: `search-ads db`

### `search-ads db embed`
Create vector embeddings for semantic search.

```bash
search-ads db embed
search-ads db embed --force  # Re-embed all (even if already embedded)
```

### `search-ads db update`
Batch update citation counts from ADS.

```bash
search-ads db update
search-ads db update --project "my-paper"
search-ads db update --older-than 30        # Only papers not updated in 30 days
search-ads db update --batch-size 25
```

### `search-ads db clear`
Clear all papers from the database.

```bash
search-ads db clear
search-ads db clear --force  # Skip confirmation
```

### `search-ads db status`
Show database and vector store statistics.

```bash
search-ads db status
```

## Sub-Commands: `search-ads pdf`

### `search-ads pdf download`
Download paper PDF from arXiv or ADS.

```bash
search-ads pdf download <bibcode>
search-ads pdf download <bibcode> --force  # Re-download
```

### `search-ads pdf embed`
Embed PDF content for full-text search.

```bash
search-ads pdf embed <bibcode>
search-ads pdf embed <bibcode> --force  # Re-embed
```

### `search-ads pdf search`
Search through embedded PDF content.

```bash
search-ads pdf search "query text"
search-ads pdf search "query" --bibcode <bibcode>  # Limit to specific paper
search-ads pdf search "query" --top-k 10
```

### `search-ads pdf status`
Show PDF download and embedding stats.

```bash
search-ads pdf status
```

### `search-ads pdf list`
List all downloaded PDFs.

```bash
search-ads pdf list
```

## Sub-Commands: `search-ads project`

### `search-ads project init`
Create a new project.

```bash
search-ads project init "my-paper-2024"
```

### `search-ads project list`
List all projects or papers in a project.

```bash
search-ads project list                    # List all projects
search-ads project list "my-paper-2024"    # List papers in project
```

### `search-ads project add-paper`
Add a paper to a project.

```bash
search-ads project add-paper <bibcode> --project "my-paper-2024"
```

### `search-ads project delete`
Delete a project.

```bash
search-ads project delete "my-paper-2024"
search-ads project delete "my-paper-2024" --delete-papers  # Also delete papers
search-ads project delete "my-paper-2024" --force          # Skip confirmation
```

## Common Workflow Examples

### Build a paper library from scratch
```bash
search-ads init
# Edit ~/.search-ads/.env with API keys
search-ads seed 2021Natur.589...29B --expand --hops 1
search-ads db embed
search-ads find -c "core-collapse supernovae" --local
```

### Fill citations in LaTeX
```bash
search-ads find -c "Core-collapse supernovae are the primary mechanism..."
# User picks bibcode from results
search-ads fill -b "2021Natur.589...29B" -t paper.tex -l 15 -c 28
```

### Get citation info
```bash
search-ads get 2021ApJ...914..140P --format bibtex
search-ads get 2021ApJ...914..140P --format bibitem
```
