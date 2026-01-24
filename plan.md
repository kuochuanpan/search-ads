# Project Design: Search-ADS

A CLI tool for automating scientific paper citations in LaTeX documents, integrated with Claude Code via skills.

## Overview

When working on a LaTeX file for scientific papers, users can assign Claude Code to work on a paragraph (or section/subsection):

1. Parse the paragraph and find empty `\cite{}`, `\cite{,}`, `\citep{}`, `\citet{}`, etc.
2. Use an AI/LLM agent to search for related papers via ADS API
3. Build and query a local paper database (for efficiency and reduced token usage)
4. Add references based on the LaTeX setup:
   - If using `.bib` file: add bibtex entry to the bibliography file
   - If no `.bib` file: add `\bibitem` entry at the end of the `.tex` file (before `\end{document}`)
5. Fill in the citation keys automatically
6. Ensure citations are accurate and support the statements

---

## Architecture

```
search-ads/
├── src/
│   ├── cli/                    # CLI tool (Claude Code skill)
│   │   ├── __init__.py
│   │   └── main.py             # Typer CLI entry point
│   │
│   ├── core/                   # Core business logic
│   │   ├── latex_parser.py     # Parse .tex files, find empty citations
│   │   ├── ads_client.py       # ADS API wrapper
│   │   ├── llm_client.py       # OpenAI/Claude API wrapper
│   │   └── citation_engine.py  # Orchestrates search & fill workflow
│   │
│   ├── db/                     # Database layer
│   │   ├── models.py           # Paper, Citation models (SQLModel)
│   │   ├── vector_store.py     # ChromaDB for embeddings
│   │   └── repository.py       # CRUD operations
│   │
│   └── web/                    # Web frontend (Phase 2)
│       ├── app.py              # FastAPI app
│       ├── routes.py
│       └── templates/
│
├── tests/
├── data/                       # Local database files
│   ├── papers.db               # SQLite database
│   ├── chroma/                 # ChromaDB vector store
│   └── pdfs/                   # Downloaded PDFs
│
├── .env                        # API keys (ADS_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY)
├── pyproject.toml
├── shell.nix
└── plan.md
```

---

## Database Design

### Storage: SQLite + ChromaDB

- **SQLite**: Structured data (papers, citations, references)
- **ChromaDB**: Vector embeddings for RAG (abstracts, optionally full PDF text)
- **Single-user**: Local database, no multi-user complexity

### Schema

```sql
-- Papers table
CREATE TABLE papers (
    bibcode TEXT PRIMARY KEY,       -- ADS bibcode (unique identifier)
    title TEXT NOT NULL,
    abstract TEXT,
    authors TEXT,                   -- JSON array of author names
    year INTEGER,
    journal TEXT,
    volume TEXT,
    pages TEXT,
    doi TEXT,
    arxiv_id TEXT,
    citation_count INTEGER,
    bibtex TEXT,                    -- Full bibtex entry
    pdf_url TEXT,                   -- URL to PDF (ADS or arXiv)
    pdf_path TEXT,                  -- Local path if downloaded
    pdf_embedded BOOLEAN DEFAULT 0, -- Whether PDF is embedded in vector store
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Citations graph (paper A cites paper B)
CREATE TABLE citations (
    citing_bibcode TEXT NOT NULL,
    cited_bibcode TEXT NOT NULL,
    context TEXT,                   -- LLM-generated citation reason
    PRIMARY KEY (citing_bibcode, cited_bibcode),
    FOREIGN KEY (citing_bibcode) REFERENCES papers(bibcode),
    FOREIGN KEY (cited_bibcode) REFERENCES papers(bibcode)
);

-- Search history for caching
CREATE TABLE searches (
    id INTEGER PRIMARY KEY,
    query TEXT NOT NULL,
    context TEXT,                   -- LaTeX context that triggered search
    results TEXT,                   -- JSON array of bibcodes
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Vector Store (ChromaDB)

Collections:
- `abstracts`: Paper abstracts embedded for semantic search
- `pdf_contents`: Full PDF text (only for downloaded & embedded papers)

---

## Database Bootstrapping

When the database is empty or small, build it by providing ADS paper links.

### Primary Method: Seed from ADS Links
```bash
# Add a paper and its references/citations
search-ads seed "https://ui.adsabs.harvard.edu/abs/2026ApJ...996...35P/abstract"

# Or use bibcode directly
search-ads seed 2026ApJ...996...35P

# Seed with automatic expansion (fetch refs + citations)
search-ads seed "https://ui.adsabs.harvard.edu/abs/2026ApJ...996...35P" --expand --hops 1
```

The tool will:
1. Parse bibcode from ADS URL
2. Fetch paper metadata from ADS API
3. Optionally fetch all references and citations (with `--expand`)
4. Store everything in the database
5. Embed abstracts for vector search

### Expand Database
```bash
# Expand from a specific paper
search-ads expand "https://ui.adsabs.harvard.edu/abs/2023ApJ...XXX"

# Expand all papers in database by 1 hop
search-ads expand --all --hops 1

# Expand with filters
search-ads expand --all --hops 2 --min-citations 10 --years 2015-2024
```

### Import from BibTeX

```bash
# Import from existing .bib file
search-ads import --bib-file "my_references.bib"

# Import and add to a project
search-ads import --bib-file "my_references.bib" --project "my-paper-2024"
```

### Recommended Bootstrap Workflow
```
1. Seed 3-5 key papers in your field via ADS links
2. Run --expand with 1-2 hops to fetch their references/citations
3. Database grows organically as you use the tool for searches
```

---

## Database Organization (Multi-Project)

### Architecture: Shared Database + Project Tags

Use a **single shared database** with project tagging, not separate databases per project.

```
~/.search-ads/                    # Global data directory
├── papers.db                     # Single SQLite database (all papers)
├── chroma/                       # Shared vector store
└── pdfs/                         # Downloaded PDFs

~/my-paper-project/               # Your LaTeX project
└── .search-ads.yaml              # Project config (links to shared DB)
```

### Why Shared Database?
- **No duplication**: Same paper used in multiple projects is stored once
- **Cross-project discovery**: Papers from one project may be relevant to another
- **Cumulative knowledge**: Database grows over time across all your research
- **Smaller storage**: PDFs and embeddings aren't duplicated

### Project Configuration
Each LaTeX project can have a `.search-ads.yaml` config:

```yaml
# .search-ads.yaml in your project root
project:
  name: "dark-matter-paper-2024"

# Optional: filter searches to project-relevant papers
search:
  prefer_project_papers: true    # Prioritize papers tagged with this project
  include_all_papers: true       # But still search entire database

# Seed papers for this project (run once to bootstrap)
seeds:
  - "https://ui.adsabs.harvard.edu/abs/2026ApJ...996...35P"
  - "https://ui.adsabs.harvard.edu/abs/2023ApJ...XXX"
```

### Database Schema Update
```sql
-- Projects table
CREATE TABLE projects (
    name TEXT PRIMARY KEY,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Paper-Project association (many-to-many)
CREATE TABLE paper_projects (
    bibcode TEXT NOT NULL,
    project_name TEXT NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (bibcode, project_name),
    FOREIGN KEY (bibcode) REFERENCES papers(bibcode),
    FOREIGN KEY (project_name) REFERENCES projects(name)
);
```

### CLI Commands for Projects
```bash
# Initialize project in current directory
search-ads project init "my-paper-2024"

# Seed papers for this project
search-ads seed "https://ui.adsabs.harvard.edu/..." --project "my-paper-2024"

# Search with project context (auto-detected from .search-ads.yaml)
search-ads find --context "..."

# List papers in a project
search-ads project list "my-paper-2024"

# Show all projects
search-ads project list
```

---

## Search Algorithm

### Parameters
- `max_hops`: Maximum citation/reference expansion depth (default: 2, user-configurable)
- `top_k`: Number of candidates to return per search (default: 10)
- `expand_top_k`: Number of papers to expand per hop (default: 5, prevents explosion)
- `refs_limit`: Max references to fetch per paper (default: 30)
- `citations_limit`: Max citations to fetch per paper (default: 30)
- `min_citation_count`: Minimum citations for a paper to be included (default: 0)

### Efficiency Controls
- **Rate limiting**: Track ADS API calls, max ~5000/day
- **Caching**: Check `searches` table for similar contexts before querying
- **Two-stage ranking**:
  1. Vector similarity (fast) → filter to top 20
  2. LLM ranking (accurate) → select top 5 to present

### Citation Type Classification
The LLM should identify what TYPE of citation is needed:
- **Foundational**: "X established that..." (seminal papers)
- **Methodological**: "Following the method of X..." (technique papers)
- **Supporting**: "consistent with X..." (corroborating evidence)
- **Contrasting**: "unlike X, we find..." (papers to contrast against)
- **Review**: "see X for a review" (review articles)

### Workflow

```
1. INPUT: Empty \cite{} with surrounding LaTeX context

2. CONTEXT EXTRACTION:
   - Extract paragraph/sentence around the empty citation
   - Use LLM to identify: topic, claim type, what kind of source is needed

3. LOCAL SEARCH (fast, no API cost):
   - Embed context → query ChromaDB for similar abstracts
   - If good matches found (similarity > threshold), use them

4. ADS SEARCH (if local search insufficient):
   - LLM extracts search keywords from context
   - Query ADS API with keywords
   - Fetch paper metadata and store in database

5. GRAPH EXPANSION (up to max_hops):
   hop = 0
   candidates = initial_results
   while hop < max_hops:
       # Limit expansion to prevent API explosion
       papers_to_expand = top_k_by_relevance(candidates, k=expand_top_k)

       for paper in papers_to_expand:
           # Check if already in database (skip API call)
           if refs_not_in_db(paper):
               fetch_references(paper, limit=refs_limit)
           if citations_not_in_db(paper):
               fetch_citations(paper, limit=citations_limit, min_citations=min_citation_count)

           # Quick scoring via embeddings (not LLM)
           score_new_papers_by_embedding_similarity()

       candidates = merge_and_deduplicate(candidates, new_papers)
       hop += 1

6. RANKING:
   - Use LLM to rank final candidates by:
     - Relevance to the statement being cited
     - Citation count / impact
     - Recency (if relevant)
   - Return ranked list with explanations

7. PRESENT RESULTS:
   - Show ranked papers with: title, authors, year, abstract, relevance explanation, citation count
   - User can: Accept, Reject (search more), or Skip

8. HANDLE USER RESPONSE:
   - Accept: Fill \cite{bibkey} in LaTeX
     - Check for duplicates in existing .bib file first
     - If using .bib file: add bibtex entry to .bib file
     - If no .bib file: add \bibitem entry at the end of the .tex file (before \end{document})
     - Record acceptance for feedback learning
   - Reject:
     - Record rejection (exclude from future results for this context)
     - Expand search (increase hops, broaden keywords) → go to step 5
   - Skip: Leave citation empty, move to next empty citation

9. FEEDBACK LEARNING:
   - Track accepted/rejected papers per search context
   - Boost papers similar to accepted ones in future searches
   - Penalize papers similar to rejected ones
```

---

## Citation Key Generation

### Format Options (user-configurable in `.search-ads.yaml`)
```yaml
citation_key:
  format: "author_year"  # Options: author_year, author_year_title, bibcode
  lowercase: true
  max_length: 30
```

### Formats
- `author_year`: `smith2024` (first author + year)
- `author_year_title`: `smith2024dark` (+ first word of title)
- `bibcode`: `2024ApJ...123S` (use ADS bibcode directly)

### Duplicate Handling
- Before adding to .bib, check if bibcode/DOI already exists
- If duplicate found, reuse existing citation key
- Warn user if same paper has different keys

---

## Batch Processing

### Multiple Empty Citations
When a paragraph has multiple `\cite{}`:
```latex
Dark matter halos \cite{} follow NFW profiles \cite{}, though
some studies suggest \cite{} alternative models.
```

### Workflow
1. Parse all empty citations in selection/paragraph
2. For each, extract local context (surrounding sentence)
3. Run searches in parallel (respecting rate limits)
4. Present all results together
5. User can accept/reject each independently
6. Fill all accepted citations at once

---

## ADS API Rate Limiting

### Limits
- ADS allows ~5000 requests/day for authenticated users
- Need to track and respect this limit

### Implementation
```sql
-- Track API usage
CREATE TABLE api_usage (
    date TEXT PRIMARY KEY,          -- YYYY-MM-DD
    ads_calls INTEGER DEFAULT 0,
    openai_calls INTEGER DEFAULT 0,
    anthropic_calls INTEGER DEFAULT 0
);
```

### Behavior
- Before each ADS call, check daily count
- If approaching limit (>4500), warn user
- If at limit, fall back to local database only
- Show usage stats in CLI: `search-ads status`

---

## Offline Mode

### Detection
- Check network connectivity before ADS/LLM calls
- Graceful fallback when offline

### Offline Capabilities
- **Full**: Browse local database, view papers, search by embeddings
- **Limited**: Cannot fetch new papers, expand graph, or use LLM ranking
- **Degraded search**: Use embedding similarity only (no LLM)

### Sync on Reconnect
- Queue failed operations (seeds, expansions)
- Retry when connection restored

---

## PDF Handling

### Workflow
1. **Store URL**: Always store `pdf_url` from ADS/arXiv
2. **One-click download**: User can download important papers via CLI or web UI
3. **Optional embedding**: After download, user can choose to embed PDF content for full-text search

### Implementation
```python
# CLI commands
search-ads pdf download <bibcode>      # Download PDF to data/pdfs/
search-ads pdf embed <bibcode>         # Parse PDF and embed in ChromaDB
search-ads pdf embed --all-downloaded  # Embed all downloaded PDFs
```

---

## Claude Code Skill Definition

### Skill: `search-cite`

Location: `~/.claude/skills/search-cite.md` or project-local `.claude/skills/search-cite.md`

```markdown
---
name: search-cite
description: Search for scientific paper citations using ADS and fill empty \cite{} in LaTeX
version: 1.0.0
---

# Search Citation Skill

This skill helps find and fill scientific paper citations in LaTeX documents.

## Usage

When the user asks to fill citations or work on a LaTeX paragraph with empty `\cite{}`:

1. Identify the `.tex` file and locate empty citations (`\cite{}`, `\citep{}`, `\citet{}`)
2. Extract the surrounding context (paragraph or sentence)
3. Run the search-ads CLI to find relevant papers:

```bash
search-ads find --context "THE_SURROUNDING_TEXT" --max-hops 2 --top-k 5
```

4. Present the results to the user with:
   - Paper title, authors, year
   - Abstract (truncated if too long)
   - Why it's relevant to the context (LLM-generated explanation)
   - Citation count

5. User interaction:
   - **Accept**: Fill the citation and add to bibliography
   - **Reject**: Search for more papers (expand search, adjust keywords, or increase hops)
   - **Skip**: Leave citation empty for now

6. After user confirms, fill the citation:

```bash
# If using .bib file:
search-ads fill --bibcode "2023ApJ...XXX" --tex-file "paper.tex" --bib-file "references.bib" --cite-position LINE:COL

# If no .bib file (uses \bibitem in .tex):
search-ads fill --bibcode "2023ApJ...XXX" --tex-file "paper.tex" --cite-position LINE:COL
```

The tool auto-detects whether the .tex file uses `\bibliography{}` or inline `\bibitem`. If no .bib file is specified and none is detected, it appends `\bibitem` entries before `\end{document}`.

## Commands

| Command | Description |
|---------|-------------|
| `search-ads find --context "..." [--max-hops N] [--top-k N]` | Search for papers matching context |
| `search-ads fill --bibcode "..." --tex-file "..." --bib-file "..."` | Fill citation in files |
| `search-ads add --bibcode "..."` | Add a paper to local database |
| `search-ads expand --bibcode "..." [--hops N]` | Expand citations/references graph |
| `search-ads pdf download <bibcode>` | Download PDF |
| `search-ads pdf embed <bibcode>` | Embed PDF for full-text search |
| `search-ads serve` | Start web UI for database browsing |

## Environment

Requires API keys in `.env`:
- `ADS_API_KEY`: NASA ADS API token
- `OPENAI_API_KEY`: For embeddings (text-embedding-3-small)
- `ANTHROPIC_API_KEY`: For LLM reasoning (optional, can use OpenAI)
```

---

## Tech Stack

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Language | Python 3.10 | Ecosystem, ADS library support |
| CLI | Typer | Modern, type-hint based, auto-generates help |
| Database | SQLite + SQLModel | Simple, no server, ORM with type hints |
| Vector Store | ChromaDB | Local, Python-native, good for single-user |
| Embeddings | OpenAI `text-embedding-3-small` | Cost-effective, high quality |
| LLM | Claude API (primary), OpenAI (fallback) | Best reasoning for relevance ranking |
| Web Framework | FastAPI + Jinja2 + HTMX | Lightweight, async, minimal JS |
| PDF Parsing | PyMuPDF (fitz) | Fast, reliable PDF text extraction |
| ADS API | `ads` Python library | Official NASA ADS client |

---

## Environment Setup

Using Nix + direnv (shell.nix):

```nix
{ pkgs ? import <nixpkgs> { system = "aarch64-darwin"; } }:

pkgs.mkShell {
  name = "search-ads";

  buildInputs = with pkgs; [
    python310
    python310Packages.pip
    python310Packages.virtualenv
    git
  ];

  shellHook = ''
    [ ! -d ".venv" ] && virtualenv .venv
    source .venv/bin/activate

    # Install dependencies if needed
    [ -f "pyproject.toml" ] && pip install -e ".[dev]" -q

    echo "🔭 Search-ADS Development Environment"
  '';
}
```

---

## Web Frontend (Phase 2)

The web frontend is a **full management interface**, not just a viewer. It can execute all CLI operations.

### Features

#### Database Browsing
- Browse paper database with search/filter
- View paper details (title, authors, abstract, bibtex)
- Visualize citation graph (D3.js or similar)
- Expand citation graph by clicking on references/citations

#### Database Management (CLI via Web)
- **Seed papers**: Input ADS URL or bibcode to add papers
- **Expand**: Click to fetch references/citations for any paper
- **Import**: Upload .bib files to import
- **Delete**: Remove papers from database

#### PDF Management
- One-click PDF download from ADS/arXiv
- View download status (not downloaded / downloaded / embedded)
- Embed/un-embed PDFs for full-text search
- Open/preview downloaded PDFs

#### Project Management
- Create/switch between projects
- View papers by project
- Seed papers to specific projects

#### Search & Discovery
- Semantic search across abstracts
- Full-text search (for embedded PDFs)
- Filter by year, citation count, project, etc.

### API Endpoints (FastAPI)

```python
# Papers
GET    /api/papers                    # List papers (with filters)
GET    /api/papers/{bibcode}          # Get paper details
DELETE /api/papers/{bibcode}          # Remove paper

# Database operations
POST   /api/seed                      # Seed paper from ADS URL/bibcode
POST   /api/expand/{bibcode}          # Expand refs/citations for paper
POST   /api/import                    # Import from .bib file (multipart)

# PDF operations
POST   /api/pdf/download/{bibcode}    # Download PDF
POST   /api/pdf/embed/{bibcode}       # Embed PDF in vector store
DELETE /api/pdf/embed/{bibcode}       # Remove PDF embedding

# Projects
GET    /api/projects                  # List projects
POST   /api/projects                  # Create project
GET    /api/projects/{name}/papers    # Papers in project

# Search
POST   /api/search                    # Semantic search
GET    /api/graph/{bibcode}           # Get citation graph data
```

### UI Sketch
```
┌──────────────────────────────────────────────────────────────────────────┐
│ Search-ADS                                              [Project: paper1]│
├────────────┬─────────────────────────────────────────────────────────────┤
│            │  ┌─────────────────────────────────────────────────────┐    │
│ Navigation │  │ + Add Paper                                         │    │
│            │  │ ┌─────────────────────────────────────────────────┐ │    │
│ Papers     │  │ │ ADS URL or Bibcode: [________________________]  │ │    │
│ Projects   │  │ │ [x] Auto-expand (1 hop)    [Seed Paper]         │ │    │
│ Search     │  │ └─────────────────────────────────────────────────┘ │    │
│ Graph      │  └─────────────────────────────────────────────────────┘    │
│ Settings   │                                                             │
│            │  Papers (142)                        [Search: __________]   │
├────────────┤  ┌─────────────────────────────────────────────────────────┐│
│            │  │ ★ Smith et al. 2023 - "Dark Matter in Galaxies"        ││
│ Filters    │  │   Citations: 45 | Refs: 32                             ││
│ Year: all  │  │   [Expand] [PDF ⬇] [Embed] [Delete]                    ││
│ Cited: >10 │  ├─────────────────────────────────────────────────────────┤│
│ Project:all│  │   Jones et al. 2022 - "Stellar Evolution Models"       ││
│            │  │   Citations: 120 | Refs: 28                            ││
│            │  │   [Expand] [PDF ✓] [Embedded ✓] [Delete]               ││
│            │  └─────────────────────────────────────────────────────────┘│
├────────────┴─────────────────────────────────────────────────────────────┤
│ Citation Graph                                              [Fullscreen] │
│ ┌───────────────────────────────────────────────────────────────────────┐│
│ │                        [Paper A]                                      ││
│ ���                       /    |    \                                     ││
│ │                [Ref 1] [Ref 2] [Ref 3]  ← click to expand/add        ││
│ │                           |                                           ││
│ │                       [Ref 2.1]                                       ││
│ └───────────────────────────────────────────────────────────────────────┘│
│ │          [Ref 2.1]  ← click to expand                  │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## Development Phases

### Phase 1: Core CLI (MVP) ✅ Complete
- [x] Project setup (pyproject.toml, dependencies)
- [x] ADS API client with rate limiting
- [x] SQLite database with SQLModel
- [x] LaTeX parser (find empty citations)
- [x] Basic search (ADS query → results)
- [x] Fill citation command
- [x] BibTeX and AASTeX bibitem generation

### Phase 2: Intelligence ✅ Complete
- [x] ChromaDB vector store setup
- [x] Embed abstracts on paper add
- [x] LLM-based relevance ranking (Claude/OpenAI)
- [x] Graph expansion (citations/references)
- [x] Context-aware search with citation type classification
- [x] Dual LLM backend support (Anthropic preferred, OpenAI fallback)

### Phase 3: PDF & Polish ✅ Complete
- [x] PDF download command (arXiv and ADS)
- [x] PDF parsing and embedding with PyMuPDF
- [x] Full-text semantic search in PDFs
- [x] Claude Code skill definition
- [x] Error handling and edge cases
- [x] Project/collection management
- [x] BibTeX file import
- [x] API usage tracking

### Phase 4: Web UI (In Progress)

See `webui_design.md` for detailed design specifications.

#### Phase 4.1: Foundation
- [ ] FastAPI backend with all API routes
- [ ] React frontend with TanStack Router (sidebar navigation)
- [ ] Library view with full table features (columns, sorting, filtering, bulk actions)
- [ ] Right-click context menu (view, find refs/citations, download, copy)
- [ ] Paper detail view
- [ ] Project management (dropdown, CRUD)

#### Phase 4.2: Search & Discovery
- [ ] Search view with natural language input
- [ ] AI-powered search with "Add to Library" + project selection
- [ ] Writing Assistant (paste LaTeX text, get BibTeX/bibitem output)

#### Phase 4.3: Knowledge Graph
- [ ] vis.js graph visualization with node design (shape, size, color)
- [ ] Interactive exploration (pan, zoom, expand, path finding)
- [ ] Export as image

#### Phase 4.4: Import & Settings
- [ ] Import view with project selection
- [ ] Settings with citation count auto-update
- [ ] Database management

#### Phase 4.5: Polish
- [ ] Keyboard shortcuts, dark mode, dashboard
- [ ] Performance optimization

---

## Completed Bug Fixes & Improvements

All planned improvements from the initial design have been implemented:

| Item | Status | Description |
|------|--------|-------------|
| Bug 1: Project Expand | ✅ | References/citations now added to project during `--expand` |
| Bug 2: Fill Redesign | ✅ | New `get` command returns citation info as plain text |
| Feature 3: Bibcode Keys | ✅ | Default citation key uses bibcode for uniqueness |
| Feature 4: AASTeX Format | ✅ | Bibitem uses ADS export API for proper formatting |
| Feature 5: DB Schema | ✅ | Both `bibtex` and `bibitem_aastex` stored in database |
| Feature 6: DB Update | ✅ | Batch update command with project/age filtering |

---

## Future Improvements

Potential enhancements for future development (post Phase 4):

- [ ] PDF viewer component with annotations in Web UI
- [ ] AI Q&A about paper content
- [ ] Full project workspace with LaTeX file linking
- [ ] Gap analysis (missing important papers in bibliography)
- [ ] Activity timeline and research progress tracking
- [ ] Batch processing for multiple empty citations in parallel
- [ ] Feedback learning from accepted/rejected paper suggestions
- [ ] Offline mode with queued operations
- [ ] Integration with Zotero/Mendeley

---

## API Keys Required

Store in `.env`:
```
ADS_API_KEY=your_ads_api_key_here
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
```

Get ADS API key: https://ui.adsabs.harvard.edu/user/settings/token
