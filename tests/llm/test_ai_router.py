
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient
from src.web.main import app
from src.web.dependencies import (
    get_paper_repo, get_ads_client, get_llm_client, get_vector_store_dep
)
from src.core.llm_client import ContextAnalysis, CitationType, RankedPaper
from src.db.models import Paper

@pytest.fixture
def mock_deps():
    mock_paper_repo = MagicMock()
    mock_ads = MagicMock()
    mock_llm = MagicMock()
    mock_vector = MagicMock()
    
    app.dependency_overrides[get_paper_repo] = lambda: mock_paper_repo
    app.dependency_overrides[get_ads_client] = lambda: mock_ads
    app.dependency_overrides[get_llm_client] = lambda: mock_llm
    app.dependency_overrides[get_vector_store_dep] = lambda: mock_vector
    
    yield {
        "paper_repo": mock_paper_repo,
        "ads": mock_ads,
        "llm": mock_llm,
        "vector": mock_vector
    }
    
    app.dependency_overrides.clear()

@pytest.fixture
def client(mock_deps):
    return TestClient(app)

def test_ai_search_stream_basic(client, mock_deps):
    # Setup mocks
    mock_deps["llm"].analyze_context.return_value = ContextAnalysis(
        topic="Test", claim="Test", citation_type=CitationType.GENERAL,
        keywords=["k1"], search_query="k1", reasoning=""
    )
    
    # Mock vector search
    mock_deps["vector"].search.return_value = []
    
    # Mock ADS search
    mock_deps["ads"].search.return_value = []
    
    # Mock PDF search
    mock_deps["vector"].search_pdf.return_value = []
    
    # Perform Request
    with client.stream(
        "POST", 
        "/api/ai/search/stream",
        json={"query": "test query", "use_llm": True}
    ) as response:
        assert response.status_code == 200
        
        # Collect events
        events = []
        for line in response.iter_lines():
            if line:
                events.append(line)
        
        # Verify flow
        assert len(events) > 0
        # Should see progress, analysis, and result type events
        # Events are strings
        assert any('"type": "analysis"' in e for e in events)
        assert any('"type": "result"' in e for e in events)

def test_ai_search_with_results(client, mock_deps):
    # Setup results to verify flow
    mock_deps["llm"].analyze_context.return_value = ContextAnalysis(
        topic="Topic", claim="Claim", citation_type=CitationType.GENERAL,
        keywords=[], search_query="", reasoning=""
    )
    
    # Vector Search Result
    mock_deps["vector"].search.return_value = [{
        "bibcode": "p1", "distance": 0.1, "metadata": {}, "document": ""
    }]
    
    # Repo return for result
    paper = Paper(bibcode="p1", title="Paper 1", abstract="Abs", citation_count=10)
    mock_deps["paper_repo"].get_batch.return_value = [paper]
    
    # LLM Ranking
    ranked_paper = RankedPaper(
        paper=paper, relevance_score=0.95, 
        relevance_explanation="Exp", citation_type=CitationType.GENERAL
    )
    mock_deps["llm"].rank_papers.return_value = [ranked_paper]

    with client.stream(
        "POST", 
        "/api/ai/search/stream",
        json={"query": "test", "search_library": True, "search_ads": False}
    ) as response:
        assert response.status_code == 200
        
        content = "".join(response.iter_lines())
        
        # Verify result content
        assert '"bibcode": "p1"' in content
        assert '"relevance_score": 0.95' in content

def test_ask_paper_success(client, mock_deps):
    # Setup
    paper = Paper(bibcode="p1", title="Title", abstract="Abstract", pdf_embedded=True)
    mock_deps["paper_repo"].get.return_value = paper
    
    mock_deps["vector"].search_pdf.return_value = [
        {"document": "Relevant context from PDF"}
    ]
    
    # Mock LLM call using private method as used in router
    mock_deps["llm"]._call_llm.return_value = "The answer is X."
    
    response = client.post("/api/ai/ask", json={
        "bibcode": "p1",
        "question": "What is X?"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "The answer is X."
    assert "pdf" in data["sources_used"]
    assert "abstract" in data["sources_used"]

def test_ask_paper_not_found(client, mock_deps):
    mock_deps["paper_repo"].get.return_value = None
    
    response = client.post("/api/ai/ask", json={
        "bibcode": "unknown",
        "question": "Q"
    })
    
    assert response.status_code == 404
