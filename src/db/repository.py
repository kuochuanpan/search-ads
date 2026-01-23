"""Database repository for CRUD operations."""

import json
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from sqlmodel import Session, SQLModel, create_engine, select

from src.core.config import settings, ensure_data_dirs
from src.db.models import ApiUsage, Citation, Paper, PaperProject, Project, Search


class Database:
    """Database connection and operations manager."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or settings.db_path
        ensure_data_dirs()

        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            echo=False,
            connect_args={"check_same_thread": False},
        )

    def create_tables(self):
        """Create all database tables."""
        SQLModel.metadata.create_all(self.engine)

    def get_session(self) -> Session:
        """Get a new database session."""
        return Session(self.engine)


# Global database instance
_db: Optional[Database] = None


def get_db() -> Database:
    """Get or create the global database instance."""
    global _db
    if _db is None:
        _db = Database()
        _db.create_tables()
    return _db


class PaperRepository:
    """Repository for Paper CRUD operations."""

    def __init__(self, db: Optional[Database] = None, auto_embed: bool = True):
        """Initialize the paper repository.

        Args:
            db: Database instance (uses global if not provided)
            auto_embed: Whether to automatically embed papers in vector store
        """
        self.db = db or get_db()
        self.auto_embed = auto_embed
        self._vector_store = None

    @property
    def vector_store(self):
        """Lazy load the vector store."""
        if self._vector_store is None:
            from src.db.vector_store import get_vector_store
            self._vector_store = get_vector_store()
        return self._vector_store

    def add(self, paper: Paper, embed: Optional[bool] = None) -> Paper:
        """Add a paper to the database.

        Args:
            paper: Paper to add
            embed: Whether to embed in vector store (defaults to self.auto_embed)

        Returns:
            The added/updated paper
        """
        should_embed = embed if embed is not None else self.auto_embed

        with self.db.get_session() as session:
            # Check if exists
            existing = session.get(Paper, paper.bibcode)
            if existing:
                # Update existing
                for key, value in paper.model_dump(exclude_unset=True).items():
                    if key != "bibcode" and value is not None:
                        setattr(existing, key, value)
                existing.updated_at = datetime.utcnow()
                session.add(existing)
                session.commit()
                session.refresh(existing)
                result = existing
            else:
                session.add(paper)
                session.commit()
                session.refresh(paper)
                result = paper

        # Embed in vector store if requested
        if should_embed and result.abstract:
            try:
                self.vector_store.embed_paper(result)
            except Exception as e:
                # Don't fail the add if embedding fails
                print(f"Warning: Failed to embed paper {result.bibcode}: {e}")

        return result

    def get(self, bibcode: str) -> Optional[Paper]:
        """Get a paper by bibcode."""
        with self.db.get_session() as session:
            return session.get(Paper, bibcode)

    def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
        project: Optional[str] = None,
        year_min: Optional[int] = None,
        year_max: Optional[int] = None,
        min_citations: Optional[int] = None,
    ) -> list[Paper]:
        """Get all papers with optional filters."""
        with self.db.get_session() as session:
            query = select(Paper)

            if project:
                query = query.join(PaperProject).where(PaperProject.project_name == project)

            if year_min:
                query = query.where(Paper.year >= year_min)
            if year_max:
                query = query.where(Paper.year <= year_max)
            if min_citations:
                query = query.where(Paper.citation_count >= min_citations)

            query = query.offset(offset).limit(limit)
            return list(session.exec(query).all())

    def delete(self, bibcode: str) -> bool:
        """Delete a paper by bibcode."""
        with self.db.get_session() as session:
            paper = session.get(Paper, bibcode)
            if paper:
                session.delete(paper)
                session.commit()
                return True
            return False

    def count(self) -> int:
        """Count total papers in database."""
        with self.db.get_session() as session:
            from sqlalchemy import func

            result = session.exec(select(func.count(Paper.bibcode)))
            return result.one()

    def exists(self, bibcode: str) -> bool:
        """Check if a paper exists."""
        return self.get(bibcode) is not None

    def search_by_title(self, query: str, limit: int = 10) -> list[Paper]:
        """Search papers by title (simple LIKE query)."""
        with self.db.get_session() as session:
            stmt = select(Paper).where(Paper.title.ilike(f"%{query}%")).limit(limit)
            return list(session.exec(stmt).all())

    def search_by_text(self, query: str, limit: int = 20) -> list[Paper]:
        """Search papers by title and abstract (simple LIKE query).

        Args:
            query: Search query string
            limit: Maximum number of results

        Returns:
            List of matching papers, sorted by citation count
        """
        from sqlalchemy import or_

        with self.db.get_session() as session:
            stmt = (
                select(Paper)
                .where(
                    or_(
                        Paper.title.ilike(f"%{query}%"),
                        Paper.abstract.ilike(f"%{query}%"),
                    )
                )
                .order_by(Paper.citation_count.desc())
                .limit(limit)
            )
            return list(session.exec(stmt).all())

    def delete_all(self) -> int:
        """Delete all papers from the database. Returns count of deleted papers."""
        with self.db.get_session() as session:
            # First delete all paper-project associations
            stmt = select(PaperProject)
            associations = session.exec(stmt).all()
            for assoc in associations:
                session.delete(assoc)

            # Then delete all citations
            from src.db.models import Citation
            citations = session.exec(select(Citation)).all()
            for citation in citations:
                session.delete(citation)

            # Finally delete all papers
            papers = session.exec(select(Paper)).all()
            count = len(papers)
            for paper in papers:
                session.delete(paper)

            session.commit()
            return count


class CitationRepository:
    """Repository for Citation CRUD operations."""

    def __init__(self, db: Optional[Database] = None):
        self.db = db or get_db()

    def add(self, citing_bibcode: str, cited_bibcode: str, context: Optional[str] = None) -> Citation:
        """Add a citation relationship."""
        with self.db.get_session() as session:
            # Check if exists
            stmt = select(Citation).where(
                Citation.citing_bibcode == citing_bibcode,
                Citation.cited_bibcode == cited_bibcode,
            )
            existing = session.exec(stmt).first()
            if existing:
                if context:
                    existing.context = context
                session.add(existing)
                session.commit()
                session.refresh(existing)
                return existing

            citation = Citation(
                citing_bibcode=citing_bibcode,
                cited_bibcode=cited_bibcode,
                context=context,
            )
            session.add(citation)
            session.commit()
            session.refresh(citation)
            return citation

    def get_references(self, bibcode: str) -> list[str]:
        """Get all papers that this paper cites."""
        with self.db.get_session() as session:
            stmt = select(Citation.cited_bibcode).where(Citation.citing_bibcode == bibcode)
            return list(session.exec(stmt).all())

    def get_citations(self, bibcode: str) -> list[str]:
        """Get all papers that cite this paper."""
        with self.db.get_session() as session:
            stmt = select(Citation.citing_bibcode).where(Citation.cited_bibcode == bibcode)
            return list(session.exec(stmt).all())

    def has_references(self, bibcode: str) -> bool:
        """Check if we have references for this paper."""
        with self.db.get_session() as session:
            stmt = select(Citation).where(Citation.citing_bibcode == bibcode).limit(1)
            return session.exec(stmt).first() is not None

    def has_citations(self, bibcode: str) -> bool:
        """Check if we have citations for this paper."""
        with self.db.get_session() as session:
            stmt = select(Citation).where(Citation.cited_bibcode == bibcode).limit(1)
            return session.exec(stmt).first() is not None


class ProjectRepository:
    """Repository for Project CRUD operations."""

    def __init__(self, db: Optional[Database] = None):
        self.db = db or get_db()

    def get_or_create_default(self) -> Project:
        """Get or create the default project."""
        default_name = settings.default_project
        project = self.get(default_name)
        if not project:
            project = self.create(default_name, description="Default project for papers without explicit project assignment")
        return project

    def create(self, name: str, description: Optional[str] = None) -> Project:
        """Create a new project."""
        with self.db.get_session() as session:
            project = Project(name=name, description=description)
            session.add(project)
            session.commit()
            session.refresh(project)
            return project

    def get(self, name: str) -> Optional[Project]:
        """Get a project by name."""
        with self.db.get_session() as session:
            return session.get(Project, name)

    def get_all(self) -> list[Project]:
        """Get all projects."""
        with self.db.get_session() as session:
            return list(session.exec(select(Project)).all())

    def add_paper(self, project_name: str, bibcode: str) -> PaperProject:
        """Add a paper to a project."""
        with self.db.get_session() as session:
            # Check if exists
            stmt = select(PaperProject).where(
                PaperProject.project_name == project_name,
                PaperProject.bibcode == bibcode,
            )
            existing = session.exec(stmt).first()
            if existing:
                return existing

            pp = PaperProject(project_name=project_name, bibcode=bibcode)
            session.add(pp)
            session.commit()
            session.refresh(pp)
            return pp

    def get_paper_projects(self, bibcode: str) -> list[str]:
        """Get all projects that contain a paper."""
        with self.db.get_session() as session:
            stmt = select(PaperProject.project_name).where(PaperProject.bibcode == bibcode)
            return list(session.exec(stmt).all())

    def paper_in_project(self, bibcode: str, project_name: str) -> bool:
        """Check if a paper is in a project."""
        with self.db.get_session() as session:
            stmt = select(PaperProject).where(
                PaperProject.project_name == project_name,
                PaperProject.bibcode == bibcode,
            )
            return session.exec(stmt).first() is not None

    def get_project_papers(self, project_name: str) -> list[str]:
        """Get all paper bibcodes in a project."""
        with self.db.get_session() as session:
            stmt = select(PaperProject.bibcode).where(PaperProject.project_name == project_name)
            return list(session.exec(stmt).all())

    def delete(self, name: str, delete_papers: bool = False) -> tuple[bool, int]:
        """Delete a project and optionally its papers.

        Args:
            name: Project name to delete
            delete_papers: If True, also delete papers that are ONLY in this project

        Returns:
            Tuple of (success, papers_deleted_count)
        """
        with self.db.get_session() as session:
            project = session.get(Project, name)
            if not project:
                return False, 0

            # Get papers in this project
            stmt = select(PaperProject).where(PaperProject.project_name == name)
            associations = list(session.exec(stmt).all())

            papers_deleted = 0

            if delete_papers:
                # Delete papers that are ONLY in this project
                for assoc in associations:
                    # Check if paper is in other projects
                    other_projects = select(PaperProject).where(
                        PaperProject.bibcode == assoc.bibcode,
                        PaperProject.project_name != name,
                    )
                    if not session.exec(other_projects).first():
                        # Paper is only in this project, delete it
                        paper = session.get(Paper, assoc.bibcode)
                        if paper:
                            # Delete citations involving this paper
                            from src.db.models import Citation
                            cites = session.exec(
                                select(Citation).where(
                                    (Citation.citing_bibcode == assoc.bibcode) |
                                    (Citation.cited_bibcode == assoc.bibcode)
                                )
                            ).all()
                            for cite in cites:
                                session.delete(cite)
                            session.delete(paper)
                            papers_deleted += 1

            # Delete all paper-project associations for this project
            for assoc in associations:
                session.delete(assoc)

            # Delete the project
            session.delete(project)
            session.commit()

            return True, papers_deleted


class ApiUsageRepository:
    """Repository for tracking API usage."""

    def __init__(self, db: Optional[Database] = None):
        self.db = db or get_db()

    def _get_today(self) -> str:
        return date.today().isoformat()

    def _get_or_create_today(self, session: Session) -> ApiUsage:
        """Get or create today's usage record."""
        today = self._get_today()
        usage = session.get(ApiUsage, today)
        if not usage:
            usage = ApiUsage(date=today)
            session.add(usage)
            session.commit()
            session.refresh(usage)
        return usage

    def increment_ads(self) -> int:
        """Increment ADS API call count and return new count."""
        with self.db.get_session() as session:
            usage = self._get_or_create_today(session)
            usage.ads_calls += 1
            session.add(usage)
            session.commit()
            return usage.ads_calls

    def get_ads_usage_today(self) -> int:
        """Get today's ADS API call count."""
        with self.db.get_session() as session:
            today = self._get_today()
            usage = session.get(ApiUsage, today)
            return usage.ads_calls if usage else 0

    def can_make_ads_call(self, limit: int = 5000, warn_threshold: int = 4500) -> tuple[bool, bool]:
        """Check if we can make an ADS call. Returns (can_call, is_warning)."""
        current = self.get_ads_usage_today()
        return (current < limit, current >= warn_threshold)

    def increment_openai(self) -> int:
        """Increment OpenAI API call count and return new count."""
        with self.db.get_session() as session:
            usage = self._get_or_create_today(session)
            usage.openai_calls += 1
            session.add(usage)
            session.commit()
            return usage.openai_calls

    def increment_anthropic(self) -> int:
        """Increment Anthropic API call count and return new count."""
        with self.db.get_session() as session:
            usage = self._get_or_create_today(session)
            usage.anthropic_calls += 1
            session.add(usage)
            session.commit()
            return usage.anthropic_calls

    def get_openai_usage_today(self) -> int:
        """Get today's OpenAI API call count."""
        with self.db.get_session() as session:
            today = self._get_today()
            usage = session.get(ApiUsage, today)
            return usage.openai_calls if usage else 0

    def get_anthropic_usage_today(self) -> int:
        """Get today's Anthropic API call count."""
        with self.db.get_session() as session:
            today = self._get_today()
            usage = session.get(ApiUsage, today)
            return usage.anthropic_calls if usage else 0
