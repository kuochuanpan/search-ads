
import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.db.models import Paper, Note
from src.db.vector_store import VectorStore

def test_embed_paper_format():
    print("Testing embed_paper document formatting...")
    
    # Mock vector store dependencies
    with patch('src.core.config.settings') as mock_settings:
        mock_settings.chroma_path = Path("./temp_chroma")
        mock_settings.openai_api_key = "fake_key"
        
        # Mock ChromaDB client to avoid actual DB creation
        with patch('chromadb.PersistentClient') as mock_client:
            vs = VectorStore()
            # method mocking
            vs._abstracts_collection = MagicMock()
            
            # Create a test paper
            paper = Paper(
                bibcode="2024Test...123P",
                title="Test Paper Title",
                abstract="This is a test abstract.",
                authors='["Pan, K.", "Smith, J."]',
                year=2024,
                is_my_paper=True
            )
            
            # 1. Test embedding without note
            vs.embed_paper(paper)
            
            # Verify call args
            call_args = vs.abstracts_collection.upsert.call_args
            kwargs = call_args[1]
            doc_text = kwargs['documents'][0]
            metadata = kwargs['metadatas'][0]
            
            print(f"Document Text (No Note):\n---\n{doc_text}\n---")
            assert "Title: Test Paper Title" in doc_text
            assert "Authors: Pan, K., Smith, J." in doc_text
            assert "My Paper: Yes" in doc_text
            assert "Abstract: This is a test abstract" in doc_text
            assert "Notes:" not in doc_text
            
            assert metadata['is_my_paper'] is True
            assert metadata['has_note'] is False
            assert metadata['authors'] == "Pan, K., Smith, J."

            # 2. Test embedding with note
            vs.embed_paper(paper, note_content="This is a verify note.")
            
            call_args = vs.abstracts_collection.upsert.call_args
            kwargs = call_args[1]
            doc_text = kwargs['documents'][0]
            metadata = kwargs['metadatas'][0]
            
            print(f"\nDocument Text (With Note):\n---\n{doc_text}\n---")
            assert "Notes: This is a verify note." in doc_text
            assert metadata['has_note'] is True
            
            print("✅ embed_paper format verification passed!")

if __name__ == "__main__":
    test_embed_paper_format()
