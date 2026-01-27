"""Project-related schemas for API request/response models."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    """Request schema for creating a project."""

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None


class ProjectRead(BaseModel):
    """Response schema for a project."""

    name: str
    description: Optional[str] = None
    created_at: datetime
    paper_count: int = 0

    class Config:
        from_attributes = True

    @classmethod
    def from_db_model(cls, project, paper_count: int = 0):
        """Create from database Project model."""
        return cls(
            name=project.name,
            description=project.description,
            created_at=project.created_at,
            paper_count=paper_count,
        )


class ProjectListResponse(BaseModel):
    """Response for project list endpoint."""

    projects: List[ProjectRead]
    total: int


class AddPaperToProject(BaseModel):
    """Request to add a paper to a project."""

    bibcode: str


class AddPapersToProject(BaseModel):
    """Request to add multiple papers to a project."""

    bibcodes: List[str]


class RemovePaperFromProject(BaseModel):
    """Request to remove a paper from a project."""

    bibcode: str
