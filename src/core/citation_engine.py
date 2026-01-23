"""Citation engine that orchestrates the search and fill workflow."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from src.core.ads_client import ADSClient, RateLimitExceeded
from src.core.config import settings
from src.core.latex_parser import (
    LaTeXParser,
    EmptyCitation,
    add_bibtex_entry,
    format_bibitem_from_paper,
)
from src.core.llm_client import (
    CitationType,
    ContextAnalysis,
    LLMClient,
    LLMNotAvailable,
    RankedPaper,
)
from src.db.models import Paper
from src.db.repository import PaperRepository


@dataclass
class CitationResult:
    """Result of a citation search for a single empty citation."""

    citation: EmptyCitation
    context_analysis: Optional[ContextAnalysis]
    ranked_papers: list[RankedPaper]
    selected_paper: Optional[Paper] = None
    citation_key: Optional[str] = None
    error: Optional[str] = None


@dataclass
class FillResult:
    """Result of filling a citation."""

    success: bool
    citation_key: Optional[str] = None
    bibcode: Optional[str] = None
    error: Optional[str] = None


class CitationEngine:
    """Engine for finding and filling citations in LaTeX documents.

    This class orchestrates the complete workflow:
    1. Parse LaTeX to find empty citations
    2. Analyze context with LLM
    3. Search ADS for relevant papers
    4. Rank papers by relevance
    5. Fill citations and update bibliography
    """

    def __init__(
        self,
        use_llm: bool = True,
        max_hops: int = 2,
        top_k: int = 5,
        search_multiplier: int = 3,
    ):
        """Initialize the citation engine.

        Args:
            use_llm: Whether to use LLM for analysis and ranking
            max_hops: Maximum citation graph expansion depth
            top_k: Number of top papers to return
            search_multiplier: Fetch this many times top_k papers for ranking
        """
        self.use_llm = use_llm
        self.max_hops = max_hops
        self.top_k = top_k
        self.search_multiplier = search_multiplier

        self.ads_client = ADSClient()
        self.paper_repo = PaperRepository()
        self.llm_client: Optional[LLMClient] = None

        if use_llm:
            try:
                self.llm_client = LLMClient()
            except Exception:
                self.llm_client = None

    def find_empty_citations(self, tex_file: Path) -> list[EmptyCitation]:
        """Find all empty citations in a LaTeX file.

        Args:
            tex_file: Path to the LaTeX file

        Returns:
            List of EmptyCitation objects
        """
        parser = LaTeXParser(tex_file)
        return parser.find_empty_citations()

    def search_for_citation(
        self,
        context: str,
        empty_citation: Optional[EmptyCitation] = None,
    ) -> CitationResult:
        """Search for papers to fill a citation.

        Args:
            context: The text context around the citation
            empty_citation: Optional EmptyCitation object for metadata

        Returns:
            CitationResult with ranked papers
        """
        citation = empty_citation or EmptyCitation(
            line=0, column=0, cite_command="cite", context=context
        )

        context_analysis = None
        ranked_papers: list[RankedPaper] = []
        error = None

        try:
            # Step 1: Analyze context with LLM (if available)
            if self.llm_client:
                try:
                    context_analysis = self.llm_client.analyze_context(context)
                    search_query = context_analysis.search_query
                except LLMNotAvailable:
                    search_query = context
            else:
                search_query = context

            # Step 2: Search ADS
            fetch_limit = self.top_k * self.search_multiplier
            papers = self.ads_client.search(search_query, limit=fetch_limit)

            # Fallback to keyword search if no results
            if not papers and context_analysis:
                keyword_query = " OR ".join(context_analysis.keywords[:3])
                papers = self.ads_client.search(keyword_query, limit=fetch_limit)

            if not papers:
                return CitationResult(
                    citation=citation,
                    context_analysis=context_analysis,
                    ranked_papers=[],
                    error="No papers found for the given context",
                )

            # Step 3: Rank papers with LLM (if available)
            if self.llm_client:
                try:
                    ranked_papers = self.llm_client.rank_papers(
                        papers,
                        context,
                        context_analysis=context_analysis,
                        top_k=self.top_k,
                    )
                except Exception as e:
                    # Fallback to citation count ranking
                    ranked_papers = self._fallback_ranking(papers, context_analysis)
                    error = f"LLM ranking failed: {e}"
            else:
                ranked_papers = self._fallback_ranking(papers, context_analysis)

        except RateLimitExceeded as e:
            error = str(e)
        except Exception as e:
            error = f"Search failed: {e}"

        return CitationResult(
            citation=citation,
            context_analysis=context_analysis,
            ranked_papers=ranked_papers,
            error=error,
        )

    def _fallback_ranking(
        self,
        papers: list[Paper],
        context_analysis: Optional[ContextAnalysis],
    ) -> list[RankedPaper]:
        """Fallback ranking when LLM is not available."""
        sorted_papers = sorted(
            papers, key=lambda p: p.citation_count or 0, reverse=True
        )

        citation_type = (
            context_analysis.citation_type
            if context_analysis
            else CitationType.GENERAL
        )

        return [
            RankedPaper(
                paper=paper,
                relevance_score=0.5,
                relevance_explanation="Ranked by citation count",
                citation_type=citation_type,
            )
            for paper in sorted_papers[: self.top_k]
        ]

    def fill_citation(
        self,
        tex_file: Path,
        bibcode: str,
        line: int,
        column: int,
        bib_file: Optional[Path] = None,
    ) -> FillResult:
        """Fill an empty citation with a paper.

        Args:
            tex_file: Path to the LaTeX file
            bibcode: The paper's bibcode
            line: Line number of the empty citation
            column: Column position of the empty citation
            bib_file: Optional path to .bib file (auto-detected if not provided)

        Returns:
            FillResult with success status and citation key
        """
        try:
            # Get the paper (from database or ADS)
            paper = self.paper_repo.get(bibcode)
            if not paper:
                paper = self.ads_client.fetch_paper(bibcode)
                if not paper:
                    return FillResult(
                        success=False, error=f"Paper not found: {bibcode}"
                    )

            # Generate citation key
            citation_key = paper.generate_citation_key(
                format=settings.citation_key_format,
                lowercase=settings.citation_key_lowercase,
                max_length=settings.citation_key_max_length,
            )

            # Parse LaTeX file
            parser = LaTeXParser(tex_file)
            bib_info = parser.get_bibliography_info()

            # Determine bib file
            if bib_file is None and bib_info.uses_bib_file:
                bib_file = tex_file.parent / bib_info.bib_file

            # Fill the citation
            parser.fill_citation(line, column, citation_key)

            # Add to bibliography
            if bib_file:
                bibtex = paper.bibtex
                if not bibtex:
                    bibtex = self.ads_client.generate_bibtex(bibcode)
                    if bibtex:
                        paper.bibtex = bibtex
                        self.paper_repo.add(paper)

                if bibtex:
                    add_bibtex_entry(bib_file, bibtex)
            else:
                bibitem_text = format_bibitem_from_paper(paper)
                parser.add_bibitem(citation_key, bibitem_text)

            return FillResult(
                success=True, citation_key=citation_key, bibcode=bibcode
            )

        except Exception as e:
            return FillResult(success=False, error=str(e))

    def process_document(
        self,
        tex_file: Path,
        bib_file: Optional[Path] = None,
        auto_fill: bool = False,
    ) -> list[CitationResult]:
        """Process all empty citations in a document.

        Args:
            tex_file: Path to the LaTeX file
            bib_file: Optional path to .bib file
            auto_fill: If True, automatically fill with top result

        Returns:
            List of CitationResult objects
        """
        results = []
        empty_citations = self.find_empty_citations(tex_file)

        for citation in empty_citations:
            result = self.search_for_citation(
                citation.context, empty_citation=citation
            )

            if auto_fill and result.ranked_papers:
                top_paper = result.ranked_papers[0].paper
                fill_result = self.fill_citation(
                    tex_file,
                    top_paper.bibcode,
                    citation.line,
                    citation.column,
                    bib_file,
                )
                if fill_result.success:
                    result.selected_paper = top_paper
                    result.citation_key = fill_result.citation_key

            results.append(result)

        return results
