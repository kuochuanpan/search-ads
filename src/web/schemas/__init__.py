"""Pydantic schemas for API request/response models."""

from src.web.schemas.paper import (
    PaperRead,
    PaperListResponse,
    PaperFilters,
)
from src.web.schemas.project import (
    ProjectCreate,
    ProjectRead,
    ProjectListResponse,
    AddPaperToProject,
)
from src.web.schemas.common import (
    PaginationParams,
    MessageResponse,
    ErrorResponse,
)

__all__ = [
    "PaperRead",
    "PaperListResponse",
    "PaperFilters",
    "ProjectCreate",
    "ProjectRead",
    "ProjectListResponse",
    "AddPaperToProject",
    "PaginationParams",
    "MessageResponse",
    "ErrorResponse",
]
