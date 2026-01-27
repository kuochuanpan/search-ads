"""Paper-related schemas for API request/response models."""

from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field
import json


class PaperRead(BaseModel):
    """Paper response schema."""

    bibcode: str
    title: str
    abstract: Optional[str] = None
    authors: Optional[List[str]] = None  # Parsed from JSON
    year: Optional[int] = None
    journal: Optional[str] = None
    volume: Optional[str] = None
    pages: Optional[str] = None
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    citation_count: Optional[int] = None
    bibtex: Optional[str] = None
    bibitem_aastex: Optional[str] = None
    pdf_url: Optional[str] = None
    pdf_path: Optional[str] = None
    pdf_embedded: bool = False
    is_my_paper: bool = False
    created_at: datetime
    updated_at: datetime
    # Computed fields
    has_note: bool = False
    projects: List[str] = []
    first_author: Optional[str] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_db_model(cls, paper, has_note: bool = False, projects: List[str] = None):
        """Create from database Paper model."""
        # Parse authors JSON
        authors_list = None
        if paper.authors:
            try:
                authors_list = json.loads(paper.authors)
            except json.JSONDecodeError:
                authors_list = None

        return cls(
            bibcode=paper.bibcode,
            title=paper.title,
            abstract=paper.abstract,
            authors=authors_list,
            year=paper.year,
            journal=paper.journal,
            volume=paper.volume,
            pages=paper.pages,
            doi=paper.doi,
            arxiv_id=paper.arxiv_id,
            citation_count=paper.citation_count,
            bibtex=paper.bibtex,
            bibitem_aastex=paper.bibitem_aastex,
            pdf_url=paper.pdf_url,
            pdf_path=paper.pdf_path,
            pdf_embedded=paper.pdf_embedded,
            is_my_paper=paper.is_my_paper,
            created_at=paper.created_at,
            updated_at=paper.updated_at,
            has_note=has_note,
            projects=projects or [],
            first_author=paper.first_author,
        )


class PaperListResponse(BaseModel):
    """Response for paper list endpoint."""

    papers: List[PaperRead]
    total: int
    limit: int
    offset: int


class PaperFilters(BaseModel):
    """Filters for paper list endpoint."""

    project: Optional[str] = None
    year_min: Optional[int] = None
    year_max: Optional[int] = None
    min_citations: Optional[int] = None
    has_pdf: Optional[bool] = None
    pdf_embedded: Optional[bool] = None
    is_my_paper: Optional[bool] = None
    has_note: Optional[bool] = None
    search: Optional[str] = None
    sort_by: Literal["title", "year", "citation_count", "created_at", "updated_at"] = "created_at"
    sort_order: Literal["asc", "desc"] = "desc"


class ToggleMyPaperRequest(BaseModel):
    """Request to toggle my paper status."""

    is_my_paper: bool


class PaperBulkActionRequest(BaseModel):
    """Request for bulk paper actions."""

    bibcodes: List[str]


class PaperBulkActionResponse(BaseModel):
    """Response for bulk paper actions."""

    success: bool
    processed: int
    failed: int
    errors: List[str] = []
