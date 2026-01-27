import pytest
from unittest.mock import MagicMock

def test_search_local(client, sample_paper):
    """Test local keyword search."""
    # Search by title word
    response = client.post("/api/search/local", json={"query": "Test"})
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) >= 1
    assert data["results"][0]["bibcode"] == sample_paper.bibcode

def test_search_ads_mock(client, mock_ads_client):
    """Test ADS search with mocked client."""
    # Setup mock return
    mock_paper = MagicMock()
    mock_paper.bibcode = "2024ADS...Mock"
    mock_paper.title = "ADS Mock Paper"
    mock_paper.year = 2024
    mock_paper.first_author = "Mock, A."
    mock_paper.citation_count = 5
    mock_paper.abstract = "Abstract"
    
    mock_ads_client.search.return_value = [mock_paper]

    response = client.post("/api/search/ads", json={"query": "dark matter"})
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 1
    assert data["results"][0]["bibcode"] == "2024ADS...Mock"

def test_ai_search_integration(client, mock_llm_client, mock_vector_store, mock_ads_client):
    """Test the AI search orchestration."""
    # Mock LLM analysis
    mock_analysis = MagicMock()
    mock_analysis.topic = "Dark Matter"
    mock_analysis.claim = "Halos exist"
    mock_analysis.citation_type.value = "foundational"
    mock_analysis.keywords = ["dark matter", "halo"]
    mock_analysis.reasoning = "Because"
    mock_llm_client.analyze_context.return_value = mock_analysis

    # Mock Vector Store results
    # Returns list of (bibcode, distance, metadata, document)
    mock_vector_store.search.return_value = []

    # Mock ADS results
    mock_ads_client.search.return_value = []

    # Call AI search
    response = client.post("/api/ai/search", json={
        "query": "find papers about dark matter",
        "use_llm": True
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["ai_analysis"]["topic"] == "Dark Matter"
    # Even with empty results, structure should be valid
    assert "results" in data
