"""Search API router."""

from typing import Optional, List, AsyncGenerator
import json
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.db.repository import PaperRepository, NoteRepository
from src.web.dependencies import (
    get_paper_repo,
    get_ads_client,
    get_llm_client,
    get_vector_store_dep,
)
from src.web.schemas.paper import PaperRead
from src.web.schemas.search import (
    UnifiedSearchRequest,
    UnifiedSearchResponse,
    SearchResultItem as UnifiedResultItem,
    AIAnalysis,
)

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


def _extract_keywords_fallback(query: str) -> List[str]:
    """Fallback keyword extraction using regex and stopwords."""
    import re
    stopwords = {
        "that", "this", "with", "from", "have", "been", "were", "which",
        "their", "there", "about", "would", "could", "should", "these",
        "those", "other", "paper", "papers", "search", "find", "looking",
        "show", "give", "what", "where", "when", "why", "how"
    }
    words = re.findall(r"\b[a-zA-Z]{4,}\b", query.lower())
    keywords = [w for w in words if w not in stopwords][:5]
    if keywords:
        print(f"Using fallback keywords: {keywords}")
    return keywords


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
        
        if not is_structured and len(query.split()) > 3:
            keywords = []
            if llm_client:
                try:
                    # Use strict keyword extraction
                    keywords = await asyncio.to_thread(llm_client.extract_keywords_only, query)
                except Exception as e:
                    print(f"Keyword extraction failed: {e}")
            
            # Fallback if LLM extraction returned nothing or failed (and we have no keywords yet)
            if not keywords:
                keywords = _extract_keywords_fallback(query)

            if keywords:
                # Construct a new query with keywords
                query = " ".join(keywords)
                print(f"Refined natural language query '{request.query}' to: '{query}'")

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
            
            if not is_structured and len(query.split()) > 3:
                keywords = []
                if llm_client:
                    try:
                        yield json.dumps({
                            "type": "progress",
                            "message": "Analyzing natural language query..."
                        }) + "\n"
                        
                        # Use strict keyword extraction
                        keywords = await asyncio.to_thread(llm_client.extract_keywords_only, query)
                    except Exception as e:
                        print(f"Keyword extraction failed: {e}")
                
                # Fallback
                if not keywords:
                     yield json.dumps({
                        "type": "progress",
                        "message": "Extracting keywords..."
                    }) + "\n"
                     keywords = _extract_keywords_fallback(query)

                if keywords:
                    query = " ".join(keywords)
                    yield json.dumps({
                        "type": "progress",
                        "message": f"Refined query: {query}"
                    }) + "\n"
            
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


def _parse_authors(paper) -> Optional[List[str]]:
    """Parse authors JSON from a paper model."""
    if paper.authors:
        try:
            return json.loads(paper.authors)
        except (json.JSONDecodeError, TypeError):
            return [paper.authors] if isinstance(paper.authors, str) else None
    return None


@router.post("/unified", response_model=UnifiedSearchResponse)
async def search_unified(
    request: UnifiedSearchRequest,
    paper_repo: PaperRepository = Depends(get_paper_repo),
    ads_client=Depends(get_ads_client),
    llm_client=Depends(get_llm_client),
    vector_store=Depends(get_vector_store_dep),
):
    """Unified search endpoint supporting all mode/scope combinations.

    Modes: natural (LLM analysis + ranking), keywords (direct search)
    Scopes: library (abstracts), pdf (abstracts + pdf chunks), ads (NASA ADS API)
    """
    results: List[UnifiedResultItem] = []
    ai_analysis = None
    query_used = request.query
    total_available = 0

    # Step 1: For natural language mode, analyze query with LLM
    if request.mode == "natural":
        if llm_client:
            try:
                context_analysis = await asyncio.to_thread(
                    llm_client.analyze_context, request.query
                )
                ai_analysis = AIAnalysis(
                    topic=context_analysis.topic,
                    claim=context_analysis.claim,
                    citation_type_needed=context_analysis.citation_type.value,
                    keywords=context_analysis.keywords,
                    reasoning=context_analysis.reasoning,
                )
                # For ADS scope, use the LLM-generated search query
                if request.scope == "ads" and context_analysis.search_query:
                    query_used = context_analysis.search_query
            except Exception as e:
                print(f"LLM analysis failed: {e}")

        # Fallback for ADS if no refined query yet (LLM failed or missing)
        if request.scope == "ads" and query_used == request.query:
            # Check if likely natural language
            is_structured = any(x in request.query.lower() for x in ["author:", "year:", "bibcode:", "title:", "abs:", " AND ", " OR "])
            if not is_structured and len(request.query.split()) > 3:
                keywords = _extract_keywords_fallback(request.query)
                if keywords:
                    query_used = " ".join(keywords)
                    print(f"Unified fallback: Refined query to '{query_used}'")

    # Step 2: Search the selected scope
    seen_bibcodes = set()

    if request.scope == "library":
        results, total_available = await _search_library(
            request, query_used, vector_store, paper_repo, seen_bibcodes
        )

    elif request.scope == "pdf":
        results, total_available = await _search_pdf(
            request, query_used, vector_store, paper_repo, seen_bibcodes
        )

    elif request.scope == "ads":
        results, total_available = await _search_ads(
            request, query_used, ads_client, paper_repo, seen_bibcodes
        )

    # Step 3: For natural language mode, rank results with LLM
    if request.mode == "natural" and llm_client and results and ai_analysis:
        try:
            from src.db.models import Paper
            from src.core.llm_client import ContextAnalysis, CitationType

            papers_to_rank = []
            for r in results[:50]:
                authors_json = json.dumps(r.authors) if r.authors else None
                if not authors_json and r.first_author:
                    authors_json = json.dumps([r.first_author])
                p = Paper(
                    bibcode=r.bibcode,
                    title=r.title,
                    year=r.year,
                    abstract=r.abstract,
                    citation_count=r.citation_count,
                    authors=authors_json,
                )
                papers_to_rank.append(p)

            context = ContextAnalysis(
                topic=ai_analysis.topic,
                claim=ai_analysis.claim,
                citation_type=CitationType(ai_analysis.citation_type_needed.lower()),
                keywords=ai_analysis.keywords,
                search_query=request.query,
                reasoning=ai_analysis.reasoning,
            )

            ranked = await asyncio.to_thread(
                llm_client.rank_papers,
                papers_to_rank,
                request.query,
                context_analysis=context,
                top_k=len(papers_to_rank),
            )

            rank_map = {rp.paper.bibcode: rp for rp in ranked}
            for result in results:
                if result.bibcode in rank_map:
                    rp = rank_map[result.bibcode]
                    result.relevance_score = rp.relevance_score
                    result.relevance_explanation = rp.relevance_explanation
                    result.citation_type = rp.citation_type.value

            results.sort(key=lambda x: x.relevance_score or 0, reverse=True)
        except Exception as e:
            print(f"LLM ranking failed: {e}")

    has_more = total_available > request.offset + len(results)

    return UnifiedSearchResponse(
        results=results,
        total_available=total_available,
        offset=request.offset,
        limit=request.limit,
        has_more=has_more,
        ai_analysis=ai_analysis,
        query_used=query_used,
    )


async def _search_library(
    request: UnifiedSearchRequest,
    query: str,
    vector_store,
    paper_repo: PaperRepository,
    seen_bibcodes: set,
) -> tuple[List[UnifiedResultItem], int]:
    """Search local library via ChromaDB abstracts collection."""
    results = []
    try:
        # ChromaDB doesn't support offset, so fetch offset+limit and skip
        n_results = request.offset + request.limit
        semantic_results = await asyncio.to_thread(
            vector_store.search,
            query,
            n_results=n_results,
            min_year=request.min_year,
            max_year=request.max_year,
            min_citations=request.min_citations,
        )

        total_available = len(semantic_results)
        
        # Determine if there are more results potentially available in DB
        # If we got exactly n_results matches, likely there are more
        if total_available >= n_results:
             # We don't know exact total, but we know there's at least one more page potentially
             total_available += 1

        # Skip offset results
        page_results = semantic_results[request.offset:]

        bibcodes = [r["bibcode"] for r in page_results]
        papers = paper_repo.get_batch(bibcodes)
        paper_map = {p.bibcode: p for p in papers}

        for result in page_results:
            bibcode = result["bibcode"]
            if bibcode in seen_bibcodes:
                continue
            seen_bibcodes.add(bibcode)

            paper = paper_map.get(bibcode)
            distance = result["distance"] or 1.0

            results.append(UnifiedResultItem(
                bibcode=bibcode,
                title=paper.title if paper else result["metadata"].get("title", ""),
                year=paper.year if paper else result["metadata"].get("year"),
                first_author=paper.first_author if paper else result["metadata"].get("first_author"),
                authors=_parse_authors(paper) if paper else None,
                abstract=paper.abstract[:500] if paper and paper.abstract else None,
                citation_count=paper.citation_count if paper else result["metadata"].get("citation_count"),
                journal=paper.journal if paper else None,
                in_library=True,
                relevance_score=round(1.0 - min(distance, 1.0), 3),
                source="library",
            ))

        return results, total_available
    except Exception as e:
        print(f"Library search failed: {e}")
        return [], 0


async def _search_pdf(
    request: UnifiedSearchRequest,
    query: str,
    vector_store,
    paper_repo: PaperRepository,
    seen_bibcodes: set,
) -> tuple[List[UnifiedResultItem], int]:
    """Search library abstracts + PDF chunks, grouped by bibcode."""
    results = []
    bibcode_best: dict = {}  # bibcode -> best distance

    try:
        # Search abstracts
        n_results = request.offset + request.limit
        abstract_results = await asyncio.to_thread(
            vector_store.search,
            query,
            n_results=n_results,
            min_year=request.min_year,
            max_year=request.max_year,
            min_citations=request.min_citations,
        )
        for r in abstract_results:
            bc = r["bibcode"]
            dist = r["distance"] or 1.0
            if bc not in bibcode_best or dist < bibcode_best[bc]["distance"]:
                bibcode_best[bc] = {"distance": dist, "source": "abstract", "metadata": r["metadata"]}

        # Search PDF chunks
        pdf_results = await asyncio.to_thread(
            vector_store.search_pdf,
            query,
            n_results=n_results * 3,  # More chunks since multiple per paper
        )
        for r in pdf_results:
            bc = r["bibcode"]
            dist = r["distance"] or 1.0
            if bc not in bibcode_best or dist < bibcode_best[bc]["distance"]:
                bibcode_best[bc] = {"distance": dist, "source": "pdf", "metadata": r.get("metadata", {})}

        # Sort by best distance
        sorted_bibcodes = sorted(bibcode_best.items(), key=lambda x: x[1]["distance"])
        total_available = len(sorted_bibcodes)
        
        # If result count == n_results, likely truncated by vector store limit
        if total_available >= n_results:
             total_available += 1

        # Apply offset
        page_bibcodes = sorted_bibcodes[request.offset:]

        # Fetch paper details
        bcs = [bc for bc, _ in page_bibcodes]
        papers = paper_repo.get_batch(bcs)
        paper_map = {p.bibcode: p for p in papers}

        for bibcode, info in page_bibcodes:
            if bibcode in seen_bibcodes:
                continue
            seen_bibcodes.add(bibcode)

            paper = paper_map.get(bibcode)
            distance = info["distance"]

            results.append(UnifiedResultItem(
                bibcode=bibcode,
                title=paper.title if paper else info["metadata"].get("title", ""),
                year=paper.year if paper else info["metadata"].get("year"),
                first_author=paper.first_author if paper else info["metadata"].get("first_author"),
                authors=_parse_authors(paper) if paper else None,
                abstract=paper.abstract[:500] if paper and paper.abstract else None,
                citation_count=paper.citation_count if paper else None,
                journal=paper.journal if paper else None,
                in_library=True,
                relevance_score=round(1.0 - min(distance, 1.0), 3),
                source="pdf",
            ))

        return results, total_available
    except Exception as e:
        print(f"PDF search failed: {e}")
        return [], 0


async def _search_ads(
    request: UnifiedSearchRequest,
    query: str,
    ads_client,
    paper_repo: PaperRepository,
    seen_bibcodes: set,
) -> tuple[List[UnifiedResultItem], int]:
    """Search NASA ADS API with pagination."""
    results = []
    try:
        # Build year range for ADS query
        year_range = None
        if request.min_year or request.max_year:
            min_y = request.min_year or 0
            max_y = request.max_year or 9999
            year_range = (min_y, max_y)

        # Over-fetch if filtering by min_citations (ADS doesn't support it natively)
        fetch_limit = request.limit
        if request.min_citations:
            fetch_limit = request.limit * 3

        ads_papers = await asyncio.to_thread(
            ads_client.search,
            query,
            limit=fetch_limit,
            start=request.offset,
            year_range=year_range,
            save=False,
        )

        # Apply min_citations filter client-side
        if request.min_citations:
            ads_papers = [
                p for p in ads_papers
                if (p.citation_count or 0) >= request.min_citations
            ][:request.limit]

        # Check which papers are in library
        bibcodes = [p.bibcode for p in ads_papers]
        local_papers = paper_repo.get_batch(bibcodes)
        local_map = {p.bibcode: p for p in local_papers}

        # Estimate total: ADS doesn't return total easily, use len as lower bound
        total_available = request.offset + len(ads_papers)
        # If we got exactly the requested limit, there are likely more results
        if len(ads_papers) >= request.limit:
            total_available += request.limit  # Assume there's more

        for paper in ads_papers:
            if paper.bibcode in seen_bibcodes:
                continue
            seen_bibcodes.add(paper.bibcode)

            local = local_map.get(paper.bibcode)

            results.append(UnifiedResultItem(
                bibcode=paper.bibcode,
                title=paper.title or "",
                year=paper.year,
                first_author=paper.first_author,
                authors=_parse_authors(paper),
                abstract=paper.abstract[:500] if paper.abstract else None,
                citation_count=paper.citation_count,
                journal=paper.journal,
                in_library=local is not None,
                source="ads",
            ))

        return results, total_available
    except Exception as e:
        print(f"ADS search failed: {e}")
        return [], 0


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
