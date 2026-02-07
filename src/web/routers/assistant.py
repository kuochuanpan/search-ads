from __future__ import annotations

import json
import os
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

from src.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


def _insights_path() -> Path:
    """Resolve the insights JSON path.

    Priority:
    1) ASSISTANT_INSIGHTS_PATH env var
    2) <data_dir>/assistant_insights.json

    This keeps the API testable and avoids hard-coding machine-specific paths.
    """
    override = os.getenv("ASSISTANT_INSIGHTS_PATH")
    if override:
        return Path(os.path.expanduser(override)).resolve()
    return (settings.data_dir / "assistant_insights.json").resolve()


@router.get("/insights")
def get_assistant_insights():
    insights_file = _insights_path()

    if not insights_file.exists():
        return {
            "last_updated": None,
            "summary": "No insights available yet.",
            "recommendations": [],
            "insights": [],
        }

    try:
        with open(insights_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        logger.exception("Invalid insights JSON: %s", insights_file)
        raise HTTPException(status_code=500, detail="Insights file is not valid JSON")
    except Exception:
        # Avoid leaking filesystem paths / internal exceptions.
        logger.exception("Failed to read insights file: %s", insights_file)
        raise HTTPException(status_code=500, detail="Failed to read insights")
