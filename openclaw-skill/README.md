# Search-ADS Skill for OpenClaw

This skill integrates **Search-ADS** (your personal astrophysics paper library) with **OpenClaw** agents, enabling AI-powered literature management.

## What It Does

Your AI agent can:
- 🔍 **Search** for papers using natural language or by author/year
- 📥 **Add** papers to your library by Bibcode, arXiv ID, DOI, or URL
- 📖 **Show** paper details (abstract, citations, notes)
- 🌐 **Expand** citation graphs to discover related work
- 📝 **Annotate** papers with reading notes
- 📄 **Get** BibTeX and citation info
- 📥 **Download** PDFs
- 📊 **Sync** assistant insights to the WebUI dashboard

## Prerequisites

1. **Search-ADS** installed and configured (with `.venv` and ADS API token)
2. **OpenClaw** running

## Installation

```bash
cd openclaw-skill
./install.sh ~/code/search-ads "Maho"   # or your agent's name
```

This will:
- Copy the skill to `~/.openclaw/workspace/skills/search-ads/`
- Enable the assistant integration for the WebUI

## Usage Examples

Ask your agent:

| You say | What happens |
|---------|-------------|
| "Find papers about neutrino transport in CCSNe" | Semantic search across library + ADS |
| "Add paper 2024ApJ...123..456P" | Fetches metadata and adds to library |
| "Show me Pan's papers from 2020-2024" | Author + year filtered search |
| "Get BibTeX for this paper" | Returns citation info |
| "Download the PDF" | Fetches PDF from ADS |
| "Update my dashboard" | Analyzes recent papers → WebUI insights |

## Skill Structure

```
search-ads/
├── SKILL.md           # Skill definition (YAML frontmatter + Markdown)
└── scripts/
    └── sync_insights.py   # Dashboard insights generator
```

## Dashboard Integration

After running `search_ads_sync` at least once, your Search-ADS WebUI will show an assistant insights card. The WebUI reads from `~/.search-ads/assistant_insights.json` (override with `ASSISTANT_INSIGHTS_PATH`).

## Building Skills — Reference

This skill follows the [Anthropic Skills Guide](https://docs.anthropic.com) format:

- **YAML frontmatter** with `name` (kebab-case) and `description` (includes trigger phrases)
- **Markdown body** with instructions, tool docs, examples, and troubleshooting
- **Progressive disclosure**: frontmatter → SKILL.md body → linked scripts
- **`scripts/`** for executable code bundled with the skill

For more on building skills, see the [Anthropic Skills Best Practices Guide](https://docs.anthropic.com/en/docs/agents-and-tools/skills).
