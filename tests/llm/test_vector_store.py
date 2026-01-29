
import pytest
import sys
from unittest.mock import MagicMock, patch
from src.db.models import Paper

# We need to mock chromadb BEFORE it is imported by the module under test 
# if it were imported at top level. But it is lazy loaded. 
# However, we can patch sys.modules to mock it entirely.

@pytest.fixture
def mock_chroma_module():
    mock_chroma = MagicMock()
    # Mock modules in sys.modules
    modules = {
        "chromadb": mock_chroma,
        "chromadb.config": MagicMock(),
        "chromadb.utils": MagicMock(),
        "chromadb.utils.embedding_functions": MagicMock(),
    }
    with patch.dict(sys.modules, modules):
        yield mock_chroma

@pytest.fixture
def vector_store(mock_chroma_module):
    # We must import VectorStore AFTER mocking sys.modules to ensure correct binding if it was top-level,
    # but since it's lazy, we can import anytime. 
    # But to be safe and clean:
    from src.db.vector_store import VectorStore
    
    with patch("src.db.vector_store.settings") as mock_settings:
        mock_settings.chroma_path = MagicMock()
        mock_settings.openai_api_key = "test_key"
        
        store = VectorStore(persist_dir=MagicMock())
        return store

class TestVectorStore:
    def test_init_lazy_load(self, mock_chroma_module):
        from src.db.vector_store import VectorStore
        store = VectorStore(persist_dir=MagicMock())
        assert store._client is None
        
        # Access client to trigger import
        _ = store.client
        
        # Verify PersistentClient was called on our mock
        mock_chroma_module.PersistentClient.assert_called_once()

    def test_embed_paper(self, vector_store):
        paper = Paper(
            bibcode="p1", 
            title="Title", 
            abstract="Abstract",
            authors='["Author A"]',
            is_my_paper=True,
            year=2024
        )
        
        # Setup mock collection
        mock_collection = MagicMock()
        vector_store.client.get_or_create_collection.return_value = mock_collection
        
        result = vector_store.embed_paper(paper)
        
        assert result is True
        mock_collection.upsert.assert_called_once()
        call_args = mock_collection.upsert.call_args[1]
        assert call_args["ids"] == ["p1"]
        assert "Title: Title" in call_args["documents"][0]
        assert "Abstract: Abstract" in call_args["documents"][0]
        assert call_args["metadatas"][0]["is_my_paper"] is True

    def test_embed_paper_no_abstract(self, vector_store):
        paper = Paper(bibcode="p1", title="Title", abstract=None)
        
        # Ensure we don't access client/collection if not needed
        # But if we did, it should be mocked
        mock_collection = MagicMock()
        vector_store.client.get_or_create_collection.return_value = mock_collection
        
        result = vector_store.embed_paper(paper)
        assert result is False
        mock_collection.upsert.assert_not_called()

    def test_embed_paper_with_note(self, vector_store):
        paper = Paper(bibcode="p1", title="Title", abstract=None)
        
        mock_collection = MagicMock()
        vector_store.client.get_or_create_collection.return_value = mock_collection
        
        result = vector_store.embed_paper(paper, note_content="My note")
        
        assert result is True
        call_args = mock_collection.upsert.call_args[1]
        assert "Notes: My note" in call_args["documents"][0]
        assert call_args["metadatas"][0]["has_note"] is True
        
    def test_split_text(self, vector_store):
        text = "Sentence one. Sentence two. Sentence three."
        chunks = vector_store._split_text(text, chunk_size=20, overlap=5)
        # Should split
        assert len(chunks) > 1

    def test_embed_pdf(self, vector_store):
        # Function calls delete_pdf internally
        vector_store.delete_pdf = MagicMock()
        
        mock_pdf_collection = MagicMock()
        # We need to make sure pdf_collection property returns this mock
        # pdf_collection calls get_or_create_collection("pdf_contents")
        vector_store.client.get_or_create_collection.side_effect = lambda name, **kwargs: mock_pdf_collection if name == "pdf_contents" else MagicMock()
        
        count = vector_store.embed_pdf(
            bibcode="p1",
            pdf_text="Some long text content.",
            title="Title"
        )
        
        assert count == 1 
        mock_pdf_collection.add.assert_called_once()

    def test_search_construction(self, vector_store):
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "ids": [["p1"]],
            "distances": [[0.1]],
            "metadatas": [[{"title": "Title"}]],
            "documents": [["Doc"]]
        }
        # abstracts_collection calls get_or_create
        vector_store.client.get_or_create_collection.return_value = mock_collection
        
        results = vector_store.search(
            query="test",
            n_results=5,
            min_year=2020,
            min_citations=10
        )
        
        assert len(results) == 1
        call_args = mock_collection.query.call_args[1]
        assert call_args["query_texts"] == ["test"]
        where = call_args["where"]
        assert {"year": {"$gte": 2020}} in where["$and"]

    def test_collection_conflict_recovery(self, vector_store):
        # Mock client methods directly
        mock_client = vector_store.client
        
        # First call raises ValueError
        mock_client.get_or_create_collection.side_effect = [ValueError("embedding function"), MagicMock()]
        
        vector_store._get_or_create_collection("test", "desc")
        
        mock_client.delete_collection.assert_called_once_with(name="test")
        mock_client.create_collection.assert_called_once()
