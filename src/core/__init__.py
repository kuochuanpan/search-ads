"""Core module for search-ads."""

from src.core.ads_client import ADSClient, RateLimitExceeded
from src.core.config import ProjectConfig, Settings, ensure_data_dirs, settings
from src.core.latex_parser import (
    EmptyCitation,
    LaTeXParser,
    add_bibtex_entry,
    format_bibitem_from_paper,
)

__all__ = [
    "ADSClient",
    "RateLimitExceeded",
    "ProjectConfig",
    "Settings",
    "ensure_data_dirs",
    "settings",
    "EmptyCitation",
    "LaTeXParser",
    "add_bibtex_entry",
    "format_bibitem_from_paper",
]
