"""Core module for search-ads."""

from src.core.ads_client import ADSClient, RateLimitExceeded
from src.core.config import ProjectConfig, Settings, ensure_data_dirs, settings
from src.core.latex_parser import (
    EmptyCitation,
    LaTeXParser,
    add_bibtex_entry,
    format_bibitem_from_paper,
)
from src.core.llm_client import (
    CitationType,
    ContextAnalysis,
    LLMClient,
    LLMNotAvailable,
    RankedPaper,
)
from src.core.citation_engine import CitationEngine, CitationResult, FillResult

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
    "CitationType",
    "ContextAnalysis",
    "LLMClient",
    "LLMNotAvailable",
    "RankedPaper",
    "CitationEngine",
    "CitationResult",
    "FillResult",
]
