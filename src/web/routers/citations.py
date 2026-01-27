"""Citations API router."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from src.db.repository import CitationRepository, PaperRepository
from src.core.ads_client import ADSClient
from src.web.dependencies import get_citation_repo, get_paper_repo, get_ads_client

router = APIRouter()


class PaperSummary(BaseModel):
    """Summary of a paper for references/citations list."""

    bibcode: str
    title: Optional[str] = None
    authors: Optional[str] = None
    year: Optional[int] = None
    journal: Optional[str] = None
    citation_count: Optional[int] = None
    in_library: bool = False


class ReferencesResponse(BaseModel):
    """Response for references endpoint."""

    bibcode: str
    title: Optional[str] = None
    references: list[PaperSummary]
    count: int
    total: Optional[int] = None
    page: int = 1
    has_more: bool = False


class CitationsResponse(BaseModel):
    """Response for citations endpoint."""

    bibcode: str
    title: Optional[str] = None
    citations: list[PaperSummary]
    count: int
    total: Optional[int] = None
    page: int = 1
    has_more: bool = False


@router.get("/{bibcode}/references", response_model=ReferencesResponse)
async def get_references(
    bibcode: str,
    fetch_from_ads: bool = Query(False, description="Fetch fresh data from ADS API"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of references to return"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    save: bool = Query(False, description="Save fetched papers to library"),
    citation_repo: CitationRepository = Depends(get_citation_repo),
    paper_repo: PaperRepository = Depends(get_paper_repo),
    ads_client: ADSClient = Depends(get_ads_client),
):
    """Get papers that this paper cites (references).

    By default, returns references from the local database.
    Use fetch_from_ads=true to fetch fresh data from ADS API.
    """
    # Get paper info
    paper = paper_repo.get(bibcode)
    title = paper.title if paper else None

    if fetch_from_ads:
        # Fetch from ADS
        try:
            # ADS doesn't support true pagination for references query,
            # so we fetch all up to limit
            offset = (page - 1) * limit
            ref_papers = ads_client.fetch_references(bibcode, limit=limit + offset, save=save)

            # Apply pagination manually
            ref_papers = ref_papers[offset : offset + limit]

            references = []
            for p in ref_papers:
                in_library = paper_repo.get(p.bibcode) is not None
                references.append(
                    PaperSummary(
                        bibcode=p.bibcode,
                        title=p.title,
                        authors=p.authors,
                        year=p.year,
                        journal=p.journal,
                        citation_count=p.citation_count,
                        in_library=in_library,
                    )
                )

            return ReferencesResponse(
                bibcode=bibcode,
                title=title,
                references=references,
                count=len(references),
                page=page,
                has_more=len(ref_papers) == limit,
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error fetching from ADS: {str(e)}")
    else:
        # Get from local database
        ref_bibcodes = citation_repo.get_references(bibcode)

        # Apply pagination
        offset = (page - 1) * limit
        paginated_bibcodes = ref_bibcodes[offset : offset + limit]

        references = []
        for ref_bibcode in paginated_bibcodes:
            p = paper_repo.get(ref_bibcode)
            if p:
                references.append(
                    PaperSummary(
                        bibcode=p.bibcode,
                        title=p.title,
                        authors=p.authors,
                        year=p.year,
                        journal=p.journal,
                        citation_count=p.citation_count,
                        in_library=True,
                    )
                )
            else:
                # Paper not in library but we have the reference relationship
                references.append(
                    PaperSummary(
                        bibcode=ref_bibcode,
                        in_library=False,
                    )
                )

        return ReferencesResponse(
            bibcode=bibcode,
            title=title,
            references=references,
            count=len(references),
            total=len(ref_bibcodes),
            page=page,
            has_more=offset + limit < len(ref_bibcodes),
        )


@router.get("/{bibcode}/citations", response_model=CitationsResponse)
async def get_citations(
    bibcode: str,
    fetch_from_ads: bool = Query(False, description="Fetch fresh data from ADS API"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of citations to return"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    save: bool = Query(False, description="Save fetched papers to library"),
    citation_repo: CitationRepository = Depends(get_citation_repo),
    paper_repo: PaperRepository = Depends(get_paper_repo),
    ads_client: ADSClient = Depends(get_ads_client),
):
    """Get papers that cite this paper (citations).

    By default, returns citations from the local database.
    Use fetch_from_ads=true to fetch fresh data from ADS API.
    Supports pagination with 100 papers per page by default.
    """
    # Get paper info
    paper = paper_repo.get(bibcode)
    title = paper.title if paper else None

    if fetch_from_ads:
        # Fetch from ADS
        try:
            # ADS doesn't support true pagination for citations query,
            # so we fetch all up to limit * page
            offset = (page - 1) * limit
            citing_papers = ads_client.fetch_citations(bibcode, limit=limit + offset, save=save)

            # Apply pagination manually
            citing_papers = citing_papers[offset : offset + limit]

            citations = []
            for p in citing_papers:
                in_library = paper_repo.get(p.bibcode) is not None
                citations.append(
                    PaperSummary(
                        bibcode=p.bibcode,
                        title=p.title,
                        authors=p.authors,
                        year=p.year,
                        journal=p.journal,
                        citation_count=p.citation_count,
                        in_library=in_library,
                    )
                )

            return CitationsResponse(
                bibcode=bibcode,
                title=title,
                citations=citations,
                count=len(citations),
                page=page,
                has_more=len(citing_papers) == limit,
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error fetching from ADS: {str(e)}")
    else:
        # Get from local database
        citing_bibcodes = citation_repo.get_citations(bibcode)

        # Apply pagination
        offset = (page - 1) * limit
        paginated_bibcodes = citing_bibcodes[offset : offset + limit]

        citations = []
        for citing_bibcode in paginated_bibcodes:
            p = paper_repo.get(citing_bibcode)
            if p:
                citations.append(
                    PaperSummary(
                        bibcode=p.bibcode,
                        title=p.title,
                        authors=p.authors,
                        year=p.year,
                        journal=p.journal,
                        citation_count=p.citation_count,
                        in_library=True,
                    )
                )
            else:
                # Paper not in library but we have the citation relationship
                citations.append(
                    PaperSummary(
                        bibcode=citing_bibcode,
                        in_library=False,
                    )
                )

        return CitationsResponse(
            bibcode=bibcode,
            title=title,
            citations=citations,
            count=len(citations),
            total=len(citing_bibcodes),
            page=page,
            has_more=offset + limit < len(citing_bibcodes),
        )


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
