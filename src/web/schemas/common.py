"""Common schemas for API responses."""

from typing import Optional
from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    """Pagination parameters for list endpoints."""

    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str
    success: bool = True


class ErrorResponse(BaseModel):
    """Error response schema."""

    error: str
    detail: Optional[str] = None
    success: bool = False


class StatsResponse(BaseModel):
    """Database statistics response."""

    total_papers: int
    total_projects: int
    total_notes: int
    papers_with_pdf: int
    papers_with_embedded_pdf: int
    my_papers_count: int


class ApiUsageResponse(BaseModel):
    """API usage statistics response."""

    date: str
    ads_calls: int
    openai_calls: int
    anthropic_calls: int
