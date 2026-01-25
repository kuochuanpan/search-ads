"""Search API router."""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from src.db.repository import PaperRepository
from src.web.dependencies import (
    get_paper_repo,
    get_ads_client,
    get_llm_client,
    get_vector_store_dep,
)
from src.web.schemas.paper import PaperRead

router = APIRouter()


class SearchRequest(BaseModel):
    """Search request body."""
    query: str
    limit: int = 20


class SemanticSearchResult(BaseModel):
    """Result from semantic search."""
    bibcode: str
    distance: float
    title: Optional[str] = None
    year: Optional[int] = None
    first_author: Optional[str] = None


class SearchResponse(BaseModel):
    """Search response."""
    query: str
    results: List[SemanticSearchResult]
    count: int


@router.post("/local")
async def search_local(
    request: SearchRequest,
    paper_repo: PaperRepository = Depends(get_paper_repo),
):
    """Search papers in local database by title and abstract."""
    papers = paper_repo.search_by_text(request.query, limit=request.limit)

    return {
        "query": request.query,
        "results": [
            {
                "bibcode": p.bibcode,
                "title": p.title,
                "year": p.year,
                "first_author": p.first_author,
                "citation_count": p.citation_count,
            }
            for p in papers
        ],
        "count": len(papers),
    }


@router.post("/semantic", response_model=SearchResponse)
async def search_semantic(
    request: SearchRequest,
    min_year: Optional[int] = Query(default=None),
    min_citations: Optional[int] = Query(default=None),
    vector_store=Depends(get_vector_store_dep),
):
    """Semantic search using vector embeddings."""
    try:
        results = vector_store.search(
            request.query,
            n_results=request.limit,
            min_year=min_year,
            min_citations=min_citations,
        )

        search_results = []
        for bibcode, distance, metadata, document in results:
            search_results.append(SemanticSearchResult(
                bibcode=bibcode,
                distance=distance,
                title=metadata.get("title"),
                year=metadata.get("year"),
                first_author=metadata.get("first_author"),
            ))

        return SearchResponse(
            query=request.query,
            results=search_results,
            count=len(search_results),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post("/pdf")
async def search_pdf(
    request: SearchRequest,
    bibcode: Optional[str] = Query(default=None, description="Filter to specific paper"),
    vector_store=Depends(get_vector_store_dep),
):
    """Search through embedded PDF content."""
    try:
        results = vector_store.search_pdf(
            request.query,
            n_results=request.limit,
            bibcode=bibcode,
        )

        return {
            "query": request.query,
            "results": [
                {
                    "bibcode": r[0],
                    "distance": r[1],
                    "metadata": r[2],
                    "text_snippet": r[3][:500] if r[3] else None,  # Truncate text
                }
                for r in results
            ],
            "count": len(results),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF search failed: {str(e)}")


@router.post("/ads")
async def search_ads(
    request: SearchRequest,
    ads_client=Depends(get_ads_client),
):
    """Search NASA ADS for papers."""
    try:
        papers = ads_client.search(request.query, max_results=request.limit)

        return {
            "query": request.query,
            "results": [
                {
                    "bibcode": p.bibcode,
                    "title": p.title,
                    "year": p.year,
                    "first_author": p.first_author,
                    "citation_count": p.citation_count,
                    "abstract": p.abstract[:500] if p.abstract else None,
                }
                for p in papers
            ],
            "count": len(papers),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ADS search failed: {str(e)}")
