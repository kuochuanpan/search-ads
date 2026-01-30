"""Search-related schemas for the unified search API."""

from typing import Optional, List, Literal
from pydantic import BaseModel, Field


class UnifiedSearchRequest(BaseModel):
    """Request for the unified search endpoint."""

    query: str = Field(..., description="Search query text")
    mode: Literal["natural", "keywords"] = Field(
        default="natural", description="Search mode"
    )
    scope: Literal["library", "pdf", "ads"] = Field(
        default="library", description="Search scope"
    )
    limit: int = Field(default=100, ge=1, le=500)
    offset: int = Field(default=0, ge=0)
    min_year: Optional[int] = None
    max_year: Optional[int] = None
    min_citations: Optional[int] = None


class AIAnalysis(BaseModel):
    """AI analysis of the search query."""

    topic: str = ""
    claim: str = ""
    citation_type_needed: str = "general"
    keywords: List[str] = []
    reasoning: str = ""


class SearchResultItem(BaseModel):
    """A single search result."""

    bibcode: str
    title: str
    year: Optional[int] = None
    first_author: Optional[str] = None
    authors: Optional[List[str]] = None
    abstract: Optional[str] = None
    citation_count: Optional[int] = None
    journal: Optional[str] = None
    in_library: bool = False
    relevance_score: Optional[float] = None
    relevance_explanation: Optional[str] = None
    citation_type: Optional[str] = None
    source: str = "library"


class UnifiedSearchResponse(BaseModel):
    """Response from the unified search endpoint."""

    results: List[SearchResultItem]
    total_available: int
    offset: int
    limit: int
    has_more: bool
    ai_analysis: Optional[AIAnalysis] = None
    query_used: str = ""
