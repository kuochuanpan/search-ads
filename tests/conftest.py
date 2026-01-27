import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from src.web.main import app
from src.db.repository import get_db, Database, PaperRepository, NoteRepository, ProjectRepository
from src.web.dependencies import (
    get_paper_repo,
    get_note_repo,
    get_project_repo,
    get_ads_client,
    get_llm_client,
    get_vector_store_dep,
    get_citation_repo,
)
from src.db.models import Paper

# --- Database Fixtures ---

@pytest.fixture(name="session")
def session_fixture():
    """Create an in-memory database session for testing."""
    engine = create_engine(
        "sqlite://", 
        connect_args={"check_same_thread": False}, 
        poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

@pytest.fixture(name="client")
def client_fixture(session: Session):
    """Create a TestClient with overridden dependencies."""
    
    # Mock Repository Providers
    def get_session_override():
        return session

    # We need to patch the repository getters or the repositories themselves.
    # Ideally, we inject a repository that uses our test session.
    
    # Since the app uses `get_paper_repo` which instantiates `PaperRepository(get_db())`,
    # we need to override `get_paper_repo`.
    
    # Create a mock DB wrapper that returns our test session
    mock_db = MagicMock(spec=Database)
    mock_db.get_session.return_value.__enter__.return_value = session
    
    def get_paper_repo_override():
        return PaperRepository(db=mock_db, auto_embed=False)

    def get_note_repo_override():
        return NoteRepository(db=mock_db, auto_embed=False)
        
    def get_project_repo_override():
        return ProjectRepository(db=mock_db)

    def get_citation_repo_override():
        # Import here to avoid circular dependencies if any
        from src.db.repository import CitationRepository
        return CitationRepository(db=mock_db)

    # Mock External Clients
    mock_ads = MagicMock()
    mock_llm = MagicMock()
    mock_vector = MagicMock()

    app.dependency_overrides[get_paper_repo] = get_paper_repo_override
    app.dependency_overrides[get_note_repo] = get_note_repo_override
    app.dependency_overrides[get_project_repo] = get_project_repo_override
    app.dependency_overrides[get_citation_repo] = get_citation_repo_override
    app.dependency_overrides[get_ads_client] = lambda: mock_ads
    app.dependency_overrides[get_llm_client] = lambda: mock_llm
    app.dependency_overrides[get_vector_store_dep] = lambda: mock_vector

    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

# --- Mock Data Fixtures ---

@pytest.fixture
def mock_ads_client(client):
    """Accces to the mocked ADS client."""
    return app.dependency_overrides[get_ads_client]()

@pytest.fixture
def mock_llm_client(client):
    """Access to the mocked LLM client."""
    return app.dependency_overrides[get_llm_client]()

@pytest.fixture
def mock_vector_store(client):
    """Access to the mocked Vector Store."""
    return app.dependency_overrides[get_vector_store_dep]()

@pytest.fixture
def sample_paper(session):
    """Create a sample paper in the DB."""
    paper = Paper(
        bibcode="2024Test...123A",
        title="Test Paper Title",
        authors='["Author, A.", "Author, B."]',
        year=2024,
        citation_count=10,
        abstract="This is a test abstract.",
        pdf_path="/tmp/test.pdf",
        is_my_paper=False
    )
    session.add(paper)
    session.commit()
    return paper
