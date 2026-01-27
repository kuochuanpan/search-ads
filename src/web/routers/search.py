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
            n_results=request.limit * 2,  # Fetch more to allow for re-ranking
            min_year=min_year,
            min_citations=min_citations,
        )

        if not results:
            return SearchResponse(query=request.query, results=[], count=0)

        # Extract bibcodes to fetch metadata needed for re-ranking
        bibcodes = [r["bibcode"] for r in results]
        
        # Get paper details (for is_my_paper)
        # We need to query the repo directly or assume metadata has it?
        # Vector store metadata stores 'is_my_paper' only if we added it. 
        # Current implementation of embed_paper in vector_store.py doesn't store is_my_paper in metadata default.
        # So we query repo.
        from src.db.repository import get_db, PaperRepository, NoteRepository
        
        # We'll use a new session to be safe, or reuse dependencies if cleaner. 
        # Since this is inside router, let's just use the dependencies if possible, but 
        # vector_store doesn't give us repo.
        # Let's instantiate repo here efficiently or fetch properties.
        
        # Optimization: Batch fetch is better, but for now simple loop or `in` query
        repo = PaperRepository()
        note_repo = NoteRepository()

        # Re-score results
        scored_results = []
        for result in results:
            bibcode = result["bibcode"]
            raw_distance = result["distance"] or 1.0 # Handle None
            
            # 1. Fetch Paper status
            paper = repo.get(bibcode)
            is_my_paper = paper.is_my_paper if paper else False
            
            # 2. Check for Notes
            has_note = note_repo.get(bibcode) is not None
            
            # Apply Weights (lower distance is better)
            # My Paper: 20% boost (0.8 multiplier)
            # Has Note: 10% boost (0.9 multiplier)
            
            multiplier = 1.0
            if is_my_paper:
                multiplier *= 0.8
            if has_note:
                multiplier *= 0.9
                
            new_distance = raw_distance * multiplier
            
            search_results = SemanticSearchResult(
                bibcode=bibcode,
                distance=new_distance,
                title=result["metadata"].get("title"),
                year=result["metadata"].get("year"),
                first_author=result["metadata"].get("first_author"),
            )
            scored_results.append(search_results)

        # Re-sort by new distance
        scored_results.sort(key=lambda x: x.distance)
        
        # Trim to requested limit
        final_results = scored_results[:request.limit]

        return SearchResponse(
            query=request.query,
            results=final_results,
            count=len(final_results),
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
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
                    "bibcode": r["bibcode"],
                    "distance": r["distance"],
                    "metadata": r.get("metadata", {}),
                    "text_snippet": r["document"][:500] if r.get("document") else None,  # Truncate text
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
