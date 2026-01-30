---
name: search-cite
description: Search for scientific paper citations using NASA ADS and fill empty \cite{} in LaTeX
version: 1.0.0
---

# Search Citation Skill

This skill helps find and fill scientific paper citations in LaTeX documents using NASA ADS (Astrophysics Data System).

## When to Use

Use this skill when the user:
- Asks to fill empty citations in a LaTeX file (`\cite{}`, `\citep{}`, `\citet{}`)
- Needs to find papers related to a scientific topic
- Wants to add references to a LaTeX document
- Asks about papers in their local citation database

## Workflow

### 1. Finding Empty Citations

When working with a LaTeX file, first identify empty citations:

```bash
# The tool can parse LaTeX files to find empty citations
# Look for patterns like \cite{}, \citep{}, \citet{}, \cite{key1, }
```

### 2. Searching for Papers

Search for relevant papers using the context around the citation:

```bash
# Search using LLM-powered analysis (recommended)
search-ads find --context "THE_SURROUNDING_TEXT" --top-k 5

# Search local database only (faster, no API calls)
search-ads find --context "THE_SURROUNDING_TEXT" --local --top-k 5

# Search without LLM analysis (basic keyword matching)
search-ads find --context "THE_SURROUNDING_TEXT" --no-llm --top-k 5
```

The `find` command will:
1. Analyze the context to understand what type of citation is needed
2. Extract relevant keywords for searching
3. Search ADS or local database for matching papers
4. Rank results by relevance using LLM
5. Display papers with title, authors, year, abstract, and relevance explanation

### 3. Showing Paper Details

To see full details of a specific paper:

```bash
search-ads show <bibcode>

# Fetch from ADS if not in local database
search-ads show <bibcode> --fetch
```

### 4. Filling Citations

After the user selects a paper, fill the citation:

```bash
# Single reference
search-ads fill --bibcode "2023ApJ...XXX" --tex-file "paper.tex" --line LINE --column COL

# Multiple references (for \cite{,} patterns)
search-ads fill --bibcodes "2023ApJ...XXX,2022MNRAS...YYY" --tex-file "paper.tex" --line LINE --column COL

# With explicit bib file
search-ads fill --bibcode "2023ApJ...XXX" --tex-file "paper.tex" --bib-file "refs.bib" --line LINE --column COL
```

The tool automatically:
- Detects if the project uses `.bib` files or `\bibitem`
- Adds BibTeX entries to the bibliography file
- Generates appropriate citation keys (e.g., `smith2024`)
- Fills the citation in the LaTeX file

## Database Management

### Adding Papers

```bash
# Seed a paper from ADS URL or bibcode
search-ads seed "https://ui.adsabs.harvard.edu/abs/2023ApJ...XXX/abstract"
search-ads seed 2023ApJ...XXX

# Seed with automatic expansion (fetch references and citations)
search-ads seed 2023ApJ...XXX --expand --hops 1
```

### Checking Status

```bash
# Show database and API usage status
search-ads status

# Show detailed database stats
search-ads db status
```

### Listing Papers

```bash
# List papers in database
search-ads list-papers --limit 20

# Filter by project
search-ads list-papers --project "my-paper"
```

## PDF Features

For full-text search through paper PDFs:

```bash
# Download a paper's PDF
search-ads pdf download <bibcode>

# Embed PDF for full-text search
search-ads pdf embed <bibcode>

# Search through embedded PDFs
search-ads pdf search "query text"

# Show PDF status
search-ads pdf status
```

## Project Management

Organize papers by project:

```bash
# Initialize a project
search-ads project init "my-paper-2024"

# Add paper to project
search-ads project add-paper <bibcode> --project "my-paper-2024"

# List projects
search-ads project list

# List papers in a project
search-ads project list "my-paper-2024"
```

## Example Session

User has a LaTeX file with empty citations:

```latex
Core-collapse supernovae \cite{} are the primary mechanism for neutron star formation.
```

1. **Search for relevant papers:**
```bash
search-ads find --context "Core-collapse supernovae are the primary mechanism for neutron star formation" --top-k 5
```

2. **Review the results** - the tool shows ranked papers with relevance explanations

3. **User selects a paper** (e.g., bibcode `2021Natur.589...29B`)

4. **Fill the citation:**
```bash
search-ads fill --bibcode "2021Natur.589...29B" --tex-file "paper.tex" --line 15 --column 28
```

5. **Result:** The LaTeX file now has `\cite{2021Natur.589...29B}` and the BibTeX entry is added to the bibliography. (Citation keys default to the ADS bibcode format.)

## Search Filters

The `find` command supports additional filters:

```bash
# Filter by author
search-ads find --context "stellar evolution" --author "Pan"

# Filter by year
search-ads find --context "black holes" --year 2020
search-ads find --context "cosmology" --year 2018-2022

# Request multiple references (for \cite{,} patterns)
search-ads find --context "text needing two refs" --num-refs 2
```

## Environment Requirements

The tool requires API keys configured in `~/.search-ads/.env`:
- `ADS_API_KEY`: NASA ADS API token (required for ADS searches)
- `LLM_PROVIDER`: Which LLM to use - openai, anthropic, gemini, or ollama
- `OPENAI_API_KEY`: For OpenAI embeddings and LLM analysis
- `ANTHROPIC_API_KEY`: For Anthropic/Claude LLM backend
- `GEMINI_API_KEY`: For Google Gemini LLM backend

Get an ADS API key at: https://ui.adsabs.harvard.edu/user/settings/token

Use `search-ads config` to view and update settings.

## Tips

- Use `--local` flag for faster searches when you have a well-populated database
- Run `search-ads db embed` to enable semantic search over your paper collection
- The tool learns from your research area as you seed more papers
- For broad introductory statements, the tool prefers review papers
- For specific claims, it finds papers with supporting evidence
- Notes attached to papers (via `search-ads note`) are also searched during `find --local`
