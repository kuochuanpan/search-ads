"""Dependency injection for FastAPI endpoints."""

from src.db.repository import (
    PaperRepository,
    ProjectRepository,
    CitationRepository,
    NoteRepository,
    ApiUsageRepository,
)
from src.core.ads_client import ADSClient
from src.core.llm_client import LLMClient
from src.core.pdf_handler import PDFHandler
from src.db.vector_store import get_vector_store


def get_paper_repo() -> PaperRepository:
    """Get paper repository instance."""
    return PaperRepository()


def get_project_repo() -> ProjectRepository:
    """Get project repository instance."""
    return ProjectRepository()


def get_citation_repo() -> CitationRepository:
    """Get citation repository instance."""
    return CitationRepository()


def get_note_repo() -> NoteRepository:
    """Get note repository instance."""
    return NoteRepository()


def get_api_usage_repo() -> ApiUsageRepository:
    """Get API usage repository instance."""
    return ApiUsageRepository()


def get_ads_client() -> ADSClient:
    """Get ADS client instance."""
    return ADSClient()


def get_llm_client() -> LLMClient:
    """Get LLM client instance."""
    return LLMClient()


def get_pdf_handler() -> PDFHandler:
    """Get PDF handler instance."""
    return PDFHandler()


def get_vector_store_dep():
    """Get vector store instance."""
    return get_vector_store()
