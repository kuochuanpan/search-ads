"""Core module for search-ads.

Note: Imports are lazy to avoid circular dependencies.
Import directly from submodules instead of from this __init__.py.
"""

# Lazy imports - these are available but only loaded when accessed
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


def __getattr__(name):
    """Lazy import to avoid circular dependencies."""
    if name in ("ADSClient", "RateLimitExceeded"):
        from src.core.ads_client import ADSClient, RateLimitExceeded
        return ADSClient if name == "ADSClient" else RateLimitExceeded
    elif name in ("ProjectConfig", "Settings", "ensure_data_dirs", "settings"):
        from src.core.config import ProjectConfig, Settings, ensure_data_dirs, settings
        if name == "ProjectConfig":
            return ProjectConfig
        elif name == "Settings":
            return Settings
        elif name == "ensure_data_dirs":
            return ensure_data_dirs
        else:
            return settings
    elif name in ("EmptyCitation", "LaTeXParser", "add_bibtex_entry", "format_bibitem_from_paper"):
        from src.core.latex_parser import (
            EmptyCitation,
            LaTeXParser,
            add_bibtex_entry,
            format_bibitem_from_paper,
        )
        if name == "EmptyCitation":
            return EmptyCitation
        elif name == "LaTeXParser":
            return LaTeXParser
        elif name == "add_bibtex_entry":
            return add_bibtex_entry
        else:
            return format_bibitem_from_paper
    elif name in ("CitationType", "ContextAnalysis", "LLMClient", "LLMNotAvailable", "RankedPaper"):
        from src.core.llm_client import (
            CitationType,
            ContextAnalysis,
            LLMClient,
            LLMNotAvailable,
            RankedPaper,
        )
        if name == "CitationType":
            return CitationType
        elif name == "ContextAnalysis":
            return ContextAnalysis
        elif name == "LLMClient":
            return LLMClient
        elif name == "LLMNotAvailable":
            return LLMNotAvailable
        else:
            return RankedPaper
    elif name in ("CitationEngine", "CitationResult", "FillResult"):
        from src.core.citation_engine import CitationEngine, CitationResult, FillResult
        if name == "CitationEngine":
            return CitationEngine
        elif name == "CitationResult":
            return CitationResult
        else:
            return FillResult
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
