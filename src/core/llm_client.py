"""LLM client for context analysis, keyword extraction, and paper ranking."""

import json
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Any

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

    Supports OpenAI, Anthropic, Gemini, and Ollama APIs.
    """

    def __init__(self):
        """Initialize the LLM client."""
        self.usage_repo = ApiUsageRepository()
        self._anthropic_client = None
        self._openai_client = None
        self._gemini_client = None
        
        # Configure providers based on settings
        self.provider = settings.llm_provider

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

    def _get_gemini_client(self):
        """Lazy initialize Gemini client."""
        if self._gemini_client is None and settings.gemini_api_key:
            try:
                from google import genai
                self._gemini_client = genai.Client(api_key=settings.gemini_api_key)
            except ImportError:
                pass
        return self._gemini_client

    def _call_anthropic(self, system_prompt: str, user_prompt: str) -> str:
        """Call Claude API."""
        if not self.anthropic_client:
            raise ValueError("Anthropic client not initialized. Check API key.")
            
        response = self.anthropic_client.messages.create(
            model=settings.anthropic_model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            temperature=0.0
        )
        self.usage_repo.increment_anthropic()
        return response.content[0].text

    def _call_openai(self, system_prompt: str, user_prompt: str) -> str:
        """Call OpenAI API."""
        if not self.openai_client:
            raise ValueError("OpenAI client not initialized. Check API key.")
            
        response = self.openai_client.chat.completions.create(
            model=settings.openai_model,
            max_tokens=4096,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0
        )
        self.usage_repo.increment_openai()
        return response.choices[0].message.content

    def _call_gemini(self, system_prompt: str, user_prompt: str) -> str:
        """Call Google Gemini API."""
        client = self._get_gemini_client()
        if client is None:
            raise ValueError("Gemini not configured or google-genai not installed.")

        from google.genai import types

        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                candidate_count=1,
                max_output_tokens=4096,
                temperature=0.0,
            ),
        )
        return response.text

    def _call_ollama(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        """Call Ollama API via HTTP."""
        import requests
        
        # Llama3 and recent models support system prompts properly
        payload = {
            "model": settings.ollama_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False,
            "options": {
                "temperature": 0.0,
                "num_predict": 4096
            }
        }
        
        if kwargs.get("json_mode"):
             payload["format"] = "json"
        
        try:
            response = requests.post(
                f"{settings.ollama_base_url}/api/chat",
                json=payload,
                timeout=120
            )
            response.raise_for_status()
            result = response.json()
            return result["message"]["content"]
        except requests.RequestException as e:
            raise ValueError(f"Ollama API call failed: {e}")

    def _call_llm(self, system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
        """Call the configured LLM backend."""
        provider = self.provider

        try:
            if provider == "anthropic":
                return self._call_anthropic(system_prompt, user_prompt)
            elif provider == "openai":
                return self._call_openai(system_prompt, user_prompt)
            elif provider == "gemini":
                return self._call_gemini(system_prompt, user_prompt)
            elif provider == "ollama":
                # Ollama support might be limited by model capabilities, but we try
                return self._call_ollama(system_prompt, user_prompt, json_mode=json_mode)
            else:
                raise ValueError(f"Unknown LLM provider: {provider}")
        except Exception as e:
            raise LLMNotAvailable(f"LLM provider '{provider}' failed: {str(e)}")

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

        try:
            response = self._call_llm(system_prompt, user_prompt, json_mode=True)
        except Exception as e:
            # Fallback if LLM call fails (e.g. no key, connection error)
            return self._fallback_context_analysis(latex_context, str(e))

        # Parse JSON response
        try:
            # Handle potential markdown code blocks
            response = response.strip()
            if response.startswith("```"):
                # Handle generic code block or json block
                parts = response.split("```")
                if len(parts) > 1:
                    content = parts[1]
                    if content.startswith("json"):
                        content = content[4:]
                    response = content
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
            "that", "this", "with", "from", "have", "been", "were", "which",
            "their", "there", "about", "would", "could", "should", "these",
            "those", "other",
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
        
        # Batch fetch notes
        bibcodes = [p.bibcode for p in papers]
        notes = note_repo.get_batch(bibcodes)
        notes_map = {n.bibcode: n for n in notes}

        # Prepare batches (chunk size 8 for better parallelism)
        chunk_size = 8
        batches = [papers[i:i + chunk_size] for i in range(0, len(papers), chunk_size)]
        
        # Define worker function for processing a batch
        def process_batch(batch_papers):
            batch_summaries = []
            for i, paper in enumerate(batch_papers):
                summary = {
                    "id": i, # Local ID within batch
                    "bibcode": paper.bibcode,
                    "title": paper.title,
                    "year": paper.year,
                    "citations": paper.citation_count or 0,
                    "abstract": (paper.abstract[:500] + "...") if paper.abstract and len(paper.abstract) > 500 else paper.abstract,
                }
                if paper.is_my_paper:
                    summary["is_my_paper"] = True
                note = notes_map.get(paper.bibcode)
                if note:
                    summary["user_note"] = note.content[:200] + "..." if len(note.content) > 200 else note.content
                batch_summaries.append(summary)
            
            # Reduce prompt overhead for batches
            system_prompt = """You are an expert scientific paper recommender. Rank these papers by relevance to the context.
RANKING CRITERIA:
1. **User's own papers (is_my_paper=true)** or papers with **user_note**: Give STRONG preference.
2. **Match citation type**: "Review"/"Foundational" -> prefer heavily cited/review papers. "Methodological" -> prefer technique papers.
3. **Relevance**: Direct address of the claim.
4. **Authority**: High citation count.

Return a JSON array of rankings with:
- "id": The local paper ID from input
- "relevance_score": Float 0.0-1.0
- "explanation": Brief reason (1 sentence)
- "citation_type": The type this paper serves
"""
            user_prompt = f"""Context: {context}
Analysis: Topic: {context_analysis.topic}, Claim: {context_analysis.claim}, Needs: {context_analysis.citation_type.value}

Candidate papers:
{json.dumps(batch_summaries, indent=2)}

Rank these papers."""

            try:
                response = self._call_llm(system_prompt, user_prompt)
                # Cleanup and parse
                response = response.strip()
                if response.startswith("```"):
                    parts = response.split("```")
                    if len(parts) > 1:
                        content = parts[1]
                        if content.startswith("json"):
                            content = content[4:]
                        response = content
                
                rankings = json.loads(response.strip())
                
                # Map back to real paper objects
                batch_results = []
                for ranking in rankings:
                    local_id = ranking.get("id")
                    if local_id is not None and 0 <= local_id < len(batch_papers):
                        batch_results.append(
                            RankedPaper(
                                paper=batch_papers[local_id],
                                relevance_score=float(ranking.get("relevance_score", 0.5)),
                                relevance_explanation=ranking.get("explanation", ""),
                                citation_type=CitationType(
                                    ranking.get("citation_type", "general").lower()
                                ),
                            )
                        )
                return batch_results
            except Exception as e:
                print(f"Batch ranking failed: {e}")
                return []

        # Run batches in parallel
        # Note: If using Ollama, we might want to limit workers to avoid overloading local inference
        max_workers = 5
        if self.provider == "ollama":
            max_workers = 1 # Sequential for local LLM
            
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        all_ranked_papers = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_batch = {executor.submit(process_batch, batch): batch for batch in batches}
            for future in as_completed(future_to_batch):
                try:
                    results = future.result()
                    all_ranked_papers.extend(results)
                except Exception as e:
                    print(f"Batch processing exception: {e}")
        
        # If we got no results (e.g. all failed), fallback
        if not all_ranked_papers:
            return self._fallback_ranking(papers, context_analysis, top_k, notes_map)
            
        if len(all_ranked_papers) < len(papers) * 0.5: # If >50% failed
             print("Too many failures, falling back to heuristic ranking")
             return self._fallback_ranking(papers, context_analysis, top_k, notes_map)

        # Sort and return
        all_ranked_papers.sort(key=lambda x: x.relevance_score, reverse=True)
        return all_ranked_papers[:top_k]

    def _fallback_ranking(
        self, 
        papers: list[Paper], 
        context_analysis: ContextAnalysis, 
        top_k: int,
        notes_map: dict = None
    ) -> list[RankedPaper]:
        """Fallback ranking based on citation count, with boosts for my papers and notes."""
        if notes_map is None:
            # Should normally be passed, but handle if not
            from src.db.repository import NoteRepository
            note_repo = NoteRepository(auto_embed=False)
            bibcodes = [p.bibcode for p in papers]
            notes = note_repo.get_batch(bibcodes)
            notes_map = {n.bibcode: n for n in notes}

        # Calculate scores with boosts
        scored_papers = []
        for paper in papers:
            # Base score from citations (normalized to 0-0.5 range)
            base_score = min((paper.citation_count or 0) / 1000, 0.5)

            # Boost for "my paper"
            my_paper_boost = 0.3 if paper.is_my_paper else 0.0

            # Boost for having a note
            note = notes_map.get(paper.bibcode)
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
Be specific about what aspect of the paper is relevant. Return ONLY the explanation."""

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
            response = self._call_llm(system_prompt, user_prompt, json_mode=True)
            response = response.strip()
            if response.startswith("```"):
                parts = response.split("```")
                if len(parts) > 1:
                    content = parts[1]
                    if content.startswith("json"):
                         content = content[4:]
                    response = content
            return json.loads(response.strip())
        except (json.JSONDecodeError, Exception):
            # Fallback to simple extraction
            import re

            words = re.findall(r"\b[a-zA-Z]{4,}\b", text.lower())
            return list(dict.fromkeys(words))[:5]  # Dedupe while preserving order


class LLMNotAvailable(Exception):
    """Raised when no LLM API is available."""

    pass
