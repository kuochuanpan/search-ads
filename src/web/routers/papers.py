"""Papers API router."""

import json

from typing import Optional, Literal
from fastapi import APIRouter, Depends, HTTPException, Query

from src.db.repository import PaperRepository, NoteRepository, ProjectRepository
from src.core.ads_client import ADSClient
from src.web.dependencies import get_paper_repo, get_note_repo, get_project_repo, get_ads_client
from src.web.schemas.paper import (
    PaperRead,
    PaperListResponse,
    ToggleMyPaperRequest,
    PaperBulkActionRequest,
    PaperBulkActionResponse,
)
from src.web.schemas.common import MessageResponse

router = APIRouter()


@router.get("/", response_model=PaperListResponse)
async def list_papers(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    project: Optional[str] = Query(default=None),
    year_min: Optional[int] = Query(default=None),
    year_max: Optional[int] = Query(default=None),
    min_citations: Optional[int] = Query(default=None),
    has_pdf: Optional[bool] = Query(default=None),
    pdf_embedded: Optional[bool] = Query(default=None),
    is_my_paper: Optional[bool] = Query(default=None),
    has_note: Optional[bool] = Query(default=None),
    search: Optional[str] = Query(default=None),
    sort_by: Literal["title", "year", "citation_count", "created_at", "updated_at", "authors", "journal"] = Query(default="created_at"),
    sort_order: Literal["asc", "desc"] = Query(default="desc"),
    paper_repo: PaperRepository = Depends(get_paper_repo),
    note_repo: NoteRepository = Depends(get_note_repo),
    project_repo: ProjectRepository = Depends(get_project_repo),
):
    """List papers with optional filters, sorting, and pagination."""
    # Get papers from repository
    # Note: The repository's get_all has limited filtering, so we'll do some filtering in Python
    papers = paper_repo.get_all(
        limit=1000,  # Get more to filter
        offset=0,
        project=project,
        year_min=year_min,
        year_max=year_max,
        min_citations=min_citations,
    )

    # Additional filtering
    if has_pdf is not None:
        papers = [p for p in papers if (p.pdf_path is not None) == has_pdf]

    if pdf_embedded is not None:
        papers = [p for p in papers if p.pdf_embedded == pdf_embedded]

    if is_my_paper is not None:
        papers = [p for p in papers if p.is_my_paper == is_my_paper]

    if has_note is not None:
        papers = [p for p in papers if (note_repo.get(p.bibcode) is not None) == has_note]

    if search:
        search_lower = search.lower()
        papers = [
            p for p in papers
            if search_lower in (p.title or "").lower()
            or search_lower in (p.abstract or "").lower()
            or search_lower in (p.authors or "").lower()
        ]

    # Sorting
    reverse = sort_order == "desc"
    if sort_by == "title":
        papers.sort(key=lambda p: (p.title or "").lower(), reverse=reverse)
    elif sort_by == "year":
        papers.sort(key=lambda p: p.year or 0, reverse=reverse)
    elif sort_by == "citation_count":
        papers.sort(key=lambda p: p.citation_count or 0, reverse=reverse)
    elif sort_by == "created_at":
        papers.sort(key=lambda p: p.created_at, reverse=reverse)
    elif sort_by == "updated_at":
        papers.sort(key=lambda p: p.updated_at, reverse=reverse)
    elif sort_by == "journal":
        papers.sort(key=lambda p: (p.journal or "").lower(), reverse=reverse)
    elif sort_by == "authors":
        def get_authors_sort_key(p):
            if not p.authors:
                return ""
            try:
                authors_list = json.loads(p.authors)
                # Join authors for sorting, or use first author
                return " ".join(authors_list).lower() if authors_list else ""
            except (json.JSONDecodeError, TypeError):
                return ""
        
        papers.sort(key=get_authors_sort_key, reverse=reverse)

    # Get total before pagination
    total = len(papers)

    # Apply pagination
    papers = papers[offset:offset + limit]

    # Convert to response models with additional info
    paper_reads = []
    for paper in papers:
        # Check if paper has a note
        note = note_repo.get(paper.bibcode)
        paper_has_note = note is not None

        # Get projects for this paper
        projects = project_repo.get_paper_projects(paper.bibcode)

        paper_reads.append(PaperRead.from_db_model(paper, has_note=paper_has_note, projects=projects))

    return PaperListResponse(
        papers=paper_reads,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/count")
async def count_papers(
    paper_repo: PaperRepository = Depends(get_paper_repo),
):
    """Get total paper count."""
    return {"count": paper_repo.count()}


@router.get("/mine", response_model=PaperListResponse)
async def list_my_papers(
    limit: int = Query(default=100, ge=1, le=1000),
    paper_repo: PaperRepository = Depends(get_paper_repo),
    note_repo: NoteRepository = Depends(get_note_repo),
    project_repo: ProjectRepository = Depends(get_project_repo),
):
    """List papers marked as user's own papers."""
    papers = paper_repo.get_my_papers(limit=limit)

    paper_reads = []
    for paper in papers:
        note = note_repo.get(paper.bibcode)
        has_note = note is not None
        projects = project_repo.get_paper_projects(paper.bibcode)
        paper_reads.append(PaperRead.from_db_model(paper, has_note=has_note, projects=projects))

    return PaperListResponse(
        papers=paper_reads,
        total=len(paper_reads),
        limit=limit,
        offset=0,
    )


@router.get("/{bibcode}", response_model=PaperRead)
async def get_paper(
    bibcode: str,
    paper_repo: PaperRepository = Depends(get_paper_repo),
    note_repo: NoteRepository = Depends(get_note_repo),
    project_repo: ProjectRepository = Depends(get_project_repo),
):
    """Get a single paper by bibcode."""
    paper = paper_repo.get(bibcode)
    if not paper:
        raise HTTPException(status_code=404, detail=f"Paper not found: {bibcode}")

    note = note_repo.get(bibcode)
    has_note = note is not None
    projects = project_repo.get_paper_projects(bibcode)

    return PaperRead.from_db_model(paper, has_note=has_note, projects=projects)


@router.delete("/{bibcode}", response_model=MessageResponse)
async def delete_paper(
    bibcode: str,
    paper_repo: PaperRepository = Depends(get_paper_repo),
):
    """Delete a paper by bibcode."""
    success = paper_repo.delete(bibcode)
    if not success:
        raise HTTPException(status_code=404, detail=f"Paper not found: {bibcode}")

    return MessageResponse(message=f"Paper {bibcode} deleted successfully")


@router.patch("/{bibcode}/mine", response_model=MessageResponse)
async def toggle_my_paper(
    bibcode: str,
    request: ToggleMyPaperRequest,
    paper_repo: PaperRepository = Depends(get_paper_repo),
):
    """Toggle whether a paper is marked as user's own paper."""
    success = paper_repo.set_my_paper(bibcode, request.is_my_paper)
    if not success:
        raise HTTPException(status_code=404, detail=f"Paper not found: {bibcode}")

    status = "marked as your paper" if request.is_my_paper else "unmarked as your paper"
    return MessageResponse(message=f"Paper {bibcode} {status}")


@router.post("/bulk/delete", response_model=PaperBulkActionResponse)
async def bulk_delete_papers(
    request: PaperBulkActionRequest,
    paper_repo: PaperRepository = Depends(get_paper_repo),
):
    """Delete multiple papers."""
    processed = 0
    failed = 0
    errors = []

    for bibcode in request.bibcodes:
        success = paper_repo.delete(bibcode)
        if success:
            processed += 1
        else:
            failed += 1
            errors.append(f"Paper not found: {bibcode}")

    return PaperBulkActionResponse(
        success=failed == 0,
        processed=processed,
        failed=failed,
        errors=errors,
    )


@router.post("/bulk/mine", response_model=PaperBulkActionResponse)
async def bulk_mark_my_papers(
    request: PaperBulkActionRequest,
    is_my_paper: bool = Query(default=True),
    paper_repo: PaperRepository = Depends(get_paper_repo),
):
    """Mark/unmark multiple papers as user's own papers."""
    processed = 0
    failed = 0
    errors = []

    for bibcode in request.bibcodes:
        success = paper_repo.set_my_paper(bibcode, is_my_paper)
        if success:
            processed += 1
        else:
            failed += 1
            errors.append(f"Paper not found: {bibcode}")

    return PaperBulkActionResponse(
        success=failed == 0,
        processed=processed,
        failed=failed,
        errors=errors,
    )


@router.get("/{bibcode}/citations-export")
async def get_citation_export(
    bibcode: str,
    paper_repo: PaperRepository = Depends(get_paper_repo),
    ads_client: ADSClient = Depends(get_ads_client),
):
    """Get BibTeX and AASTeX citation formats for a paper.

    Fetches from ADS if not cached in database.
    """
    paper = paper_repo.get(bibcode)
    if not paper:
        raise HTTPException(status_code=404, detail=f"Paper not found: {bibcode}")

    bibtex = paper.bibtex
    bibitem_aastex = paper.bibitem_aastex
    updated = False

    # Fetch bibtex from ADS if not cached
    if not bibtex:
        bibtex = ads_client.generate_bibtex(bibcode)
        if bibtex:
            paper.bibtex = bibtex
            updated = True

    # Fetch aastex from ADS if not cached
    if not bibitem_aastex:
        bibitem_aastex = ads_client.generate_aastex(bibcode)
        if bibitem_aastex:
            paper.bibitem_aastex = bibitem_aastex
            updated = True

    # Save updates to database
    if updated:
        paper_repo.add(paper, embed=False)

    return {
        "bibcode": bibcode,
        "bibtex": bibtex,
        "bibitem_aastex": bibitem_aastex,
    }
