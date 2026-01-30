"""Database repository for CRUD operations."""

import json
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from sqlmodel import Session, SQLModel, create_engine, select

from src.core.config import settings, ensure_data_dirs
from src.db.models import ApiUsage, Citation, Note, Paper, PaperProject, Project, Search


class Database:
    """Database connection and operations manager."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or settings.db_path
        ensure_data_dirs()

        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            echo=False,
            connect_args={"check_same_thread": False},
            pool_size=20,
            max_overflow=40,
        )

    def create_tables(self):
        """Create all database tables."""
        SQLModel.metadata.create_all(self.engine)
        self._migrate_tables()

    def _migrate_tables(self):
        """Perform manual migrations for schema updates."""
        # Check ApiUsage table for new columns
        from sqlalchemy import text
        with self.engine.connect() as conn:
            try:
                # Check if gemini_calls column exists
                # SQLite PRAGMA table_info returns (cid, name, type, notnull, dflt_value, pk)
                columns = conn.execute(text("PRAGMA table_info(api_usage)")).fetchall()
                col_names = [c[1] for c in columns]
                
                if "gemini_calls" not in col_names:
                    print("Migrating: Adding gemini_calls to api_usage")
                    conn.execute(text("ALTER TABLE api_usage ADD COLUMN gemini_calls INTEGER DEFAULT 0 NOT NULL"))
                    
                if "ollama_calls" not in col_names:
                    print("Migrating: Adding ollama_calls to api_usage")
                    conn.execute(text("ALTER TABLE api_usage ADD COLUMN ollama_calls INTEGER DEFAULT 0 NOT NULL"))
                    
                conn.commit()
            except Exception as e:
                print(f"Migration warning: {e}")

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

        note_content = None

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

            # Fetch note content inside session if needed
            if should_embed:
                from src.db.models import Note
                stmt = select(Note).where(Note.bibcode == result.bibcode)
                note = session.exec(stmt).first()
                if note:
                    note_content = note.content

        # Embed in vector store if requested
        if should_embed:
            try:
                self.vector_store.embed_paper(result, note_content=note_content)
            except Exception as e:
                # Don't fail the add if embedding fails
                import logging
                logging.error(f"Failed to embed paper {result.bibcode}: {e}", exc_info=True)
                print(f"Warning: Failed to embed paper {result.bibcode}: {e}")

        return result

    def get(self, bibcode: str) -> Optional[Paper]:
        """Get a paper by bibcode."""
        with self.db.get_session() as session:
            return session.get(Paper, bibcode)

    def get_batch(self, bibcodes: list[str]) -> list[Paper]:
        """Get multiple papers by bibcodes.

        Args:
            bibcodes: List of bibcodes to fetch

        Returns:
            List of found papers
        """
        if not bibcodes:
            return []
            
        with self.db.get_session() as session:
            stmt = select(Paper).where(Paper.bibcode.in_(bibcodes))
            return list(session.exec(stmt).all())

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
        """Delete a paper and all associated data by bibcode.
        
        Removes:
        - Paper record
        - PDF file from filesystem
        - Vector embeddings (abstract, PDF, note)
        - Citations (in/out)
        - Project associations
        - Note record
        """
        with self.db.get_session() as session:
            paper = session.get(Paper, bibcode)
            if not paper:
                return False

            # 1. Delete PDF file
            if paper.pdf_path and Path(paper.pdf_path).exists():
                try:
                    Path(paper.pdf_path).unlink()
                except Exception as e:
                    print(f"Error deleting PDF file: {e}")

            # 2. Delete Vector Embeddings
            try:
                # Delete abstract embedding
                self.vector_store.delete_paper(bibcode)
                # Delete PDF chunks
                self.vector_store.delete_pdf(bibcode)
                # Delete Note embedding
                self.vector_store.delete_note(bibcode)
            except Exception as e:
                print(f"Error deleting embeddings: {e}")

            # 3. Delete Note
            from src.db.models import Note
            stmt = select(Note).where(Note.bibcode == bibcode)
            note = session.exec(stmt).first()
            if note:
                session.delete(note)

            # 4. Delete Citations
            from src.db.models import Citation
            citations = session.exec(
                select(Citation).where(
                    (Citation.citing_bibcode == bibcode) | 
                    (Citation.cited_bibcode == bibcode)
                )
            ).all()
            for citation in citations:
                session.delete(citation)

            # 5. Delete Project Associations
            from src.db.models import PaperProject
            projects = session.exec(
                select(PaperProject).where(PaperProject.bibcode == bibcode)
            ).all()
            for proj in projects:
                session.delete(proj)

            # 6. Delete Paper
            session.delete(paper)
            session.commit()
            return True

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

    def set_my_paper(self, bibcode: str, is_my_paper: bool) -> bool:
        """Set whether a paper is marked as the user's paper.

        Args:
            bibcode: Paper bibcode
            is_my_paper: Whether this is the user's paper

        Returns:
            True if updated, False if paper not found
        """
        with self.db.get_session() as session:
            paper = session.get(Paper, bibcode)
            if paper:
                paper.is_my_paper = is_my_paper
                paper.updated_at = datetime.utcnow()
                session.add(paper)
                session.commit()
                
                # Re-embed if updated
                try:
                     self.vector_store.embed_paper(paper)
                except:
                     pass
                     
                return True
            return False

    def get_my_papers(self, limit: int = 100) -> list[Paper]:
        """Get all papers marked as the user's papers.

        Returns:
            List of papers where is_my_paper is True
        """
        with self.db.get_session() as session:
            stmt = (
                select(Paper)
                .where(Paper.is_my_paper == True)
                .order_by(Paper.year.desc())
                .limit(limit)
            )
            return list(session.exec(stmt).all())

    def delete_all(self) -> int:
        """Delete all papers from the database. Returns count of deleted papers."""
        with self.db.get_session() as session:
            # 1. Clean up PDFs first
            papers = session.exec(select(Paper)).all()
            for paper in papers:
                if paper.pdf_path and Path(paper.pdf_path).exists():
                    try:
                        Path(paper.pdf_path).unlink()
                    except Exception as e:
                        print(f"Error deleting PDF file {paper.pdf_path}: {e}")

            # 2. Clear Vector Store
            try:
                self.vector_store.clear()          # abstracts
                self.vector_store.clear_pdfs()     # PDF chunks
                self.vector_store.clear_notes()    # notes
            except Exception as e:
                print(f"Error clearing vector store: {e}")

            # 3. Clean up database records
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

            # Delete all notes
            from src.db.models import Note
            notes = session.exec(select(Note)).all()
            for note in notes:
                session.delete(note)

            # Finally delete all papers
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

    def delete_all(self) -> int:
        """Delete all projects.
        
        Returns:
            Number of projects deleted
        """
        with self.db.get_session() as session:
            # Delete all paper-project associations first
            from src.db.models import PaperProject
            session.exec(select(PaperProject)).all()
            # Actually sqlmodel/sqlalchemy might not support delete directly on select without synchronize_session
            # But we can just iterate and delete
            associations = session.exec(select(PaperProject)).all()
            for assoc in associations:
                session.delete(assoc)
            
            # Delete all projects
            projects = session.exec(select(Project)).all()
            count = len(projects)
            for project in projects:
                session.delete(project)
            
            session.commit()
            return count


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

    def increment_gemini(self) -> int:
        """Increment Gemini API call count and return new count."""
        with self.db.get_session() as session:
            usage = self._get_or_create_today(session)
            usage.gemini_calls += 1
            session.add(usage)
            session.commit()
            return usage.gemini_calls

    def get_gemini_usage_today(self) -> int:
        """Get today's Gemini API call count."""
        with self.db.get_session() as session:
            today = self._get_today()
            usage = session.get(ApiUsage, today)
            return usage.gemini_calls if usage else 0

    def increment_ollama(self) -> int:
        """Increment Ollama API call count and return new count."""
        with self.db.get_session() as session:
            usage = self._get_or_create_today(session)
            usage.ollama_calls += 1
            session.add(usage)
            session.commit()
            return usage.ollama_calls

    def get_ollama_usage_today(self) -> int:
        """Get today's Ollama API call count."""
        with self.db.get_session() as session:
            today = self._get_today()
            usage = session.get(ApiUsage, today)
            return usage.ollama_calls if usage else 0


class NoteRepository:
    """Repository for Note CRUD operations."""

    def __init__(self, db: Optional[Database] = None, auto_embed: bool = True):
        """Initialize the note repository.

        Args:
            db: Database instance (uses global if not provided)
            auto_embed: Whether to automatically embed notes in vector store
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

    def add(self, bibcode: str, content: str, embed: Optional[bool] = None) -> Note:
        """Add or append a note to a paper.

        If a note already exists for this paper, appends the content.

        Args:
            bibcode: Paper bibcode
            content: Note content to add
            embed: Whether to embed in vector store (defaults to self.auto_embed)

        Returns:
            The added/updated note
        """
        should_embed = embed if embed is not None else self.auto_embed

        paper_to_embed = None

        with self.db.get_session() as session:
            # Check if note exists for this paper
            stmt = select(Note).where(Note.bibcode == bibcode)
            existing = session.exec(stmt).first()

            if existing:
                # Append to existing note
                existing.content = existing.content + "\n\n" + content
                existing.updated_at = datetime.utcnow()
                session.add(existing)
                session.commit()
                session.refresh(existing)
                result = existing
            else:
                # Create new note
                note = Note(bibcode=bibcode, content=content)
                session.add(note)
                session.commit()
                session.refresh(note)
                result = note

            # Fetch paper inside session if needed
            if should_embed:
                stmt_paper = select(Paper).where(Paper.bibcode == bibcode)
                paper_to_embed = session.exec(stmt_paper).first()
                # Trigger a load of attributes if needed, though simple selection usually suffices
                if paper_to_embed:
                    _ = paper_to_embed.title

        # Embed in vector store if requested
        if should_embed:
            try:
                if paper_to_embed:
                    # Re-embed paper with new note content
                    self.vector_store.embed_paper(paper_to_embed, note_content=result.content)
                
                # Also index note separately if needed (legacy or specific note search)
                self.vector_store.embed_note(result)
            except Exception as e:
                import traceback
                print(f"Warning: Failed to embed note/paper for {bibcode}: {e}")
                print(traceback.format_exc())

        return result

    def get(self, bibcode: str) -> Optional[Note]:
        """Get note for a paper by bibcode."""
        with self.db.get_session() as session:
            stmt = select(Note).where(Note.bibcode == bibcode)
            return session.exec(stmt).first()

    def get_batch(self, bibcodes: list[str]) -> list[Note]:
        """Get notes for multiple papers.

        Args:
            bibcodes: List of bibcodes to fetch notes for

        Returns:
            List of found notes
        """
        if not bibcodes:
            return []

        with self.db.get_session() as session:
            stmt = select(Note).where(Note.bibcode.in_(bibcodes))
            return list(session.exec(stmt).all())

    def get_by_id(self, note_id: int) -> Optional[Note]:
        """Get note by ID."""
        with self.db.get_session() as session:
            return session.get(Note, note_id)

    def get_all(self, limit: int = 100) -> list[Note]:
        """Get all notes."""
        with self.db.get_session() as session:
            stmt = select(Note).limit(limit)
            return list(session.exec(stmt).all())

    def delete(self, bibcode: str) -> bool:
        """Delete note for a paper by bibcode.

        Args:
            bibcode: Paper bibcode

        Returns:
            True if deleted, False if not found
        """
        paper_to_reembed = None
        
        with self.db.get_session() as session:
            stmt = select(Note).where(Note.bibcode == bibcode)
            note = session.exec(stmt).first()
            if note:
                # Delete from vector store first
                try:
                    self.vector_store.delete_note(bibcode)
                except Exception:
                    pass  # Continue even if vector store delete fails

                session.delete(note)
                session.commit()
                
                # Fetch paper inside session
                try:
                    stmt = select(Paper).where(Paper.bibcode == bibcode)
                    paper_to_reembed = session.exec(stmt).first()
                    if paper_to_reembed:
                         _ = paper_to_reembed.title
                except:
                    pass
            else:
                 return False

        # Re-embed paper without note (outside session)
        if paper_to_reembed:
            try:
                self.vector_store.embed_paper(paper_to_reembed, note_content=None)
            except:
                pass
        
        return True

    def count(self) -> int:
        """Count total notes in database."""
        with self.db.get_session() as session:
            from sqlalchemy import func
            result = session.exec(select(func.count(Note.id)))
            return result.one()

    def search_by_text(self, query: str, limit: int = 20) -> list[Note]:
        """Search notes by content (simple LIKE query).

        Args:
            query: Search query string
            limit: Maximum number of results

        Returns:
            List of matching notes
        """
        with self.db.get_session() as session:
            stmt = (
                select(Note)
                .where(Note.content.ilike(f"%{query}%"))
                .limit(limit)
            )
            return list(session.exec(stmt).all())
