"""ADS (Astrophysics Data System) API client."""

import json
import re
from typing import Optional

import ads

from src.core.config import settings
from src.db.models import Paper
from src.db.repository import ApiUsageRepository, PaperRepository, CitationRepository, get_db


class ADSClient:
    """Client for interacting with the NASA ADS API."""

    # ADS API fields to request
    FIELDS = [
        "bibcode",
        "title",
        "abstract",
        "author",
        "year",
        "pub",
        "volume",
        "page",
        "doi",
        "identifier",
        "citation_count",
        "reference",
        "citation",
    ]

    def __init__(self):
        # Set up ADS token
        if settings.ads_api_key:
            ads.config.token = settings.ads_api_key

        self.paper_repo = PaperRepository()
        self.citation_repo = CitationRepository()
        self.usage_repo = ApiUsageRepository()

    def _check_rate_limit(self) -> bool:
        """Check if we can make an API call."""
        can_call, is_warning = self.usage_repo.can_make_ads_call()
        if not can_call:
            raise RateLimitExceeded("Daily ADS API limit reached (5000 calls)")
        if is_warning:
            print("Warning: Approaching daily ADS API limit (>4500 calls)")
        return True

    def _track_call(self):
        """Track an API call."""
        self.usage_repo.increment_ads()

    @staticmethod
    def parse_bibcode_from_url(url: str) -> Optional[str]:
        """Extract bibcode from an ADS URL.

        Examples:
            https://ui.adsabs.harvard.edu/abs/2026ApJ...996...35P/abstract
            -> 2026ApJ...996...35P
        """
        # Pattern to match ADS URLs
        patterns = [
            r"ui\.adsabs\.harvard\.edu/abs/([^/]+)",
            r"adsabs\.harvard\.edu/abs/([^/]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        # If it's already a bibcode (no URL), return as-is
        if not url.startswith("http"):
            return url

        return None

    def _ads_article_to_paper(self, article: ads.search.Article) -> Paper:
        """Convert an ADS Article to our Paper model."""
        # Get arXiv ID from identifiers
        arxiv_id = None
        if hasattr(article, "identifier") and article.identifier:
            for ident in article.identifier:
                if ident.startswith("arXiv:"):
                    arxiv_id = ident.replace("arXiv:", "")
                    break

        # Format authors as JSON array
        authors = json.dumps(article.author) if article.author else None

        # Get first page
        pages = None
        if hasattr(article, "page") and article.page:
            pages = article.page[0] if isinstance(article.page, list) else article.page

        # Get DOI
        doi = None
        if hasattr(article, "doi") and article.doi:
            doi = article.doi[0] if isinstance(article.doi, list) else article.doi

        # Construct PDF URL (ADS or arXiv)
        pdf_url = None
        if arxiv_id:
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        else:
            pdf_url = f"https://ui.adsabs.harvard.edu/link_gateway/{article.bibcode}/PUB_PDF"

        # Convert year to int (ADS returns it as str)
        year = None
        if article.year:
            try:
                year = int(article.year)
            except (ValueError, TypeError):
                pass

        return Paper(
            bibcode=article.bibcode,
            title=article.title[0] if article.title else "Unknown",
            abstract=article.abstract,
            authors=authors,
            year=year,
            journal=article.pub,
            volume=article.volume,
            pages=pages,
            doi=doi,
            arxiv_id=arxiv_id,
            citation_count=article.citation_count,
            pdf_url=pdf_url,
        )

    def fetch_paper(self, bibcode: str, save: bool = True) -> Optional[Paper]:
        """Fetch a single paper by bibcode.

        Args:
            bibcode: The ADS bibcode or URL
            save: Whether to save to database

        Returns:
            Paper object or None if not found
        """
        # Parse bibcode from URL if needed
        bibcode = self.parse_bibcode_from_url(bibcode) or bibcode

        # Check cache first
        existing = self.paper_repo.get(bibcode)
        if existing:
            return existing

        self._check_rate_limit()

        try:
            query = ads.SearchQuery(
                bibcode=bibcode,
                fl=self.FIELDS,
            )
            articles = list(query)
            self._track_call()

            if not articles:
                return None

            paper = self._ads_article_to_paper(articles[0])

            if save:
                paper = self.paper_repo.add(paper)

            return paper

        except Exception as e:
            print(f"Error fetching paper {bibcode}: {e}")
            return None

    def search(
        self,
        query: str,
        limit: int = 10,
        sort: str = "citation_count desc",
        year_range: Optional[tuple[int, int]] = None,
        save: bool = True,
    ) -> list[Paper]:
        """Search ADS for papers.

        Args:
            query: Search query string
            limit: Maximum number of results
            sort: Sort order (default: by citation count)
            year_range: Optional (min_year, max_year) tuple
            save: Whether to save results to database

        Returns:
            List of Paper objects
        """
        self._check_rate_limit()

        # Build query
        q = query
        if year_range:
            q = f"({q}) AND year:[{year_range[0]} TO {year_range[1]}]"

        try:
            search = ads.SearchQuery(
                q=q,
                fl=self.FIELDS,
                sort=sort,
                rows=limit,
            )
            articles = list(search)
            self._track_call()

            papers = []
            for article in articles:
                paper = self._ads_article_to_paper(article)
                if save:
                    paper = self.paper_repo.add(paper)
                papers.append(paper)

            return papers

        except Exception as e:
            print(f"Error searching ADS: {e}")
            return []

    def fetch_references(
        self,
        bibcode: str,
        limit: int = 30,
        save: bool = True,
    ) -> list[Paper]:
        """Fetch papers that this paper cites (references).

        Args:
            bibcode: The paper's bibcode
            limit: Maximum number of references to fetch
            save: Whether to save to database

        Returns:
            List of referenced Paper objects
        """
        bibcode = self.parse_bibcode_from_url(bibcode) or bibcode

        self._check_rate_limit()

        try:
            # Query for references
            query = ads.SearchQuery(
                q=f"references(bibcode:{bibcode})",
                fl=self.FIELDS,
                rows=limit,
                sort="citation_count desc",
            )
            articles = list(query)
            self._track_call()

            papers = []
            for article in articles:
                paper = self._ads_article_to_paper(article)
                if save:
                    paper = self.paper_repo.add(paper)
                    # Record citation relationship
                    self.citation_repo.add(citing_bibcode=bibcode, cited_bibcode=paper.bibcode)
                papers.append(paper)

            return papers

        except Exception as e:
            print(f"Error fetching references for {bibcode}: {e}")
            return []

    def fetch_citations(
        self,
        bibcode: str,
        limit: int = 30,
        min_citation_count: int = 0,
        save: bool = True,
    ) -> list[Paper]:
        """Fetch papers that cite this paper (citations).

        Args:
            bibcode: The paper's bibcode
            limit: Maximum number of citations to fetch
            min_citation_count: Minimum citation count filter
            save: Whether to save to database

        Returns:
            List of citing Paper objects
        """
        bibcode = self.parse_bibcode_from_url(bibcode) or bibcode

        self._check_rate_limit()

        try:
            # Query for citations
            q = f"citations(bibcode:{bibcode})"
            if min_citation_count > 0:
                q = f"({q}) AND citation_count:[{min_citation_count} TO *]"

            query = ads.SearchQuery(
                q=q,
                fl=self.FIELDS,
                rows=limit,
                sort="citation_count desc",
            )
            articles = list(query)
            self._track_call()

            papers = []
            for article in articles:
                paper = self._ads_article_to_paper(article)
                if save:
                    paper = self.paper_repo.add(paper)
                    # Record citation relationship
                    self.citation_repo.add(citing_bibcode=paper.bibcode, cited_bibcode=bibcode)
                papers.append(paper)

            return papers

        except Exception as e:
            print(f"Error fetching citations for {bibcode}: {e}")
            return []

    def generate_bibtex(self, bibcode: str) -> Optional[str]:
        """Generate BibTeX entry for a paper.

        Args:
            bibcode: The paper's bibcode

        Returns:
            BibTeX string or None
        """
        bibcode = self.parse_bibcode_from_url(bibcode) or bibcode

        self._check_rate_limit()

        try:
            query = ads.ExportQuery(bibcodes=[bibcode], format="bibtex")
            result = query.execute()
            self._track_call()
            return result

        except Exception as e:
            print(f"Error generating BibTeX for {bibcode}: {e}")
            return None

    def generate_aastex(self, bibcode: str) -> Optional[str]:
        """Generate AASTeX bibitem entry for a paper.

        Args:
            bibcode: The paper's bibcode

        Returns:
            AASTeX bibitem string or None
        """
        bibcode = self.parse_bibcode_from_url(bibcode) or bibcode

        self._check_rate_limit()

        try:
            query = ads.ExportQuery(bibcodes=[bibcode], format="aastex")
            result = query.execute()
            self._track_call()
            return result

        except Exception as e:
            print(f"Error generating AASTeX for {bibcode}: {e}")
            return None

    def batch_update_papers(
        self,
        bibcodes: list[str],
        batch_size: int = 50,
    ) -> dict[str, dict]:
        """Batch fetch updated metadata for multiple papers.

        This is more efficient than fetching one paper at a time.

        Args:
            bibcodes: List of bibcodes to update
            batch_size: Number of papers per API call (max 50)

        Returns:
            Dict mapping bibcode to updated fields (citation_count, etc.)
        """
        updates = {}

        for i in range(0, len(bibcodes), batch_size):
            batch = bibcodes[i:i + batch_size]

            self._check_rate_limit()

            try:
                # Use OR query to fetch multiple papers at once
                bibcode_query = " OR ".join(f"bibcode:{b}" for b in batch)
                query = ads.SearchQuery(
                    q=bibcode_query,
                    fl=["bibcode", "citation_count"],
                    rows=batch_size,
                )
                articles = list(query)
                self._track_call()

                for article in articles:
                    updates[article.bibcode] = {
                        "citation_count": article.citation_count,
                    }

            except Exception as e:
                print(f"Error batch updating papers: {e}")

        return updates


class RateLimitExceeded(Exception):
    """Raised when API rate limit is exceeded."""

    pass
