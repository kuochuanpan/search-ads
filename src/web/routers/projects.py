"""Projects API router."""

from fastapi import APIRouter, Depends, HTTPException

from src.db.repository import ProjectRepository
from src.web.dependencies import get_project_repo
from src.web.schemas.project import (
    ProjectCreate,
    ProjectRead,
    ProjectListResponse,
    AddPaperToProject,
    AddPapersToProject,
)
from src.web.schemas.common import MessageResponse

router = APIRouter()


@router.get("/", response_model=ProjectListResponse)
async def list_projects(
    project_repo: ProjectRepository = Depends(get_project_repo),
):
    """List all projects."""
    projects = project_repo.get_all()

    project_reads = []
    for project in projects:
        paper_bibcodes = project_repo.get_project_papers(project.name)
        project_reads.append(ProjectRead.from_db_model(project, paper_count=len(paper_bibcodes)))

    return ProjectListResponse(
        projects=project_reads,
        total=len(project_reads),
    )


@router.post("/", response_model=ProjectRead)
async def create_project(
    request: ProjectCreate,
    project_repo: ProjectRepository = Depends(get_project_repo),
):
    """Create a new project."""
    # Check if project already exists
    existing = project_repo.get(request.name)
    if existing:
        raise HTTPException(status_code=400, detail=f"Project already exists: {request.name}")

    project = project_repo.create(request.name, request.description)
    return ProjectRead.from_db_model(project, paper_count=0)


@router.get("/{name}", response_model=ProjectRead)
async def get_project(
    name: str,
    project_repo: ProjectRepository = Depends(get_project_repo),
):
    """Get a project by name."""
    project = project_repo.get(name)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project not found: {name}")

    paper_bibcodes = project_repo.get_project_papers(name)
    return ProjectRead.from_db_model(project, paper_count=len(paper_bibcodes))


@router.delete("/{name}", response_model=MessageResponse)
async def delete_project(
    name: str,
    delete_papers: bool = False,
    project_repo: ProjectRepository = Depends(get_project_repo),
):
    """Delete a project and optionally its papers."""
    success, papers_deleted = project_repo.delete(name, delete_papers=delete_papers)
    if not success:
        raise HTTPException(status_code=404, detail=f"Project not found: {name}")

    message = f"Project '{name}' deleted"
    if delete_papers and papers_deleted > 0:
        message += f" along with {papers_deleted} paper(s)"

    return MessageResponse(message=message)


@router.post("/{name}/papers", response_model=MessageResponse)
async def add_paper_to_project(
    name: str,
    request: AddPaperToProject,
    project_repo: ProjectRepository = Depends(get_project_repo),
):
    """Add a paper to a project."""
    # Check if project exists
    project = project_repo.get(name)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project not found: {name}")

    project_repo.add_paper(name, request.bibcode)
    return MessageResponse(message=f"Paper {request.bibcode} added to project '{name}'")


@router.post("/{name}/papers/bulk", response_model=MessageResponse)
async def add_papers_to_project(
    name: str,
    request: AddPapersToProject,
    project_repo: ProjectRepository = Depends(get_project_repo),
):
    """Add multiple papers to a project."""
    # Check if project exists
    project = project_repo.get(name)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project not found: {name}")

    for bibcode in request.bibcodes:
        project_repo.add_paper(name, bibcode)

    return MessageResponse(message=f"Added {len(request.bibcodes)} paper(s) to project '{name}'")


@router.get("/{name}/papers")
async def get_project_papers(
    name: str,
    project_repo: ProjectRepository = Depends(get_project_repo),
):
    """Get all paper bibcodes in a project."""
    # Check if project exists
    project = project_repo.get(name)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project not found: {name}")

    bibcodes = project_repo.get_project_papers(name)
    return {"project": name, "bibcodes": bibcodes, "count": len(bibcodes)}
