import pytest
from unittest.mock import MagicMock

def test_parse_latex_empty_citations(client):
    """Test searching for empty citations."""
    latex = r"This is a test \cite{} and \cite{}. And \citep{}."
    response = client.post("/api/latex/parse", json={"latex_text": latex})
    
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 3
    assert data["empty_citations"][0]["cite_type"] == "cite"

def test_suggest_citations_mock(client, mock_llm_client, mock_vector_store, session):
    """Test suggestion endpoint with mocked LLM."""
    
    # Mock LLM analysis
    mock_analysis = MagicMock()
    mock_analysis.topic = "Test Topic"
    mock_analysis.claim = "Test Claim"
    mock_analysis.citation_type.value = "general"
    mock_analysis.keywords = ["test"]
    mock_analysis.reasoning = "Test Reasoning"
    mock_llm_client.analyze_context.return_value = mock_analysis

    # Mock ranking (returns list of RankedPaper or similar)
    mock_ranked = MagicMock()
    mock_ranked.paper.bibcode = "2024Test"
    mock_ranked.paper.title = "Ranked Paper"
    mock_ranked.relevance_score = 0.9
    mock_ranked.citation_type.value = "general"
    mock_ranked.relevance_explanation = "Reason"
    
    mock_ranked.paper.bibcode = "2024Test"
    mock_ranked.paper.title = "Ranked Paper"
    mock_ranked.paper.year = 2024
    mock_ranked.paper.abstract = "Abstract"
    mock_ranked.paper.first_author = "Author A"
    mock_ranked.paper.citation_count = 5
    mock_ranked.paper.bibtex = "@bibtex"
    mock_ranked.paper.bibitem_aastex = "\\bibitem"
    mock_ranked.paper.authors = '["Author A"]'
    
    mock_llm_client.rank_papers.return_value = [mock_ranked]

    # Create paper in DB so repo finds it
    from src.db.models import Paper
    paper = Paper(
        bibcode="2024Test",
        title="Ranked Paper",
        year=2024,
        abstract="Abstract",
        authors='["Author A"]',
    )
    session.add(paper)
    session.commit()
    
    # Mock Vector Store to return this paper
    # search return format: list of dicts
    mock_vector_store.search.return_value = [
        {"bibcode": "2024Test", "distance": 0.1, "metadata": {}, "document": "doc"}
    ]
    
    latex = r"Context here \cite{}"
    response = client.post("/api/latex/suggest", json={
        "latex_text": latex,
        "use_library": True,
        "use_ads": False
    })

    assert response.status_code == 200
    data = response.json()
    assert len(data["suggestions"]) == 1
    assert data["suggestions"][0]["suggestions"][0]["bibcode"] == "2024Test"
