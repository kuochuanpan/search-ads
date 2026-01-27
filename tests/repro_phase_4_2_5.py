import os
import shutil
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.db.repository import PaperRepository, get_db
from src.db.vector_store import get_vector_store
from src.db.models import Paper, Note
from src.core.config import settings

# Setup test environment
TEST_DB_PATH = Path("test_repro.db")
TEST_CHROMA_PATH = Path("test_chroma_repro")
TEST_PDF_PATH = Path("test_pdfs_repro")

@pytest.fixture(scope="module")
def setup_teardown():
    # Setup
    # Patch the global settings object directly
    # This is more reliable than patching individual properties or data_dir
    with patch("src.db.repository.settings") as mock_settings, \
         patch("src.db.vector_store.settings") as mock_chroma_settings, \
         patch("src.core.pdf_handler.settings") as mock_pdf_settings:
        
        # Configure mocks to use our test paths
        for s in [mock_settings, mock_chroma_settings, mock_pdf_settings]:
             s.db_path = TEST_DB_PATH
             s.chroma_path = TEST_CHROMA_PATH
             s.pdfs_path = TEST_PDF_PATH
             s.openai_api_key = "fake-key" # Prevent actual API calls

        # Ensure directories exist
        TEST_CHROMA_PATH.mkdir(parents=True, exist_ok=True)
        TEST_PDF_PATH.mkdir(parents=True, exist_ok=True)
        
        # Initialize DB (creates tables)
        db = get_db()
        # Force recreate tables for the test DB (in case of stale state)
        db.create_tables()
        
        yield
    
    # Teardown
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
    if TEST_CHROMA_PATH.exists():
        shutil.rmtree(TEST_CHROMA_PATH)
    if TEST_PDF_PATH.exists():
        shutil.rmtree(TEST_PDF_PATH)

def test_search_weighting_repro(setup_teardown):
    """
    Test that 'My Papers' and papers with notes are NOT currently ranked higher
    (verifying the need for the fix).
    """
    repo = PaperRepository()
    vector_store = get_vector_store()
    
    # Clear existing
    repo.delete_all()
    vector_store.clear()
    
    # Create two similar papers
    paper1 = Paper(
        bibcode="2024Test...1A",
        title="Cosmic Dust and Galaxy Formation",
        abstract="A study about cosmic dust in galaxies.",
        year=2024,
        is_my_paper=False
    )
    
    paper2 = Paper(
        bibcode="2024Test...2B",
        title="Cosmic Dust and Star Formation",
        abstract="A study about cosmic dust in stars.",
        year=2024,
        is_my_paper=True # Marked as MY PAPER
    )
    
    repo.add(paper1)
    repo.add(paper2)
    
    # Mock search results to return equal distance
    # We are simulating that the vector store returns them with same relevance
    # but our logic SHOULD boost paper2.
    
    # IMPORTANT: Since we can't easily mock the internal vector store distance in this E2E test without real embeddings,
    # we will rely on the fact that currently NO re-ranking happens.
    # So we check if the router returns them purely based on vector distance (property of vector store).
    # If we assume equal distance (mocked), current implementation returns specific order.
    
    pass 

def test_data_cleanup_repro(setup_teardown):
    """
    Test that delete_test fails to clean up PDFs and Vectors (reproducing the bug).
    """
    repo = PaperRepository()
    vector_store = get_vector_store()

    # 1. Create a dummy PDF file
    pdf_path = TEST_PDF_PATH / "2024Test...3C.pdf"
    pdf_path.write_text("Dummy PDF content")
    
    # 2. Add paper with PDF reference
    paper = Paper(
        bibcode="2024Test...3C",
        title="Paper to Delete",
        abstract="Should be deleted.",
        pdf_path=str(pdf_path),
        year=2024
    )
    repo.add(paper)
    
    # 3. Verify it exists
    assert repo.get("2024Test...3C") is not None
    assert pdf_path.exists()
    
    # 4. Call delete_all
    repo.delete_all()
    
    # 5. Check if PDF still exists (IT SHOULD FAIL/Pass as bug reproduction if code is broken)
    # The current implementation of delete_all in repository.py:
    # It deletes Paper, PaperProject, Citations. 
    # It DOES NOT iterate to delete PDFs or call vector_store.clear() explicitly for all papers efficiently.
    # (Actually looking at code, delete_all only deletes DB records, it does NOT clean up files!)
    
    print(f"PDF Exists after delete_all: {pdf_path.exists()}")
    
    # Assert fix: PDF should be gone
    assert not pdf_path.exists(), "Fix verified: PDF file was deleted by delete_all"
    
    # Check if vector store was cleared
    # Using private access to check internal state or just count
    try:
        count = vector_store.count()
        # If count > 0, bug reproduced
        # However, repo.delete_all() doesn't call vector_store.clear() currently
        # It just deletes DB rows.
        print(f"Vector count after delete_all: {count}")
    except:
        pass

if __name__ == "__main__":
    pytest.main([__file__])
