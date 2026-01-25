"""Citations API router."""

from fastapi import APIRouter, Depends, HTTPException

from src.db.repository import CitationRepository, PaperRepository
from src.web.dependencies import get_citation_repo, get_paper_repo

router = APIRouter()


@router.get("/{bibcode}/references")
async def get_references(
    bibcode: str,
    citation_repo: CitationRepository = Depends(get_citation_repo),
    paper_repo: PaperRepository = Depends(get_paper_repo),
):
    """Get papers that this paper cites (references)."""
    # Check if paper exists
    paper = paper_repo.get(bibcode)
    if not paper:
        raise HTTPException(status_code=404, detail=f"Paper not found: {bibcode}")

    references = citation_repo.get_references(bibcode)
    return {
        "bibcode": bibcode,
        "references": references,
        "count": len(references),
    }


@router.get("/{bibcode}/citations")
async def get_citations(
    bibcode: str,
    citation_repo: CitationRepository = Depends(get_citation_repo),
    paper_repo: PaperRepository = Depends(get_paper_repo),
):
    """Get papers that cite this paper (citations)."""
    # Check if paper exists
    paper = paper_repo.get(bibcode)
    if not paper:
        raise HTTPException(status_code=404, detail=f"Paper not found: {bibcode}")

    citations = citation_repo.get_citations(bibcode)
    return {
        "bibcode": bibcode,
        "citations": citations,
        "count": len(citations),
    }


@router.get("/{bibcode}/has-references")
async def has_references(
    bibcode: str,
    citation_repo: CitationRepository = Depends(get_citation_repo),
):
    """Check if we have loaded references for this paper."""
    return {
        "bibcode": bibcode,
        "has_references": citation_repo.has_references(bibcode),
    }


@router.get("/{bibcode}/has-citations")
async def has_citations(
    bibcode: str,
    citation_repo: CitationRepository = Depends(get_citation_repo),
):
    """Check if we have loaded citations for this paper."""
    return {
        "bibcode": bibcode,
        "has_citations": citation_repo.has_citations(bibcode),
    }
