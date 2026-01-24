"""LLM client for context analysis, keyword extraction, and paper ranking."""

import json
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from src.core.config import settings
from src.db.models import Paper
from src.db.repository import ApiUsageRepository


class CitationType(str, Enum):
    """Types of citations based on their purpose."""

    FOUNDATIONAL = "foundational"  # Seminal papers: "X established that..."
    METHODOLOGICAL = "methodological"  # Technique papers: "Following the method of X..."
    SUPPORTING = "supporting"  # Corroborating evidence: "consistent with X..."
    CONTRASTING = "contrasting"  # Papers to contrast against: "unlike X, we find..."
    REVIEW = "review"  # Review articles: "see X for a review"
    GENERAL = "general"  # General reference


@dataclass
class ContextAnalysis:
    """Result of analyzing LaTeX context for citation needs."""

    topic: str  # Main topic/subject being discussed
    claim: str  # The specific claim or statement being made
    citation_type: CitationType  # What kind of citation is needed
    keywords: list[str]  # Keywords for ADS search
    search_query: str  # Formatted ADS search query
    reasoning: str  # Explanation of the analysis


@dataclass
class RankedPaper:
    """A paper with its relevance score and explanation."""

    paper: Paper
    relevance_score: float  # 0.0 to 1.0
    relevance_explanation: str
    citation_type: CitationType


class LLMClient:
    """Client for LLM-based context analysis and paper ranking.

    Supports both Anthropic Claude and OpenAI APIs with automatic fallback.
    """

    def __init__(self, prefer_anthropic: bool = True):
        """Initialize the LLM client.

        Args:
            prefer_anthropic: If True, prefer Claude over OpenAI when both are available
        """
        self.prefer_anthropic = prefer_anthropic
        self.usage_repo = ApiUsageRepository()
        self._anthropic_client = None
        self._openai_client = None

    @property
    def anthropic_client(self):
        """Lazy load Anthropic client."""
        if self._anthropic_client is None and settings.anthropic_api_key:
            try:
                import anthropic

                self._anthropic_client = anthropic.Anthropic(
                    api_key=settings.anthropic_api_key
                )
            except ImportError:
                pass
        return self._anthropic_client

    @property
    def openai_client(self):
        """Lazy load OpenAI client."""
        if self._openai_client is None and settings.openai_api_key:
            try:
                import openai

                self._openai_client = openai.OpenAI(api_key=settings.openai_api_key)
            except ImportError:
                pass
        return self._openai_client

    def _get_available_backend(self) -> str:
        """Determine which LLM backend to use."""
        if self.prefer_anthropic and self.anthropic_client:
            return "anthropic"
        elif self.openai_client:
            return "openai"
        elif self.anthropic_client:
            return "anthropic"
        else:
            raise LLMNotAvailable(
                "No LLM API available. Please set ANTHROPIC_API_KEY or OPENAI_API_KEY"
            )

    def _call_anthropic(self, system_prompt: str, user_prompt: str) -> str:
        """Call Claude API."""
        response = self.anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        self.usage_repo.increment_anthropic()
        return response.content[0].text

    def _call_openai(self, system_prompt: str, user_prompt: str) -> str:
        """Call OpenAI API."""
        response = self.openai_client.chat.completions.create(
            model="gpt-4o",
            max_tokens=2048,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        self.usage_repo.increment_openai()
        return response.choices[0].message.content

    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """Call the appropriate LLM backend with automatic fallback."""
        backend = self._get_available_backend()

        if backend == "anthropic":
            try:
                return self._call_anthropic(system_prompt, user_prompt)
            except Exception as e:
                # Fallback to OpenAI if Anthropic fails (e.g., no credits)
                if self.openai_client:
                    print(f"Anthropic API error: {e}. Falling back to OpenAI...")
                    return self._call_openai(system_prompt, user_prompt)
                raise
        else:
            try:
                return self._call_openai(system_prompt, user_prompt)
            except Exception as e:
                # Fallback to Anthropic if OpenAI fails
                if self.anthropic_client:
                    print(f"OpenAI API error: {e}. Falling back to Anthropic...")
                    return self._call_anthropic(system_prompt, user_prompt)
                raise

    def analyze_context(self, latex_context: str) -> ContextAnalysis:
        """Analyze LaTeX context to understand citation needs.

        Args:
            latex_context: The surrounding text from the LaTeX document

        Returns:
            ContextAnalysis with topic, claim, citation type, and search keywords
        """
        system_prompt = """You are an expert scientific writing assistant specializing in astrophysics and physics papers.
Your task is to analyze LaTeX text that contains an empty citation (\\cite{} or similar) and determine what kind of paper should be cited.

IMPORTANT: Identify the NATURE of the statement:
- **Introductory/Overview statements** (e.g., "X is a fundamental process...", "X plays a key role...") need REVIEW papers or classic foundational papers with high citation counts
- **Specific claims** about measurements or observations need the original papers that made those observations
- **Methodological statements** need papers describing the techniques used
- **Comparative statements** need papers being compared against

Analyze the context and return a JSON object with:
1. "topic": The main scientific topic being discussed (e.g., "dark matter halos", "stellar evolution")
2. "claim": The specific claim or statement that needs a citation
3. "citation_type": One of:
   - "foundational": For seminal papers establishing fundamental concepts - use for broad introductory statements about well-known phenomena
   - "review": For review articles - PREFER THIS for general overview/introductory statements that summarize a field
   - "methodological": For papers describing methods/techniques ("Following the method of X...")
   - "supporting": For papers with specific results that support a claim ("consistent with X...", "observations show...")
   - "contrasting": For papers to contrast against ("unlike X...", "in contrast to X...")
   - "general": Only for very specific technical references
4. "keywords": A list of 3-5 specific keywords for searching NASA ADS (use standard astronomical terms)
5. "search_query": A well-formed ADS search query. For review/foundational types, include "review" or use broad terms. Example: "core-collapse supernovae review" or "supernova neutron star formation"
6. "reasoning": Brief explanation of your analysis, especially why you chose this citation type

Return ONLY the JSON object, no additional text."""

        user_prompt = f"""Analyze this LaTeX context that contains an empty citation:

{latex_context}

Return the JSON analysis."""

        response = self._call_llm(system_prompt, user_prompt)

        # Parse JSON response
        try:
            # Handle potential markdown code blocks
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            response = response.strip()

            data = json.loads(response)

            return ContextAnalysis(
                topic=data.get("topic", ""),
                claim=data.get("claim", ""),
                citation_type=CitationType(
                    data.get("citation_type", "general").lower()
                ),
                keywords=data.get("keywords", []),
                search_query=data.get("search_query", ""),
                reasoning=data.get("reasoning", ""),
            )
        except (json.JSONDecodeError, ValueError) as e:
            # Fallback: extract keywords from context directly
            return self._fallback_context_analysis(latex_context, str(e))

    def _fallback_context_analysis(
        self, latex_context: str, error: str
    ) -> ContextAnalysis:
        """Fallback context analysis when LLM parsing fails."""
        import re

        # Extract potential keywords from the context
        # Remove LaTeX commands
        clean_text = re.sub(r"\\[a-zA-Z]+\{[^}]*\}", " ", latex_context)
        clean_text = re.sub(r"\\[a-zA-Z]+", " ", clean_text)
        clean_text = re.sub(r"[{}$]", " ", clean_text)

        # Get words longer than 4 characters, excluding common words
        words = re.findall(r"\b[a-zA-Z]{4,}\b", clean_text.lower())
        stopwords = {
            "that",
            "this",
            "with",
            "from",
            "have",
            "been",
            "were",
            "which",
            "their",
            "there",
            "about",
            "would",
            "could",
            "should",
            "these",
            "those",
            "other",
        }
        keywords = [w for w in words if w not in stopwords][:5]

        return ContextAnalysis(
            topic=" ".join(keywords[:2]) if keywords else "astronomy",
            claim=latex_context[:200],
            citation_type=CitationType.GENERAL,
            keywords=keywords or ["astronomy"],
            search_query=" AND ".join(keywords[:3]) if keywords else "astronomy",
            reasoning=f"Fallback analysis due to: {error}",
        )

    def rank_papers(
        self,
        papers: list[Paper],
        context: str,
        context_analysis: Optional[ContextAnalysis] = None,
        top_k: int = 5,
    ) -> list[RankedPaper]:
        """Rank papers by relevance to the citation context.

        Args:
            papers: List of candidate papers to rank
            context: The LaTeX context needing a citation
            context_analysis: Optional pre-computed context analysis
            top_k: Number of top papers to return

        Returns:
            List of RankedPaper objects sorted by relevance
        """
        if not papers:
            return []

        # Use existing analysis or compute new one
        if context_analysis is None:
            context_analysis = self.analyze_context(context)

        # Get notes for papers (for boosting)
        from src.db.repository import NoteRepository
        note_repo = NoteRepository(auto_embed=False)

        # Prepare paper summaries for the LLM
        paper_summaries = []
        for i, paper in enumerate(papers):
            summary = {
                "id": i,
                "bibcode": paper.bibcode,
                "title": paper.title,
                "year": paper.year,
                "citations": paper.citation_count or 0,
                "abstract": (paper.abstract[:500] + "...") if paper.abstract and len(paper.abstract) > 500 else paper.abstract,
            }

            # Add "my paper" flag for boosting
            if paper.is_my_paper:
                summary["is_my_paper"] = True

            # Add user note if exists (for context and boosting)
            note = note_repo.get(paper.bibcode)
            if note:
                summary["user_note"] = note.content[:200] + "..." if len(note.content) > 200 else note.content

            paper_summaries.append(summary)

        system_prompt = """You are an expert scientific paper recommender for astrophysics research.
Your task is to rank papers by their relevance for citing in a specific context.

RANKING CRITERIA (in order of importance):
1. **User's own papers (is_my_paper=true)**: Give STRONG preference to the user's own papers when relevant. Self-citation is appropriate and expected in academic writing when the user's previous work is genuinely relevant.
2. **Papers with user notes**: If a paper has a "user_note" field, this indicates the user has specifically annotated this paper as relevant. Consider the note content and give extra weight to papers with notes.
3. **Match citation type needed**:
   - For "review" or "foundational" needs: STRONGLY prefer review papers, Annual Reviews, Living Reviews, or highly-cited (>500) classic papers
   - For "supporting" needs: prefer papers with specific observational/theoretical results
   - For "methodological" needs: prefer papers describing techniques
4. **Relevance to the specific claim**: How directly does the paper address what's being stated?
5. **Paper authority**: High citation count indicates community acceptance (especially important for foundational/review citations)
6. **Appropriateness**: A review paper is better than a narrow technical paper for broad overview statements

IMPORTANT:
- For introductory/overview statements, a well-cited review paper (even if slightly older) is MUCH better than a recent narrow paper.
- Papers marked as "is_my_paper" should get a significant boost (add ~0.2 to relevance score) when they are relevant to the context.
- Papers with "user_note" should be carefully considered - the user annotated them for a reason.

Return a JSON array of rankings with:
- "id": The paper ID from the input
- "relevance_score": Float from 0.0 to 1.0 (give review papers HIGH scores for overview statements, boost user's own papers)
- "explanation": Brief explanation of why this paper is relevant (1-2 sentences). Mention if it's the user's own paper.
- "citation_type": The type of citation this paper would serve (foundational, review, supporting, methodological, contrasting)

Return ONLY the JSON array, sorted by relevance_score descending. Include all papers."""

        user_prompt = f"""Context for citation:
{context}

Analysis:
- Topic: {context_analysis.topic}
- Claim: {context_analysis.claim}
- Citation type needed: {context_analysis.citation_type.value}

Candidate papers:
{json.dumps(paper_summaries, indent=2)}

Rank these papers by relevance for this citation."""

        response = self._call_llm(system_prompt, user_prompt)

        # Parse response
        try:
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            response = response.strip()

            rankings = json.loads(response)

            ranked_papers = []
            for ranking in rankings[:top_k]:
                paper_id = ranking.get("id", 0)
                if 0 <= paper_id < len(papers):
                    ranked_papers.append(
                        RankedPaper(
                            paper=papers[paper_id],
                            relevance_score=float(ranking.get("relevance_score", 0.5)),
                            relevance_explanation=ranking.get("explanation", ""),
                            citation_type=CitationType(
                                ranking.get("citation_type", "general").lower()
                            ),
                        )
                    )

            # Sort by relevance score
            ranked_papers.sort(key=lambda x: x.relevance_score, reverse=True)
            return ranked_papers[:top_k]

        except (json.JSONDecodeError, ValueError):
            # Fallback: return papers sorted by citation count
            return self._fallback_ranking(papers, context_analysis, top_k)

    def _fallback_ranking(
        self, papers: list[Paper], context_analysis: ContextAnalysis, top_k: int
    ) -> list[RankedPaper]:
        """Fallback ranking based on citation count, with boosts for my papers and notes."""
        from src.db.repository import NoteRepository
        note_repo = NoteRepository(auto_embed=False)

        # Calculate scores with boosts
        scored_papers = []
        for paper in papers:
            # Base score from citations (normalized to 0-0.5 range)
            base_score = min((paper.citation_count or 0) / 1000, 0.5)

            # Boost for "my paper"
            my_paper_boost = 0.3 if paper.is_my_paper else 0.0

            # Boost for having a note
            note = note_repo.get(paper.bibcode)
            note_boost = 0.2 if note else 0.0

            total_score = min(base_score + my_paper_boost + note_boost, 1.0)

            explanation = "Ranked by citation count"
            if paper.is_my_paper:
                explanation = "Your paper (boosted)"
            elif note:
                explanation = "Has user note (boosted)"

            scored_papers.append((paper, total_score, explanation))

        # Sort by score
        scored_papers.sort(key=lambda x: x[1], reverse=True)

        return [
            RankedPaper(
                paper=paper,
                relevance_score=score,
                relevance_explanation=explanation,
                citation_type=context_analysis.citation_type,
            )
            for paper, score, explanation in scored_papers[:top_k]
        ]

    def generate_citation_reason(
        self, paper: Paper, context: str, citation_type: CitationType
    ) -> str:
        """Generate a human-readable explanation of why a paper should be cited.

        Args:
            paper: The paper being cited
            context: The LaTeX context
            citation_type: The type of citation

        Returns:
            A brief explanation string
        """
        system_prompt = """You are a scientific writing assistant. Generate a brief (1-2 sentence)
explanation of why a specific paper should be cited in a given context.
Be specific about what aspect of the paper is relevant."""

        user_prompt = f"""Context requiring citation:
{context}

Paper to cite:
- Title: {paper.title}
- Authors: {paper.first_author} et al. ({paper.year})
- Abstract: {paper.abstract[:500] if paper.abstract else 'Not available'}

Citation type: {citation_type.value}

Explain why this paper should be cited here (1-2 sentences):"""

        try:
            return self._call_llm(system_prompt, user_prompt).strip()
        except Exception:
            return f"This paper is relevant as a {citation_type.value} reference for the discussion."

    def extract_keywords_only(self, text: str) -> list[str]:
        """Extract search keywords from text without full context analysis.

        This is a lightweight operation for quick keyword extraction.

        Args:
            text: Text to extract keywords from

        Returns:
            List of keywords suitable for ADS search
        """
        system_prompt = """You are a scientific keyword extractor for NASA ADS searches.
Extract 3-5 specific astronomical/physics keywords from the given text.
Use standard terminology that would appear in paper titles and abstracts.

Return ONLY a JSON array of strings, nothing else."""

        user_prompt = f"Extract search keywords from: {text}"

        try:
            response = self._call_llm(system_prompt, user_prompt)
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            return json.loads(response.strip())
        except (json.JSONDecodeError, Exception):
            # Fallback to simple extraction
            import re

            words = re.findall(r"\b[a-zA-Z]{4,}\b", text.lower())
            return list(dict.fromkeys(words))[:5]  # Dedupe while preserving order


class LLMNotAvailable(Exception):
    """Raised when no LLM API is available."""

    pass
