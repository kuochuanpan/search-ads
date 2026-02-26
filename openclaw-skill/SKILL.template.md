---
name: search-ads
description: "Search, manage, and analyze scientific papers from NASA ADS. Use when: user asks to find papers, search literature, add a paper by bibcode/arXiv/DOI, show paper details, manage reading notes, list library contents, expand citation graphs, get BibTeX, download PDFs, or update the assistant insights dashboard. NOT for: general web search, non-academic literature, or tasks unrelated to scientific papers."
metadata:
  author: Kuo-Chuan Pan
  version: 0.9.0-beta
  homepage: https://github.com/kuochuanpan/search-ads
  openclaw:
    emoji: "🔭"
    requires:
      bins: ["python3"]
---

# Search-ADS Skill

Interact with the Search-ADS tool to search, manage, and analyze scientific papers from NASA ADS. Supports semantic search, adding papers by identifier/URL, managing notes, and retrieving paper details.

## When to Use

✅ **USE this skill when:**

- "Find papers about [topic]" / "Search for [author]'s papers"
- "Add this paper: [bibcode/arXiv ID/DOI/URL]"
- "Show me details of [paper]"
- "What papers do I have about [topic]?"
- "Get the BibTeX for [paper]"
- "Download the PDF for [paper]"
- "Expand citations for [paper]"
- "Add a note to [paper]"
- "Update my dashboard insights"

❌ **DON'T use this skill when:**

- General web search (use web_search)
- Non-academic content
- Tasks unrelated to scientific literature

## Tools

### search_ads_find

Search for papers in the library or online using natural language.

```bash
__SEARCH_ADS_PYTHON__ -m src.cli.main find \
  -c "CONTEXT" \       # search query (e.g., "M1 closure in CCSN")
  -a "AUTHOR" \        # filter by author (e.g., "Pan")
  -y "YEAR" \          # filter by year (e.g., "2020" or "2018-2022")
  -k TOP_K \           # number of results (default: 5)
  --local \            # search local DB only (no ADS API)
  --no-llm             # disable LLM ranking
```

All parameters optional. At least one of context/author/year should be provided.

### search_ads_seed

Add a paper to the local library by identifier.

```bash
__SEARCH_ADS_PYTHON__ -m src.cli.main seed "IDENTIFIER" \
  --project "PROJECT"  # optional project tag
```

IDENTIFIER: Bibcode, arXiv ID, DOI, or ADS URL.

### search_ads_expand

Expand the citation graph (discover references and citing papers).

```bash
__SEARCH_ADS_PYTHON__ -m src.cli.main expand "BIBCODE"
```

Omit BIBCODE to expand all papers.

### search_ads_show

Show detailed paper info (abstract, citations, notes).

```bash
__SEARCH_ADS_PYTHON__ -m src.cli.main show "BIBCODE"
```

### search_ads_list

List papers in the local library.

```bash
__SEARCH_ADS_PYTHON__ -m src.cli.main list-papers \
  -n LIMIT \           # number of papers (default: 20)
  -p "PROJECT"         # filter by project
```

### search_ads_note

Add or view notes for a paper.

```bash
# View existing note
__SEARCH_ADS_PYTHON__ -m src.cli.main note "BIBCODE"

# Add/append note
__SEARCH_ADS_PYTHON__ -m src.cli.main note "BIBCODE" --add "NOTE CONTENT"
```

### search_ads_get

Get citation info (cite key, bibitem, bibtex).

```bash
__SEARCH_ADS_PYTHON__ -m src.cli.main get "BIBCODE"
```

### search_ads_pdf_download

Download a paper's PDF.

```bash
__SEARCH_ADS_PYTHON__ -m src.cli.main pdf download "BIBCODE"
```

### search_ads_status

Show database and API usage status.

```bash
__SEARCH_ADS_PYTHON__ -m src.cli.main status
```

### search_ads_sync

Analyze recent papers and update the assistant insights dashboard on the WebUI.

```bash
__SEARCH_ADS_PYTHON__ __SKILL_DIR__/scripts/sync_insights.py LIMIT
```

LIMIT: number of recent papers to analyze (default: 5).

## Examples

**Example 1: Literature search**
User says: "Find recent papers about neutrino transport in core-collapse supernovae"
Action: `search_ads_find -c "neutrino transport in core-collapse supernovae" -y "2020-2025"`

**Example 2: Add a paper**
User says: "Add this paper: 2024ApJ...123..456P"
Action: `search_ads_seed "2024ApJ...123..456P"`

**Example 3: Research workflow**
User says: "Show me Pan's recent papers and add any about nuclear EOS to my library"
Actions:
1. `search_ads_find -a "Pan" -y "2023-2025"` — find papers
2. Review results, identify relevant ones
3. `search_ads_seed "BIBCODE"` — add each relevant paper
4. `search_ads_note "BIBCODE" --add "Relevant to nuclear EOS project"` — add note

## Troubleshooting

**Error: Command not found or venv issue**
- Verify Search-ADS is installed and the virtual environment exists
- Re-run installer: `cd openclaw-skill && ./install.sh`

**Error: ADS API rate limit**
- Use `--local` flag to search local DB only
- Check status: `search_ads_status`

**Error: Paper not found**
- Try different identifier formats (Bibcode vs arXiv ID vs DOI)
- Check ADS directly: `https://ui.adsabs.harvard.edu/search/`
