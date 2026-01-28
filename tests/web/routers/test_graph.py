"""Tests for graph router."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from src.web.main import app
from src.db.repository import CitationRepository, PaperRepository
from src.db.models import Paper
from src.web.dependencies import get_citation_repo, get_paper_repo

client = TestClient(app)

@pytest.fixture
def mock_paper_repo():
    repo = MagicMock(spec=PaperRepository)
    
    # Setup some dummy papers
    p1 = Paper(bibcode="p1", title="Paper 1", authors="Author A; Author B", year=2024, citation_count=10)
    p2 = Paper(bibcode="p2", title="Paper 2", authors="Author C", year=2023, citation_count=5)
    p3 = Paper(bibcode="p3", title="Paper 3", authors="Author D", year=2022, citation_count=20)
    
    repo.get.side_effect = lambda b: {
        "p1": p1,
        "p2": p2,
        "p3": p3,
    }.get(b)
    
    return repo

@pytest.fixture
def mock_citation_repo():
    repo = MagicMock(spec=CitationRepository)
    # p1 cites p2 (reference)
    # p3 cites p1 (citation)
    repo.get_references.return_value = ["p2"]
    repo.get_citations.return_value = ["p3"]
    return repo

def test_get_graph(mock_paper_repo, mock_citation_repo):
    app.dependency_overrides[get_paper_repo] = lambda: mock_paper_repo
    app.dependency_overrides[get_citation_repo] = lambda: mock_citation_repo
    
    response = client.get("/api/graph/p1")
    assert response.status_code == 200
    data = response.json()
    
    # Expect 3 nodes: p1 (central), p2 (ref), p3 (citing)
    nodes = data["nodes"]
    assert len(nodes) == 3
    
    node_ids = {n["id"] for n in nodes}
    assert "p1" in node_ids
    assert "p2" in node_ids
    assert "p3" in node_ids
    
    # Check groups
    p1_node = next(n for n in nodes if n["id"] == "p1")
    assert p1_node["group"] == "central"
    
    p2_node = next(n for n in nodes if n["id"] == "p2")
    assert p2_node["group"] in ["library", "me"] # Depends on is_my_paper default, assumed False
    
    # Expect 2 edges
    edges = data["edges"]
    assert len(edges) == 2
    
    # p1 -> p2 (reference)
    assert any(e["from"] == "p1" and e["to"] == "p2" for e in edges)
    # p3 -> p1 (citation)
    assert any(e["from"] == "p3" and e["to"] == "p1" for e in edges)

def test_expand_graph(mock_paper_repo, mock_citation_repo):
    app.dependency_overrides[get_paper_repo] = lambda: mock_paper_repo
    app.dependency_overrides[get_citation_repo] = lambda: mock_citation_repo
    
    # Expand p1
    response = client.post("/api/graph/expand", json={"bibcodes": ["p1"]})
    assert response.status_code == 200
    data = response.json()
    
    nodes = data["nodes"]
    assert len(nodes) == 3
    
    edges = data["edges"]
    assert len(edges) == 2
    
