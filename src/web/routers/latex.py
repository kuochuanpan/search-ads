"""LaTeX parsing and citation suggestion API router."""

import re
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.db.repository import PaperRepository
from src.web.dependencies import (
    get_paper_repo,
    get_ads_client,
    get_llm_client,
    get_vector_store_dep,
)

router = APIRouter()


class EmptyCitationInfo(BaseModel):
    """Information about an empty citation found in LaTeX."""
    index: int = Field(..., description="Index of this citation in the list")
    cite_type: str = Field(..., description="Type of citation command (cite, citep, citet, etc.)")
    context: str = Field(..., description="Surrounding text for context")
    full_match: str = Field(..., description="The full citation command match")
    line_number: int = Field(default=0, description="Approximate line number")
    existing_keys: List[str] = Field(default=[], description="Any existing keys in the citation")


class ParseLaTeXRequest(BaseModel):
    """Request to parse LaTeX text for empty citations."""
    latex_text: str = Field(..., description="LaTeX text to parse")


class ParseLaTeXResponse(BaseModel):
    """Response with found empty citations."""
    empty_citations: List[EmptyCitationInfo]
    total_count: int


# Citation patterns
CITE_PATTERN = re.compile(
    r"\\(cite[pt]?|citep?|citet|citealt|citealp|citeauthor|citeyear|citeyearpar)"
    r"(?:\[[^\]]*\])?"  # Optional [] argument
    r"(?:\[[^\]]*\])?"  # Optional second [] argument
    r"\{([^}]*)\}",
    re.MULTILINE,
)

EMPTY_CITE_PATTERN = re.compile(
    r"\\(cite[pt]?|citep?|citet|citealt|citealp|citeauthor|citeyear|citeyearpar)"
    r"(?:\[[^\]]*\])?"
    r"(?:\[[^\]]*\])?"
    r"\{(\s*(?:,\s*)*)\}",  # Empty or just commas
    re.MULTILINE,
)


def extract_context(content: str, position: int, window: int = 200) -> str:
    """Extract surrounding context for a citation."""
    start = max(0, position - window)
    end = min(len(content), position + window)

    context = content[start:end]

    # Clean up LaTeX commands for better readability
    context = re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", context)
    context = re.sub(r"\\[a-zA-Z]+", "", context)
    context = re.sub(r"[{}]", "", context)
    context = re.sub(r"\s+", " ", context)

    return context.strip()


@router.post("/parse", response_model=ParseLaTeXResponse)
async def parse_latex(request: ParseLaTeXRequest):
    """Parse LaTeX text to find empty citations.

    Finds patterns like \\cite{}, \\citep{}, \\citet{} that need to be filled.
    """
    content = request.latex_text
    empty_citations = []
    index = 0

    # Find completely empty citations
    for match in EMPTY_CITE_PATTERN.finditer(content):
        start = match.start()
        line_num = content[:start].count("\n") + 1
        context = extract_context(content, start)

        empty_citations.append(EmptyCitationInfo(
            index=index,
            cite_type=match.group(1),
            context=context,
            full_match=match.group(0),
            line_number=line_num,
            existing_keys=[],
        ))
        index += 1

    # Also find citations with partial keys (e.g., \cite{key1, })
    for match in CITE_PATTERN.finditer(content):
        keys_str = match.group(2)
        keys = [k.strip() for k in keys_str.split(",")]

        # Check if any key is empty
        if any(k == "" for k in keys):
            start = match.start()
            line_num = content[:start].count("\n") + 1

            # Avoid duplicates with EMPTY_CITE_PATTERN
            if not any(ec.line_number == line_num and ec.full_match == match.group(0) for ec in empty_citations):
                context = extract_context(content, start)
                existing = [k for k in keys if k]

                empty_citations.append(EmptyCitationInfo(
                    index=index,
                    cite_type=match.group(1),
                    context=context,
                    full_match=match.group(0),
                    line_number=line_num,
                    existing_keys=existing,
                ))
                index += 1

    return ParseLaTeXResponse(
        empty_citations=empty_citations,
        total_count=len(empty_citations),
    )


class SuggestedPaper(BaseModel):
    """A paper suggested for citation."""
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
    bibtex: Optional[str] = None
    bibitem_aastex: Optional[str] = None
    in_library: bool = False


class CitationAnalysis(BaseModel):
    """AI analysis of the citation context."""
    topic: str = ""
    claim: str = ""
    citation_type_needed: str = "general"
    keywords: List[str] = []
    reasoning: str = ""


class CitationSuggestion(BaseModel):
    """Suggestion for a single empty citation."""
    citation_index: int
    cite_type: str
    context: str
    existing_keys: List[str] = Field(default=[], description="Any existing keys in the citation")
    analysis: Optional[CitationAnalysis] = None
    suggestions: List[SuggestedPaper]
    error: Optional[str] = None


class GetSuggestionsRequest(BaseModel):
    """Request to get citation suggestions."""
    latex_text: str = Field(..., description="LaTeX text containing empty citations")
    limit: int = Field(default=5, ge=1, le=20, description="Number of suggestions per citation")
    use_library: bool = Field(default=True, description="Search in local library")
    use_ads: bool = Field(default=True, description="Search in NASA ADS")


class GetSuggestionsResponse(BaseModel):
    """Response with citation suggestions."""
    suggestions: List[CitationSuggestion]
    total_citations: int


@router.post("/suggest", response_model=GetSuggestionsResponse)
async def get_citation_suggestions(
    request: GetSuggestionsRequest,
    paper_repo: PaperRepository = Depends(get_paper_repo),
    ads_client=Depends(get_ads_client),
    llm_client=Depends(get_llm_client),
    vector_store=Depends(get_vector_store_dep),
):
    """Get paper suggestions for each empty citation in LaTeX text.

    This endpoint:
    1. Parses the LaTeX to find empty citations
    2. Analyzes each citation's context with AI
    3. Searches for relevant papers in library and ADS
    4. Ranks papers with AI explanations
    """
    import json
    from src.core.llm_client import ContextAnalysis, CitationType

    # Parse LaTeX first
    parse_response = await parse_latex(ParseLaTeXRequest(latex_text=request.latex_text))
    empty_citations = parse_response.empty_citations

    suggestions = []

    for citation in empty_citations:
        suggestion = CitationSuggestion(
            citation_index=citation.index,
            cite_type=citation.cite_type,
            context=citation.context,
            existing_keys=citation.existing_keys,
            analysis=None,
            suggestions=[],
            error=None,
        )

        try:
            # Step 1: Analyze context with LLM
            context_analysis = None
            if llm_client:
                try:
                    context_analysis = llm_client.analyze_context(citation.context)
                    suggestion.analysis = CitationAnalysis(
                        topic=context_analysis.topic,
                        claim=context_analysis.claim,
                        citation_type_needed=context_analysis.citation_type.value,
                        keywords=context_analysis.keywords,
                        reasoning=context_analysis.reasoning,
                    )
                except Exception as e:
                    print(f"Context analysis failed: {e}")

            # Step 2: Search for papers
            papers = []
            seen_bibcodes = set()

            # Search library with semantic search
            if request.use_library and vector_store:
                try:
                    search_query = citation.context
                    if context_analysis:
                        search_query = context_analysis.search_query or " ".join(context_analysis.keywords)

                    results = vector_store.search(
                        search_query,
                        n_results=request.limit * 2,
                    )

                    for bibcode, distance, metadata, document in results:
                        if bibcode in seen_bibcodes:
                            continue
                        seen_bibcodes.add(bibcode)

                        paper = paper_repo.get(bibcode)
                        if paper:
                            papers.append((paper, 1.0 - min(distance, 1.0), True))
                except Exception as e:
                    print(f"Library search failed: {e}")

            # Search ADS
            if request.use_ads and ads_client:
                try:
                    search_query = citation.context[:100]
                    if context_analysis:
                        search_query = context_analysis.search_query or " ".join(context_analysis.keywords)

                    ads_papers = ads_client.search(search_query, limit=request.limit * 2)

                    for paper in ads_papers:
                        if paper.bibcode in seen_bibcodes:
                            continue
                        seen_bibcodes.add(paper.bibcode)

                        # Check if in library
                        local_paper = paper_repo.get(paper.bibcode)
                        papers.append((paper, 0.5, local_paper is not None))
                except Exception as e:
                    print(f"ADS search failed: {e}")

            # Step 3: Rank papers with LLM
            if papers:
                paper_objects = [p[0] for p in papers]
                in_library_map = {p[0].bibcode: p[2] for p in papers}

                ranked_papers = []
                if llm_client:
                    try:
                        ranked = llm_client.rank_papers(
                            paper_objects,
                            citation.context,
                            context_analysis=context_analysis,
                            top_k=request.limit,
                        )
                        for rp in ranked:
                            ranked_papers.append((
                                rp.paper,
                                rp.relevance_score,
                                rp.relevance_explanation,
                                rp.citation_type.value,
                                in_library_map.get(rp.paper.bibcode, False),
                            ))
                    except Exception as e:
                        print(f"Ranking failed: {e}")
                        # Fallback to initial scores
                        for paper, score, in_lib in papers[:request.limit]:
                            ranked_papers.append((paper, score, "Ranked by search relevance", "general", in_lib))
                else:
                    for paper, score, in_lib in papers[:request.limit]:
                        ranked_papers.append((paper, score, "Ranked by search relevance", "general", in_lib))

                # Convert to response format
                for paper, score, explanation, cit_type, in_lib in ranked_papers[:request.limit]:
                    # Parse authors
                    authors = None
                    if paper.authors:
                        try:
                            authors = json.loads(paper.authors)
                        except (json.JSONDecodeError, TypeError):
                            if isinstance(paper.authors, str):
                                authors = [paper.authors]
                            elif isinstance(paper.authors, list):
                                authors = paper.authors

                    suggestion.suggestions.append(SuggestedPaper(
                        bibcode=paper.bibcode,
                        title=paper.title or "",
                        year=paper.year,
                        first_author=paper.first_author,
                        authors=authors,
                        abstract=paper.abstract[:300] + "..." if paper.abstract and len(paper.abstract) > 300 else paper.abstract,
                        citation_count=paper.citation_count,
                        relevance_score=score,
                        relevance_explanation=explanation,
                        citation_type=cit_type,
                        bibtex=paper.bibtex,
                        bibitem_aastex=paper.bibitem_aastex,
                        in_library=in_lib,
                    ))

        except Exception as e:
            suggestion.error = str(e)

        suggestions.append(suggestion)

    return GetSuggestionsResponse(
        suggestions=suggestions,
        total_citations=len(suggestions),
    )


class GenerateBibliographyRequest(BaseModel):
    """Request to generate bibliography entries."""
    bibcodes: List[str] = Field(..., description="List of paper bibcodes")
    format: str = Field(default="bibtex", description="Output format: bibtex or aastex")


class BibliographyEntry(BaseModel):
    """A single bibliography entry."""
    bibcode: str
    cite_key: str
    entry: str
    format: str


class GenerateBibliographyResponse(BaseModel):
    """Response with generated bibliography entries."""
    entries: List[BibliographyEntry]
    combined: str  # All entries combined


@router.post("/bibliography", response_model=GenerateBibliographyResponse)
async def generate_bibliography(
    request: GenerateBibliographyRequest,
    paper_repo: PaperRepository = Depends(get_paper_repo),
    ads_client=Depends(get_ads_client),
):
    """Generate bibliography entries for a list of papers.

    Supports BibTeX and AASTeX bibitem formats.
    """
    entries = []
    combined_parts = []

    for bibcode in request.bibcodes:
        paper = paper_repo.get(bibcode)

        if not paper:
            # Try to fetch from ADS
            try:
                paper = ads_client.fetch_paper(bibcode)
            except Exception:
                continue

        if not paper:
            continue

        # Generate cite key
        cite_key = paper.generate_citation_key() if hasattr(paper, 'generate_citation_key') else bibcode

        if request.format == "bibtex":
            entry_text = paper.bibtex
            if not entry_text:
                # Generate basic BibTeX
                import json
                authors_str = ""
                if paper.authors:
                    try:
                        authors = json.loads(paper.authors)
                        authors_str = " and ".join(authors)
                    except (json.JSONDecodeError, TypeError):
                        authors_str = paper.authors if isinstance(paper.authors, str) else ""

                entry_text = f"""@article{{{bibcode},
    author = {{{authors_str}}},
    title = {{{{{paper.title or ''}}}}},
    journal = {{{paper.journal or ''}}},
    year = {{{paper.year or ''}}},
    volume = {{{paper.volume or ''}}},
    pages = {{{paper.pages or ''}}},
    doi = {{{paper.doi or ''}}}
}}"""
        else:  # aastex
            entry_text = paper.bibitem_aastex
            if not entry_text:
                # Generate basic bibitem
                import json
                authors_str = ""
                if paper.authors:
                    try:
                        authors = json.loads(paper.authors)
                        if len(authors) > 3:
                            authors_str = f"{authors[0]} et al."
                        else:
                            authors_str = ", ".join(authors)
                    except (json.JSONDecodeError, TypeError):
                        authors_str = paper.first_author or ""

                entry_text = f"\\bibitem{{{cite_key}}} {authors_str}, {paper.year}, {paper.title}, {paper.journal or ''}, {paper.volume or ''}, {paper.pages or ''}"

        entries.append(BibliographyEntry(
            bibcode=bibcode,
            cite_key=cite_key,
            entry=entry_text,
            format=request.format,
        ))
        combined_parts.append(entry_text)

    # Add header comment
    if request.format == "bibtex":
        header = f"% Generated by Search-ADS - {len(entries)} entries\n\n"
    else:
        header = f"% Generated by Search-ADS - {len(entries)} entries\n% Add these to your \\begin{{thebibliography}} section\n\n"

    combined = header + "\n\n".join(combined_parts)

    return GenerateBibliographyResponse(
        entries=entries,
        combined=combined,
    )
