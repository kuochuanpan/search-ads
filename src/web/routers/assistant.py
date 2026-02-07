from fastapi import APIRouter, HTTPException
from pathlib import Path
import json
import os

router = APIRouter()

INSIGHTS_FILE = Path(os.path.expanduser("~/.openclaw/workspace/search-ads-insights.json"))

@router.get("/insights")
def get_assistant_insights():
    if not INSIGHTS_FILE.exists():
        return {
            "last_updated": None,
            "summary": "No insights available yet.",
            "recommendations": [],
            "insights": []
        }
    try:
        with open(INSIGHTS_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
