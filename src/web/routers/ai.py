"""AI-powered API router for search and paper analysis."""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import json
import asyncio

from src.db.repository import PaperRepository
from src.web.dependencies import (
    get_paper_repo,
    get_ads_client,
    get_llm_client,
    get_vector_store_dep,
)

router = APIRouter()


class AISearchRequest(BaseModel):
    """Request for AI-powered search."""
    query: str = Field(..., description="Natural language search query")
    limit: int = Field(default=20, ge=1, le=100)
    search_library: bool = Field(default=True, description="Search in local library")
    search_ads: bool = Field(default=True, description="Search in NASA ADS")
    search_pdf: bool = Field(default=False, description="Search in PDF full-text")
    min_year: Optional[int] = Field(default=None, description="Minimum publication year")
    min_citations: Optional[int] = Field(default=None, description="Minimum citation count")
    use_llm: bool = Field(default=True, description="Use LLM for analysis and ranking (set to False for keyword search)")


class CitationTypeInfo(BaseModel):
    """Citation type classification."""
    type: str
    description: str


class SearchResultItem(BaseModel):
    """A single search result with AI analysis."""
    bibcode: str
    title: str
    year: Optional[int] = None
    first_author: Optional[str] = None
    authors: Optional[List[str]] = None
    abstract: Optional[str] = None
    citation_count: Optional[int] = None
    relevance_score: float = Field(default=0.5, ge=0.0, le=1.0)
    relevance_explanation: str = ""
    citation_type: str = "general"
    in_library: bool = False
    has_pdf: bool = False
    pdf_embedded: bool = False
    source: str = "library"  # library, ads, pdf


class AIAnalysis(BaseModel):
    """AI analysis of the search context."""
    topic: str = ""
    claim: str = ""
    citation_type_needed: str = "general"
    keywords: List[str] = []
    reasoning: str = ""


class AISearchResponse(BaseModel):
    """Response from AI-powered search."""
    query: str
    results: List[SearchResultItem]
    ai_analysis: Optional[AIAnalysis] = None
    total_count: int


@router.post("/search", response_model=AISearchResponse)
async def ai_search(
    request: AISearchRequest,
    paper_repo: PaperRepository = Depends(get_paper_repo),
    ads_client=Depends(get_ads_client),
    llm_client=Depends(get_llm_client),
    vector_store=Depends(get_vector_store_dep),
):
    """AI-powered search with context analysis and paper ranking.

    This endpoint:
    1. Analyzes the query to understand what type of paper is needed
    2. Searches across multiple sources (library, ADS, PDFs)
    3. Ranks papers by relevance with explanations
    """
    import json

    results: List[SearchResultItem] = []
    ai_analysis = None
    seen_bibcodes = set()

    # Step 1: Analyze query with LLM if available and enabled
    if request.use_llm and llm_client:
        try:
            context_analysis = llm_client.analyze_context(request.query)
            ai_analysis = AIAnalysis(
                topic=context_analysis.topic,
                claim=context_analysis.claim,
                citation_type_needed=context_analysis.citation_type.value,
                keywords=context_analysis.keywords,
                reasoning=context_analysis.reasoning,
            )
        except Exception as e:
            # Continue without AI analysis
            print(f"LLM analysis failed: {e}")

    # Step 2: Search in local library (semantic search)
    if request.search_library and vector_store:
        try:
            semantic_results = vector_store.search(
                request.query,
                n_results=request.limit,
                min_year=request.min_year,
                min_citations=request.min_citations,
            )

            # Batch fetch papers
            bibcodes_to_fetch = [r["bibcode"] for r in semantic_results]
            papers = paper_repo.get_batch(bibcodes_to_fetch)
            paper_map = {p.bibcode: p for p in papers}

            for result in semantic_results:
                bibcode = result["bibcode"]
                distance = result["distance"]
                if bibcode in seen_bibcodes:
                    continue
                seen_bibcodes.add(bibcode)

                # Get full paper details
                paper = paper_map.get(bibcode)
                if paper:
                    # Parse authors if JSON
                    authors = None
                    if paper.authors:
                        try:
                            authors = json.loads(paper.authors)
                        except json.JSONDecodeError:
                            authors = [paper.authors]

                    results.append(SearchResultItem(
                        bibcode=paper.bibcode,
                        title=paper.title or "",
                        year=paper.year,
                        first_author=paper.first_author,
                        authors=authors,
                        abstract=paper.abstract[:500] if paper.abstract else None,
                        citation_count=paper.citation_count,
                        relevance_score=1.0 - min(distance, 1.0),  # Convert distance to score
                        relevance_explanation="Semantic match from your library",
                        citation_type="general",
                        in_library=True,
                        has_pdf=bool(paper.pdf_path),
                        pdf_embedded=paper.pdf_embedded,
                        source="library",
                    ))
        except Exception as e:
            print(f"Library search failed: {e}")

    # Step 3: Search in ADS
    if request.search_ads and ads_client:
        try:
            # Use AI-generated search query if available
            search_query = request.query
            if ai_analysis and ai_analysis.keywords:
                search_query = " ".join(ai_analysis.keywords[:3])

            ads_papers = ads_client.search(search_query, limit=request.limit, save=False)

            # Batch fetch local papers to check status
            bibcodes_to_fetch = [p.bibcode for p in ads_papers]
            local_papers = paper_repo.get_batch(bibcodes_to_fetch)
            local_map = {p.bibcode: p for p in local_papers}

            for paper in ads_papers:
                if paper.bibcode in seen_bibcodes:
                    continue
                seen_bibcodes.add(paper.bibcode)

                # Check if in library
                local_paper = local_map.get(paper.bibcode)
                in_library = local_paper is not None

                # Parse authors if JSON
                authors = None
                if paper.authors:
                    try:
                        authors = json.loads(paper.authors)
                    except json.JSONDecodeError:
                        authors = [paper.authors] if isinstance(paper.authors, str) else paper.authors

                results.append(SearchResultItem(
                    bibcode=paper.bibcode,
                    title=paper.title or "",
                    year=paper.year,
                    first_author=paper.first_author,
                    authors=authors,
                    abstract=paper.abstract[:500] if paper.abstract else None,
                    citation_count=paper.citation_count,
                    relevance_score=0.5,  # Will be re-ranked by LLM
                    relevance_explanation="Found in NASA ADS",
                    citation_type="general",
                    in_library=in_library,
                    has_pdf=bool(local_paper.pdf_path) if local_paper else False,
                    pdf_embedded=local_paper.pdf_embedded if local_paper else False,
                    source="ads",
                ))
        except Exception as e:
            print(f"ADS search failed: {e}")

    # Step 4: Search in PDFs
    if request.search_pdf and vector_store:
        try:
            pdf_results = vector_store.search_pdf(
                request.query,
                n_results=request.limit,
            )

            # Batch fetch papers
            bibcodes_to_fetch = [r["bibcode"] for r in pdf_results]
            papers = paper_repo.get_batch(bibcodes_to_fetch)
            paper_map = {p.bibcode: p for p in papers}

            for result in pdf_results:
                bibcode = result["bibcode"]
                distance = result["distance"]
                text_snippet = result["document"]
                if bibcode in seen_bibcodes:
                    continue
                seen_bibcodes.add(bibcode)

                paper = paper_map.get(bibcode)
                if paper:
                    # Parse authors if JSON
                    authors = None
                    if paper.authors:
                        try:
                            authors = json.loads(paper.authors)
                        except json.JSONDecodeError:
                            authors = [paper.authors]

                    results.append(SearchResultItem(
                        bibcode=paper.bibcode,
                        title=paper.title or "",
                        year=paper.year,
                        first_author=paper.first_author,
                        authors=authors,
                        abstract=text_snippet[:500] if text_snippet else paper.abstract[:500] if paper.abstract else None,
                        citation_count=paper.citation_count,
                        relevance_score=1.0 - min(distance, 1.0),
                        relevance_explanation=f"Found in PDF content: '{text_snippet[:100]}...'" if text_snippet else "Found in PDF",
                        citation_type="general",
                        in_library=True,
                        has_pdf=True,
                        pdf_embedded=True,
                        source="pdf",
                    ))
        except Exception as e:
            print(f"PDF search failed: {e}")

    # Step 5: Rank all results with LLM if available and enabled
    if request.use_llm and llm_client and results and ai_analysis:
        try:
            # Create Paper objects for ranking
            from src.db.models import Paper
            papers_to_rank = []
            for r in results[:30]:  # Limit to top 30 for ranking
                # Convert authors list back to JSON for Paper model
                authors_json = None
                if r.authors:
                    authors_json = json.dumps(r.authors)
                elif r.first_author:
                    # If only first_author available, create a minimal authors list
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

            from src.core.llm_client import ContextAnalysis, CitationType
            context = ContextAnalysis(
                topic=ai_analysis.topic,
                claim=ai_analysis.claim,
                citation_type=CitationType(ai_analysis.citation_type_needed),
                keywords=ai_analysis.keywords,
                search_query=request.query,
                reasoning=ai_analysis.reasoning,
            )

            ranked = llm_client.rank_papers(
                papers_to_rank,
                request.query,
                context_analysis=context,
                top_k=request.limit,
            )

            # Update results with rankings
            rank_map = {rp.paper.bibcode: rp for rp in ranked}
            for result in results:
                if result.bibcode in rank_map:
                    rp = rank_map[result.bibcode]
                    result.relevance_score = rp.relevance_score
                    result.relevance_explanation = rp.relevance_explanation
                    result.citation_type = rp.citation_type.value

            # Sort by relevance score
            results.sort(key=lambda x: x.relevance_score, reverse=True)
        except Exception as e:
            print(f"LLM ranking failed: {e}")

    # Limit results
    results = results[:request.limit]

    return AISearchResponse(
        query=request.query,
        results=results,
        ai_analysis=ai_analysis,
        total_count=len(results),
    )


@router.post("/search/stream")
async def ai_search_stream(
    request: AISearchRequest,
    paper_repo: PaperRepository = Depends(get_paper_repo),
    ads_client=Depends(get_ads_client),
    llm_client=Depends(get_llm_client),
    vector_store=Depends(get_vector_store_dep),
):
    """AI-powered search with streaming progress."""
    import time
    
    async def event_generator():
        results: List[SearchResultItem] = []
        ai_analysis = None
        seen_bibcodes = set()
        
        t_total_start = time.time()
        
        # Step 1: Analyze query
        if request.use_llm and llm_client:
            yield json.dumps({"type": "progress", "message": "Analyzing query with AI..."}) + "\n"
            t_start = time.time()
            try:
                context_analysis = await asyncio.to_thread(llm_client.analyze_context, request.query)
                ai_analysis = AIAnalysis(
                    topic=context_analysis.topic,
                    claim=context_analysis.claim,
                    citation_type_needed=context_analysis.citation_type.value,
                    keywords=context_analysis.keywords,
                    reasoning=context_analysis.reasoning,
                )
                duration = time.time() - t_start
                yield json.dumps({"type": "log", "level": "info", "message": f"Query analysis took {duration:.2f}s"}) + "\n"
                
                yield json.dumps({
                    "type": "analysis", 
                    "data": ai_analysis.model_dump()
                }) + "\n"
            except Exception as e:
                import traceback
                print(f"Analysis failed details: {traceback.format_exc()}")
                yield json.dumps({"type": "log", "level": "error", "message": f"Analysis failed: {e}"}) + "\n"

        # Step 2: Library Search
        if request.search_library and vector_store:
            yield json.dumps({"type": "progress", "message": "Searching local library..."}) + "\n"
            t_start = time.time()
            try:
                # Run vector search in thread to verify if it blocks
                semantic_results = await asyncio.to_thread(
                    vector_store.search,
                    request.query,
                    n_results=request.limit,
                    min_year=request.min_year,
                    min_citations=request.min_citations,
                )
                
                # Batch fetch papers
                bibcodes_to_fetch = [r["bibcode"] for r in semantic_results]
                papers = paper_repo.get_batch(bibcodes_to_fetch)
                paper_map = {p.bibcode: p for p in papers}

                # Yield intermediate count
                duration = time.time() - t_start
                yield json.dumps({"type": "log", "level": "info", "message": f"Library search found {len(semantic_results)} matches in {duration:.2f}s"}) + "\n"

                for result in semantic_results:
                    bibcode = result["bibcode"]
                    distance = result["distance"]
                    if bibcode in seen_bibcodes:
                        continue
                    seen_bibcodes.add(bibcode)

                    paper = paper_map.get(bibcode)
                    if paper:
                        authors = None
                        if paper.authors:
                            try:
                                authors = json.loads(paper.authors)
                            except json.JSONDecodeError:
                                authors = [paper.authors]

                        item = SearchResultItem(
                            bibcode=paper.bibcode,
                            title=paper.title or "",
                            year=paper.year,
                            first_author=paper.first_author,
                            authors=authors,
                            abstract=paper.abstract[:500] if paper.abstract else None,
                            citation_count=paper.citation_count,
                            relevance_score=1.0 - min(distance, 1.0),
                            relevance_explanation="Semantic match from your library",
                            citation_type="general",
                            in_library=True,
                            has_pdf=bool(paper.pdf_path),
                            pdf_embedded=paper.pdf_embedded,
                            source="library",
                        )
                        results.append(item)
            except Exception as e:
                yield json.dumps({"type": "log", "level": "error", "message": f"Library search failed: {e}"}) + "\n"

        # Step 3: ADS Search
        if request.search_ads and ads_client:
            yield json.dumps({"type": "progress", "message": "Searching NASA ADS..."}) + "\n"
            t_start = time.time()
            try:
                search_query = request.query
                if ai_analysis and ai_analysis.keywords:
                    search_query = " ".join(ai_analysis.keywords[:3])
                
                # Check cache/perform search
                ads_papers = await asyncio.to_thread(ads_client.search, search_query, limit=request.limit, save=False)
                
                # Batch fetch local papers
                bibcodes_to_fetch = [p.bibcode for p in ads_papers]
                local_papers = paper_repo.get_batch(bibcodes_to_fetch)
                local_map = {p.bibcode: p for p in local_papers}

                duration = time.time() - t_start
                yield json.dumps({"type": "log", "level": "info", "message": f"ADS search found {len(ads_papers)} matches in {duration:.2f}s"}) + "\n"

                for paper in ads_papers:
                    if paper.bibcode in seen_bibcodes:
                        continue
                    seen_bibcodes.add(paper.bibcode)

                    local_paper = local_map.get(paper.bibcode)
                    in_library = local_paper is not None

                    authors = None
                    if paper.authors:
                        try:
                            authors = json.loads(paper.authors)
                        except json.JSONDecodeError:
                            authors = [paper.authors] if isinstance(paper.authors, str) else paper.authors

                    item = SearchResultItem(
                        bibcode=paper.bibcode,
                        title=paper.title or "",
                        year=paper.year,
                        first_author=paper.first_author,
                        authors=authors,
                        abstract=paper.abstract[:500] if paper.abstract else None,
                        citation_count=paper.citation_count,
                        relevance_score=0.5,
                        relevance_explanation="Found in NASA ADS",
                        citation_type="general",
                        in_library=in_library,
                        has_pdf=bool(local_paper.pdf_path) if local_paper else False,
                        pdf_embedded=local_paper.pdf_embedded if local_paper else False,
                        source="ads",
                    )
                    results.append(item)
            except Exception as e:
                yield json.dumps({"type": "log", "level": "error", "message": f"ADS search failed: {e}"}) + "\n"

        # Step 4: Search PDF
        if request.search_pdf and vector_store:
             yield json.dumps({"type": "progress", "message": "Searching PDF contents..."}) + "\n"
             t_start = time.time()
             # ... (simplified for minimal change, just log timing if it ran)
             # But let's assume it's disabled by default in UI for now, or just leave as is. 
             # Wait, I didn't replace Step 4 content in my previous tool call. 
             # I should probably wrap it if I want to time it.
             # For now I will leave step 4 as is or just log if I can.
             # Actually I'm replacing the whole function, so I need to put Step 4 code back in or it gets deleted!
             # I will reimplement Step 4 with timing.
             try:
                pdf_results = await asyncio.to_thread(
                    vector_store.search_pdf,
                    request.query,
                    n_results=request.limit,
                )
                
                bibcodes_to_fetch = [r["bibcode"] for r in pdf_results]
                papers = paper_repo.get_batch(bibcodes_to_fetch)
                paper_map = {p.bibcode: p for p in papers}
                
                duration = time.time() - t_start
                yield json.dumps({"type": "log", "level": "info", "message": f"PDF search found {len(pdf_results)} matches in {duration:.2f}s"}) + "\n"

                for result in pdf_results:
                    bibcode = result["bibcode"]
                    distance = result["distance"]
                    text_snippet = result["document"]
                    if bibcode in seen_bibcodes:
                        continue
                    seen_bibcodes.add(bibcode)

                    paper = paper_map.get(bibcode)
                    if paper:
                        authors = None
                        if paper.authors:
                            try:
                                authors = json.loads(paper.authors)
                            except json.JSONDecodeError:
                                authors = [paper.authors]

                        results.append(SearchResultItem(
                            bibcode=paper.bibcode,
                            title=paper.title or "",
                            year=paper.year,
                            first_author=paper.first_author,
                            authors=authors,
                            abstract=text_snippet[:500] if text_snippet else paper.abstract[:500] if paper.abstract else None,
                            citation_count=paper.citation_count,
                            relevance_score=1.0 - min(distance, 1.0),
                            relevance_explanation=f"Found in PDF content: '{text_snippet[:100]}...'" if text_snippet else "Found in PDF",
                            citation_type="general",
                            in_library=True,
                            has_pdf=True,
                            pdf_embedded=True,
                            source="pdf",
                        ))
             except Exception as e:
                yield json.dumps({"type": "log", "level": "error", "message": f"PDF search failed: {e}"}) + "\n"


        # Step 5: Ranking
        if request.use_llm and llm_client and results and ai_analysis:
            yield json.dumps({"type": "progress", "message": "Re-ranking results with AI..."}) + "\n"
            t_start = time.time()
            try:
                from src.db.models import Paper
                papers_to_rank = []
                for r in results[:30]:
                    authors_json = None
                    if r.authors:
                        authors_json = json.dumps(r.authors)
                    elif r.first_author:
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

                from src.core.llm_client import ContextAnalysis, CitationType
                context = ContextAnalysis(
                    topic=ai_analysis.topic,
                    claim=ai_analysis.claim,
                    citation_type=CitationType(ai_analysis.citation_type_needed),
                    keywords=ai_analysis.keywords,
                    search_query=request.query,
                    reasoning=ai_analysis.reasoning,
                )

                ranked = await asyncio.to_thread(
                    llm_client.rank_papers,
                    papers_to_rank,
                    request.query,
                    context_analysis=context,
                    top_k=request.limit,
                )

                rank_map = {rp.paper.bibcode: rp for rp in ranked}
                for result in results:
                    if result.bibcode in rank_map:
                        rp = rank_map[result.bibcode]
                        result.relevance_score = rp.relevance_score
                        result.relevance_explanation = rp.relevance_explanation
                        result.citation_type = rp.citation_type.value

                results.sort(key=lambda x: x.relevance_score, reverse=True)
                
                duration = time.time() - t_start
                yield json.dumps({"type": "log", "level": "info", "message": f"AI re-ranking took {duration:.2f}s"}) + "\n"
                
            except Exception as e:
                 yield json.dumps({"type": "log", "level": "error", "message": f"Ranking failed: {e}"}) + "\n"

        # Limit results
        results = results[:request.limit]
        
        total_duration = time.time() - t_total_start
        yield json.dumps({"type": "log", "level": "info", "message": f"Total search time: {total_duration:.2f}s"}) + "\n"
        
        # Final result
        response = AISearchResponse(
            query=request.query,
            results=results,
            ai_analysis=ai_analysis,
            total_count=len(results),
        )
        yield json.dumps({
            "type": "result", 
            "data": response.model_dump()
        }) + "\n"
        
    return StreamingResponse(event_generator(), media_type="application/x-ndjson")


class AskPaperRequest(BaseModel):
    """Request to ask a question about a paper."""
    bibcode: str = Field(..., description="Paper bibcode")
    question: str = Field(..., description="Question to ask about the paper")


class AskPaperResponse(BaseModel):
    """Response from asking about a paper."""
    bibcode: str
    question: str
    answer: str
    sources_used: List[str] = []  # pdf, abstract, title, etc.


@router.post("/ask", response_model=AskPaperResponse)
async def ask_about_paper(
    request: AskPaperRequest,
    paper_repo: PaperRepository = Depends(get_paper_repo),
    llm_client=Depends(get_llm_client),
    vector_store=Depends(get_vector_store_dep),
):
    """Ask a question about a specific paper using its embedded content.

    Uses PDF content (if embedded) and abstract to answer questions.
    """
    if not llm_client:
        raise HTTPException(status_code=503, detail="LLM service not available")

    paper = paper_repo.get(request.bibcode)
    if not paper:
        raise HTTPException(status_code=404, detail=f"Paper not found: {request.bibcode}")

    sources_used = []
    context_parts = []

    # Add paper metadata
    context_parts.append(f"Paper Title: {paper.title}")
    sources_used.append("title")

    if paper.abstract:
        context_parts.append(f"\nAbstract: {paper.abstract}")
        sources_used.append("abstract")

    # Search embedded PDF for relevant content
    if paper.pdf_embedded and vector_store:
        try:
            pdf_results = vector_store.search_pdf(
                request.question,
                n_results=5,
                bibcode=request.bibcode,
            )
            if pdf_results:
                sources_used.append("pdf")
                context_parts.append("\nRelevant excerpts from paper:")
                for result in pdf_results:
                    text = result.get("document")
                    if text:
                        context_parts.append(f"\n- {text[:500]}")
        except Exception as e:
            print(f"PDF search failed: {e}")

    # Get user's note if available
    from src.db.repository import NoteRepository
    note_repo = NoteRepository(auto_embed=False)
    note = note_repo.get(request.bibcode)
    if note:
        context_parts.append(f"\nUser's notes: {note.content}")
        sources_used.append("user_note")

    # Build prompt
    context = "\n".join(context_parts)

    system_prompt = """You are a scientific research assistant. Answer questions about the paper based on the provided context.
Be specific and cite relevant parts of the paper when possible.
If the information is not available in the context, say so clearly."""

    user_prompt = f"""Context about the paper:
{context}

Question: {request.question}

Please provide a clear, concise answer based on the paper content."""

    try:
        answer = llm_client._call_llm(system_prompt, user_prompt)

        return AskPaperResponse(
            bibcode=request.bibcode,
            question=request.question,
            answer=answer.strip(),
            sources_used=sources_used,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate answer: {str(e)}")
