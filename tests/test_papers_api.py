import pytest
from src.db.models import Paper
from unittest.mock import MagicMock
from src.web.main import app
from src.web.dependencies import get_pdf_handler

def test_list_papers_empty(client):
    """Test listing papers when DB is empty."""
    response = client.get("/api/papers/")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["papers"] == []

def test_list_papers_with_data(client, sample_paper):
    """Test listing papers with data."""
    response = client.get("/api/papers/")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["papers"][0]["bibcode"] == sample_paper.bibcode
    assert data["papers"][0]["title"] == sample_paper.title

def test_get_paper_detail(client, sample_paper):
    """Test getting a single paper."""
    response = client.get(f"/api/papers/{sample_paper.bibcode}")
    assert response.status_code == 200
    data = response.json()
    assert data["bibcode"] == sample_paper.bibcode

def test_get_paper_not_found(client):
    """Test getting a non-existent paper."""
    response = client.get("/api/papers/NONEXISTENT")
    assert response.status_code == 404

def test_toggle_my_paper(client, sample_paper):
    """Test toggling 'my paper' status."""
    assert not sample_paper.is_my_paper
    
    # Mark as mine
    response = client.patch(
        f"/api/papers/{sample_paper.bibcode}/mine", 
        json={"is_my_paper": True}
    )
    assert response.status_code == 200
    
    # Verify via API
    response = client.get(f"/api/papers/{sample_paper.bibcode}")
    assert response.json()["is_my_paper"] is True

def test_delete_paper(client, sample_paper):
    """Test deleting a paper."""
    response = client.delete(f"/api/papers/{sample_paper.bibcode}")
    assert response.status_code == 200
    
    # Verify deleted
    response = client.get(f"/api/papers/{sample_paper.bibcode}")
    assert response.status_code == 404

def test_citations_endpoint_empty(client, sample_paper):
    """Test citations endpoint returns empty list by default."""
    response = client.get(f"/api/citations/{sample_paper.bibcode}/citations")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["citations"] == []

def test_references_endpoint_empty(client, sample_paper):
    """Test references endpoint returns empty list by default."""
    response = client.get(f"/api/citations/{sample_paper.bibcode}/references")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["references"] == []

def test_download_pdf_updates_db(client, session, sample_paper):
    """Test that downloading a PDF updates the database with the file path."""
    
    # 1. Arrange: Ensure paper has no PDF path
    sample_paper.pdf_path = None
    session.add(sample_paper)
    session.commit()
    session.refresh(sample_paper)
    
    # 2. Act: Call download endpoint with mocked handler
    mock_handler = MagicMock()
    mock_handler.download.return_value = "/tmp/mock_paper_from_test.pdf"
    
    app.dependency_overrides[get_pdf_handler] = lambda: mock_handler
    
    try:
        response = client.post(f"/api/pdf/{sample_paper.bibcode}/download")
    finally:
        del app.dependency_overrides[get_pdf_handler]
        
    assert response.status_code == 200
    data = response.json()
    assert "downloaded successfully" in data["message"]
    
    # 3. Assert: Verify DB update
    # We need to refresh the object from the session or query it again
    session.refresh(sample_paper)
    assert sample_paper.pdf_path == "/tmp/mock_paper_from_test.pdf"
