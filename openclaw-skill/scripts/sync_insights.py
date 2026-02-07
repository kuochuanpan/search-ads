import sqlite3
import os
import json
import datetime
from pathlib import Path
from dotenv import load_dotenv
from google.genai import Client

# Paths
DB_PATH = os.path.expanduser("~/.search-ads/papers.db")
ENV_PATH = os.path.expanduser("~/.search-ads/.env")
INSIGHTS_PATH = os.path.expanduser("~/.openclaw/workspace/search-ads-insights.json")

# Load Env
load_dotenv(ENV_PATH)
API_KEY = os.getenv("GEMINI_API_KEY")

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
        paper_text += f"Title: {p['title']}\n"
        paper_text += f"Bibcode: {p['bibcode']}\n"
        paper_text += f"Year: {p['year']}\n"
        paper_text += f"Abstract: {p['abstract'][:500]}...\n\n"

    prompt = f"""
    You are an expert astrophysics research assistant named "Maho". 
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
            model="gemini-2.0-flash",
            contents=prompt,
            config={
                'response_mime_type': 'application/json'
            }
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"LLM Generation Error: {e}")
        return None

def main():
    print(f"--- Maho's Insight Generator ---")
    
    papers = fetch_recent_papers(limit=5)
    if not papers:
        print("No papers found.")
        return

    print(f"Analyzing {len(papers)} papers with Gemini...")
    insights_data = generate_insights(papers)
    
    if insights_data:
        # Add timestamp
        insights_data["last_updated"] = datetime.datetime.now().isoformat()
        
        # Save
        with open(INSIGHTS_PATH, "w") as f:
            json.dump(insights_data, f, indent=2)
        print(f"✅ Insights updated at: {INSIGHTS_PATH}")
        print("Summary:", insights_data["summary"])
    else:
        print("❌ Failed to generate insights.")

if __name__ == "__main__":
    main()
