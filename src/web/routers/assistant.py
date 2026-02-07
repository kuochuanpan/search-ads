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
    # If the user doesn't have OpenClaw/assistant integration enabled,
    # don't expose assistant content (frontend should hide the card).
    if not settings.assistant_enabled:
        raise HTTPException(status_code=404, detail="Assistant integration not enabled")

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
            raw = json.load(f)

        # Normalize/validate shape to keep the frontend stable even if the file is partial/old.
        if not isinstance(raw, dict):
            raise HTTPException(status_code=500, detail="Insights file must be a JSON object")

        recommendations = raw.get("recommendations")
        insights = raw.get("insights")

        return {
            "last_updated": raw.get("last_updated"),
            "summary": raw.get("summary") or "",
            "recommendations": recommendations if isinstance(recommendations, list) else [],
            "insights": insights if isinstance(insights, list) else [],
        }
    except json.JSONDecodeError:
        logger.exception("Invalid insights JSON: %s", insights_file)
        raise HTTPException(status_code=500, detail="Insights file is not valid JSON")
    except Exception:
        # Avoid leaking filesystem paths / internal exceptions.
        logger.exception("Failed to read insights file: %s", insights_file)
        raise HTTPException(status_code=500, detail="Failed to read insights")
