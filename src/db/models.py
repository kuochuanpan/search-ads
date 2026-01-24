"""Database models for search-ads using SQLModel."""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


class Paper(SQLModel, table=True):
    """A scientific paper from ADS."""

    __tablename__ = "papers"

    bibcode: str = Field(primary_key=True, index=True)
    title: str
    abstract: Optional[str] = None
    authors: Optional[str] = None  # JSON array of author names
    year: Optional[int] = None
    journal: Optional[str] = None
    volume: Optional[str] = None
    pages: Optional[str] = None
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    citation_count: Optional[int] = None
    bibtex: Optional[str] = None
    bibitem_aastex: Optional[str] = None  # AASTeX bibitem format from ADS
    pdf_url: Optional[str] = None
    pdf_path: Optional[str] = None
    pdf_embedded: bool = Field(default=False)
    is_my_paper: bool = Field(default=False)  # Papers authored by the user
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    citing: list["Citation"] = Relationship(
        back_populates="citing_paper",
        sa_relationship_kwargs={"foreign_keys": "Citation.citing_bibcode"},
    )
    cited_by: list["Citation"] = Relationship(
        back_populates="cited_paper",
        sa_relationship_kwargs={"foreign_keys": "Citation.cited_bibcode"},
    )
    projects: list["PaperProject"] = Relationship(back_populates="paper")

    @property
    def first_author(self) -> str:
        """Get the first author's last name."""
        import json

        if not self.authors:
            return "Unknown"
        try:
            authors_list = json.loads(self.authors)
            if authors_list:
                # Format is typically "Last, First"
                first = authors_list[0]
                return first.split(",")[0].strip()
        except (json.JSONDecodeError, IndexError):
            pass
        return "Unknown"

    def generate_citation_key(
        self,
        format: str = "bibcode",
        lowercase: bool = True,
        max_length: int = 30,
    ) -> str:
        """Generate a citation key for this paper (default: bibcode)."""
        import re

        author = self.first_author
        year = str(self.year) if self.year else ""

        if format == "bibcode":
            key = self.bibcode
        elif format == "author_year_title":
            # Get first meaningful word from title
            title_word = ""
            if self.title:
                words = re.findall(r"\b[a-zA-Z]{3,}\b", self.title)
                # Skip common words
                skip = {"the", "and", "for", "from", "with", "that", "this", "are", "was"}
                for word in words:
                    if word.lower() not in skip:
                        title_word = word
                        break
            key = f"{author}{year}{title_word}"
        else:  # author_year
            key = f"{author}{year}"

        # Clean up
        key = re.sub(r"[^a-zA-Z0-9]", "", key)

        if lowercase:
            key = key.lower()

        return key[:max_length]


class Citation(SQLModel, table=True):
    """Citation relationship between two papers."""

    __tablename__ = "citations"

    citing_bibcode: str = Field(foreign_key="papers.bibcode", primary_key=True)
    cited_bibcode: str = Field(foreign_key="papers.bibcode", primary_key=True)
    context: Optional[str] = None  # LLM-generated citation reason

    # Relationships
    citing_paper: Optional[Paper] = Relationship(
        back_populates="citing",
        sa_relationship_kwargs={"foreign_keys": "[Citation.citing_bibcode]"},
    )
    cited_paper: Optional[Paper] = Relationship(
        back_populates="cited_by",
        sa_relationship_kwargs={"foreign_keys": "[Citation.cited_bibcode]"},
    )


class Project(SQLModel, table=True):
    """A research project that groups papers."""

    __tablename__ = "projects"

    name: str = Field(primary_key=True)
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    papers: list["PaperProject"] = Relationship(back_populates="project")


class PaperProject(SQLModel, table=True):
    """Association table for papers and projects."""

    __tablename__ = "paper_projects"

    bibcode: str = Field(foreign_key="papers.bibcode", primary_key=True)
    project_name: str = Field(foreign_key="projects.name", primary_key=True)
    added_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    paper: Optional[Paper] = Relationship(back_populates="projects")
    project: Optional[Project] = Relationship(back_populates="papers")


class Search(SQLModel, table=True):
    """Search history for caching."""

    __tablename__ = "searches"

    id: Optional[int] = Field(default=None, primary_key=True)
    query: str
    context: Optional[str] = None  # LaTeX context that triggered search
    results: Optional[str] = None  # JSON array of bibcodes
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ApiUsage(SQLModel, table=True):
    """Track API usage for rate limiting."""

    __tablename__ = "api_usage"

    date: str = Field(primary_key=True)  # YYYY-MM-DD
    ads_calls: int = Field(default=0)
    openai_calls: int = Field(default=0)
    anthropic_calls: int = Field(default=0)


class Note(SQLModel, table=True):
    """A user note attached to a paper."""

    __tablename__ = "notes"

    id: Optional[int] = Field(default=None, primary_key=True)
    bibcode: str = Field(foreign_key="papers.bibcode", index=True)
    content: str  # The note text
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
