import sqlite3
import os
import sys
import json
import datetime
from pathlib import Path

from dotenv import load_dotenv
from google.genai import Client

# Paths
DB_PATH = os.path.expanduser("~/.search-ads/papers.db")
ENV_PATH = os.path.expanduser("~/.search-ads/.env")

# Load Env (so we can read config from ~/.search-ads/.env)
load_dotenv(ENV_PATH)

ASSISTANT_NAME = os.getenv("ASSISTANT_NAME", "OpenClaw")

# Write insights next to Search-ADS data by default (aligns with backend default)
DEFAULT_INSIGHTS_PATH = os.path.expanduser("~/.search-ads/assistant_insights.json")
INSIGHTS_PATH = os.path.expanduser(os.getenv("ASSISTANT_INSIGHTS_PATH", DEFAULT_INSIGHTS_PATH))

API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")

def fetch_recent_papers(limit=5):
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return []

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get recent papers with their details
        query = """
        SELECT bibcode, title, abstract, authors, year, pdf_path, created_at 
        FROM papers 
        ORDER BY created_at DESC 
        LIMIT ?
        """
        
        cursor.execute(query, (limit,))
        papers = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return papers
    except Exception as e:
        print(f"Error reading database: {e}")
        return []

def generate_insights(papers):
    if not API_KEY:
        print("Error: GEMINI_API_KEY not found in .env")
        return None

    # Prepare context for LLM
    paper_text = ""
    for p in papers:
        paper_text += f"Title: {p.get('title')}\n"
        paper_text += f"Bibcode: {p.get('bibcode')}\n"
        paper_text += f"Year: {p.get('year')}\n"

        abstract = p.get('abstract')
        if isinstance(abstract, str) and abstract.strip():
            abstract_snippet = abstract[:500]
        else:
            abstract_snippet = "(no abstract available)"

        paper_text += f"Abstract: {abstract_snippet}...\n\n"

    prompt = f"""
    You are an expert astrophysics research assistant named \"{ASSISTANT_NAME}\".
    Analyze these {len(papers)} recent papers from the user's library.
    
    Papers:
    {paper_text}
    
    Output a JSON object with this EXACT structure (do not use markdown formatting, just raw JSON):
    {{
        "summary": "A one-sentence high-level summary of what these papers focus on (e.g. 'Recent additions focus on M1 closure schemes...')",
        "insights": [
            "Key insight 1 (e.g. specific finding or trend)",
            "Key insight 2",
            "Key insight 3"
        ],
        "recommendations": [
            {{
                "bibcode": "BIBCODE_FROM_LIST",
                "title": "Exact Title From List",
                "reason": "Why this specific paper is worth reading now based on the abstract."
            }}
        ]
    }}
    
    Pick only top 2 recommendations. Keep tone professional but helpful.
    """

    try:
        client = Client(api_key=API_KEY)
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
            },
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"LLM Generation Error: {e}")
        return None

def main():
    print(f"--- {ASSISTANT_NAME}'s Insight Generator ---")

    # Optional: pass limit as first CLI arg
    limit = 5
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            print(f"Warning: invalid limit '{sys.argv[1]}', using default 5")

    papers = fetch_recent_papers(limit=limit)
    if not papers:
        print("No papers found.")
        return

    print(f"Analyzing {len(papers)} papers with Gemini...")
    insights_data = generate_insights(papers)
    
    if insights_data:
        # Add timestamp
        insights_data["last_updated"] = datetime.datetime.now().isoformat()

        # Save (ensure parent exists)
        out_path = Path(INSIGHTS_PATH)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(insights_data, f, indent=2, ensure_ascii=False)
        print(f"✅ Insights updated at: {INSIGHTS_PATH}")
        print("Summary:", insights_data["summary"])
    else:
        print("❌ Failed to generate insights.")

if __name__ == "__main__":
    main()
