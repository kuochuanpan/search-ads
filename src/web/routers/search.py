"""Search API router."""

from typing import Optional, List, AsyncGenerator
import json
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
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
        # Batch fetch papers and notes
        bibcodes = [r["bibcode"] for r in results]
        papers = repo.get_batch(bibcodes)
        notes = note_repo.get_batch(bibcodes)
        
        paper_map = {p.bibcode: p for p in papers}
        note_map = {n.bibcode: n for n in notes}

        # Re-score results
        scored_results = []
        for result in results:
            bibcode = result["bibcode"]
            raw_distance = result["distance"] or 1.0 # Handle None
            
            # 1. Fetch Paper status
            paper = paper_map.get(bibcode)
            is_my_paper = paper.is_my_paper if paper else False
            
            # 2. Check for Notes
            has_note = note_map.get(bibcode) is not None
            
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
    llm_client=Depends(get_llm_client),
):
    """Search NASA ADS for papers.
    
    If query is natural language, uses LLM to extract keywords.
    """
    try:
        # Check if query looks like a structured ADS query
        # ADS queries often contain field qualifiers like "author:", "year:", etc.
        # or operators like "AND", "OR".
        # If it looks like a simple sentence, use LLM to extract keywords.
        query = request.query
        
        # Simple heuristic: if no common ADS operators/fields and > 3 words, try extraction
        is_structured = any(x in query.lower() for x in ["author:", "year:", "bibcode:", "title:", "abs:", " AND ", " OR "])
        
        if not is_structured and len(query.split()) > 3 and llm_client:
            try:
                # Use strict keyword extraction
                keywords = await asyncio.to_thread(llm_client.extract_keywords_only, query)
                if keywords:
                    # Construct a new query with keywords
                    # Using simple space join (implicit AND/OR depending on ADS config, typically defaults to AND in modern search)
                    # ADS default operator is often AND for simple terms
                    query = " ".join(keywords)
                    print(f"Refined natural language query '{request.query}' to: '{query}'")
            except Exception as e:
                print(f"Keyword extraction failed: {e}")
                # Fallback to original query

        papers = ads_client.search(query, max_results=request.limit)

        return {
            "query": request.query,
            "transformed_query": query if query != request.query else None,
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


@router.post("/ads/stream")
async def search_ads_stream(
    request: SearchRequest,
    ads_client=Depends(get_ads_client),
    llm_client=Depends(get_llm_client),
):
    """Search NASA ADS for papers with streaming results."""
    
    async def event_generator():
        try:
            # First yield a starting message
            yield json.dumps({
                "type": "progress",
                "message": f"Searching ADS for '{request.query}'..."
            }) + "\n"

            query = request.query
            
            # Simple heuristic: if no common ADS operators/fields and > 3 words, try extraction
            is_structured = any(x in query.lower() for x in ["author:", "year:", "bibcode:", "title:", "abs:", " AND ", " OR "])
            
            if not is_structured and len(query.split()) > 3 and llm_client:
                try:
                    yield json.dumps({
                        "type": "progress",
                        "message": "Analyzing natural language query..."
                    }) + "\n"
                    
                    # Use strict keyword extraction
                    keywords = await asyncio.to_thread(llm_client.extract_keywords_only, query)
                    if keywords:
                        query = " ".join(keywords)
                        yield json.dumps({
                            "type": "progress",
                            "message": f"Refined query: {query}"
                        }) + "\n"
                except Exception as e:
                    print(f"Keyword extraction failed: {e}")
            
            # Use search_stream method which yields results
            # We iterate it. Since it's a synchronous generator, we wrap iteration if needed, 
            # but standard iteration in async helper is usually fine for short bursts, 
            # though strictly blocking.
            # Ideally we'd run the whole generator in a thread but that's complex to stream back.
            # For now, we iterate directly as it yields quickly per item (mostly).
            # If ads_client.search_stream does network calls per item (it doesn't, it fetches all then yields),
            # then it blocks once at the start.
            
            # Wait, my fix for search_stream calls list(search) internally, so it blocks at the START.
            # To be non-blocking, we should wrap the call? 
            # But we can't wrap a generator creation easily in to_thread and then iterate it async 
            # unless we consume it all.
            # For now, we accept the initial block.
            
            count = 0
            # Use the new search_stream method
            for paper in ads_client.search_stream(query, limit=request.limit):
                count += 1
                
                # Convert paper to result format
                data = {
                    "bibcode": paper.bibcode,
                    "title": paper.title,
                    "year": paper.year,
                    "first_author": paper.first_author,
                    "citation_count": paper.citation_count,
                    "abstract": paper.abstract[:500] if paper.abstract else None,
                }
                
                yield json.dumps({
                    "type": "result",
                    "data": data,
                    "count": count
                }) + "\n"
                
                # Yield to event loop
                await asyncio.sleep(0.0)

            yield json.dumps({
                "type": "done",
                "total": count
            }) + "\n"
            
        except Exception as e:
            yield json.dumps({
                "type": "error",
                "message": str(e)
            }) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")


@router.post("/semantic/stream")
async def search_semantic_stream(
    request: SearchRequest,
    min_year: Optional[int] = Query(default=None),
    min_citations: Optional[int] = Query(default=None),
    vector_store=Depends(get_vector_store_dep),
):
    """Semantic search using vector embeddings with streaming progress."""
    
    async def event_generator():
        try:
            yield json.dumps({
                "type": "progress",
                "message": "Performing vector search..."
            }) + "\n"
            await asyncio.sleep(0)

            results = vector_store.search(
                request.query,
                n_results=request.limit * 2,  # Fetch more to allow for re-ranking
                min_year=min_year,
                min_citations=min_citations,
            )

            if not results:
                yield json.dumps({"type": "done", "total": 0}) + "\n"
                return

            yield json.dumps({
                "type": "progress",
                "message": f"Found {len(results)} matches. Re-ranking..."
            }) + "\n"
            await asyncio.sleep(0)

            # Re-ranking logic
            from src.db.repository import PaperRepository, NoteRepository
            repo = PaperRepository()
            note_repo = NoteRepository()

            # Batch fetch papers and notes
            bibcodes_re_rank = [r["bibcode"] for r in results]
            papers = repo.get_batch(bibcodes_re_rank)
            notes = note_repo.get_batch(bibcodes_re_rank)
            
            paper_map = {p.bibcode: p for p in papers}
            note_map = {n.bibcode: n for n in notes}

            scored_results = []
            total = len(results)
            
            for i, result in enumerate(results):
                # Report progress every few items
                if i % 5 == 0:
                    yield json.dumps({
                        "type": "progress",
                        "message": f"Processing result {i+1}/{total}...",
                        "current": i + 1,
                        "total": total
                    }) + "\n"
                    await asyncio.sleep(0)

                bibcode = result["bibcode"]
                raw_distance = result["distance"] or 1.0
                
                paper = paper_map.get(bibcode)
                is_my_paper = paper.is_my_paper if paper else False
                has_note = note_map.get(bibcode) is not None
                
                multiplier = 1.0
                if is_my_paper:
                    multiplier *= 0.8
                if has_note:
                    multiplier *= 0.9
                    
                new_distance = raw_distance * multiplier
                
                search_result = {
                    "bibcode": bibcode,
                    "distance": new_distance,
                    "title": result["metadata"].get("title"),
                    "year": result["metadata"].get("year"),
                    "first_author": result["metadata"].get("first_author"),
                    # Add extra fields for UI display that aren't in SemanticSearchResult model
                    "citation_count": paper.citation_count if paper else None,
                    "in_library": True, # It's local search
                    "relevance_score": 1.0 - min(new_distance, 1.0) # Approx score
                }
                scored_results.append(search_result)

            # Re-sort
            scored_results.sort(key=lambda x: x["distance"])
            final_results = scored_results[:request.limit]

            # Yield final results one by one or as a batch? 
            # Re-ranking means we can't stream results until we have them all sorted.
            # But we streamed progress of re-ranking.
            
            yield json.dumps({
                "type": "progress",
                "message": "Finalizing results..."
            }) + "\n"

            for res in final_results:
                yield json.dumps({
                    "type": "result",
                    "data": res
                }) + "\n"

            yield json.dumps({
                "type": "done",
                "total": len(final_results)
            }) + "\n"

        except Exception as e:
            import traceback
            traceback.print_exc()
            yield json.dumps({
                "type": "error",
                "message": str(e)
            }) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")
