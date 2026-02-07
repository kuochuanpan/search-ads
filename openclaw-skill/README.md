# Search-ADS Skill for OpenClaw

This skill integrates **Search-ADS** (your personal astrophysics library) with **OpenClaw** agents.

It allows your AI agent to:
- 🔍 **Search** for papers using natural language (`search_ads_find`).
- 📥 **Download** PDFs and add papers to your library (`search_ads_seed`).
- 🧠 **Analyze** recent papers and update the assistant insights dashboard on the WebUI (`search_ads_sync`).

## Prerequisites

1.  **Search-ADS** installed and configured (with `.venv`).
2.  **OpenClaw** running.

## Installation

Run the install script from your search-ads directory:

```bash
cd openclaw-skill
# Optional: pass your agent's display name (shown on the WebUI)
./install.sh ~/code/search-ads "Maho"
```

This will copy the skill definition to `~/.openclaw/workspace/skills/search-ads/`.

## Usage

You can ask your agent:
- "Find papers about [topic]"
- "Add paper [bibcode] to my library"
- "Read the latest papers and update my dashboard"

## Dashboard Integration

To see the assistant insights card on your Search-ADS WebUI:
1.  Ensure you have run `search_ads_sync` at least once via the agent.
2.  The WebUI reads insights from `~/.search-ads/assistant_insights.json` by default (override with `ASSISTANT_INSIGHTS_PATH`).
