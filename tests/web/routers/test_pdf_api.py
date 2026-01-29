from fastapi.testclient import TestClient
from sqlmodel import Session
from src.db.models import Paper

def test_delete_pdf_embedding_success(client: TestClient, session: Session, mock_vector_store):
    # Setup: Create a paper with embedded PDF
    bibcode = "2024Pdf...123P"
    paper = Paper(
        bibcode=bibcode,
        title="PDF Paper",
        year=2024,
        pdf_path="/tmp/test.pdf",
        pdf_embedded=True
    )
    session.add(paper)
    session.commit()

    # Action: Delete embedding
    response = client.delete(f"/api/pdf/{bibcode}/embed")

    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "PDF embedding removed successfully"

    # Verify vector store called
    mock_vector_store.delete_pdf.assert_called_once_with(bibcode)

    # Verify DB update
    session.refresh(paper)
    assert paper.pdf_embedded is False


from unittest.mock import MagicMock
from src.web.main import app
from src.web.dependencies import get_pdf_handler

def test_embed_pdf_success(client: TestClient, session: Session, mock_vector_store):
    # Setup: Create a paper with PDF path but not embedded
    bibcode = "2024Embed...789Y"
    paper = Paper(
        bibcode=bibcode,
        title="To Embed Paper",
        year=2024,
        pdf_path="/tmp/test.pdf",
        pdf_embedded=False
    )
    session.add(paper)
    session.commit()

    # Mock PDF Handler
    mock_pdf_handler = MagicMock()
    mock_pdf_handler.parse.return_value = "Extracted text content"
    
    # Override dependency
    app.dependency_overrides[get_pdf_handler] = lambda: mock_pdf_handler

    try:
        # Action: Embed PDF
        response = client.post(f"/api/pdf/{bibcode}/embed")

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "PDF embedded successfully"

        # Verify vector store called
        mock_vector_store.embed_pdf.assert_called_once()
        args, _ = mock_vector_store.embed_pdf.call_args
        assert args[0] == bibcode
        assert args[1] == "Extracted text content"

        # Verify DB update
        session.refresh(paper)
        assert paper.pdf_embedded is True
        
    finally:
        # cleanup
        del app.dependency_overrides[get_pdf_handler]


def test_delete_pdf_embedding_not_embedded(client: TestClient, session: Session, mock_vector_store):
    # Setup: Create a paper NOT embedded
    bibcode = "2024NoEmb...456X"
    paper = Paper(
        bibcode=bibcode,
        title="Unembedded Paper",
        year=2024,
        pdf_path="/tmp/test.pdf",
        pdf_embedded=False
    )
    session.add(paper)
    session.commit()

    # Action: Delete embedding
    response = client.delete(f"/api/pdf/{bibcode}/embed")

    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "PDF is not embedded"

    # Verify vector store NOT called
    mock_vector_store.delete_pdf.assert_not_called()

    # Verify DB state unchanged
    session.refresh(paper)
    assert paper.pdf_embedded is False


def test_delete_pdf_embedding_paper_not_found(client: TestClient):
    # Action: Delete embedding for non-existent paper
    response = client.delete("/api/pdf/NONEXISTENT/embed")

    # Verify response
    assert response.status_code == 404
    assert "Paper not found" in response.json()["detail"]
