import unittest
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import modules to mock settings on
from src.core import llm_client
from src.db import vector_store
from src.core.llm_client import LLMClient
from src.db.vector_store import VectorStore, OllamaEmbeddingFunction, GoogleGeminiEmbeddingFunction

class TestProviders(unittest.TestCase):
    
    def setUp(self):
        self.orig_llm_settings = llm_client.settings
        self.orig_vector_settings = vector_store.settings
        
        # Create mocks
        self.mock_llm_settings = MagicMock()
        self.mock_vector_settings = MagicMock()
        
        # Inject mocks
        llm_client.settings = self.mock_llm_settings
        vector_store.settings = self.mock_vector_settings

    def tearDown(self):
        # Restore settings
        llm_client.settings = self.orig_llm_settings
        vector_store.settings = self.orig_vector_settings

    def test_llm_client_routing(self):
        """Test that LLMClient routes to the correct provider method."""
        
        # Test OpenAI
        self.mock_llm_settings.llm_provider = "openai"
        client = LLMClient()
        
        with patch.object(client, '_call_openai', return_value="openai_resp") as mock_openai:
            resp = client._call_llm("sys", "user")
            self.assertEqual(resp, "openai_resp")
            mock_openai.assert_called_once()
            
        # Test Gemini
        self.mock_llm_settings.llm_provider = "gemini"
        # Re-instantiate or update provider
        client = LLMClient() 
        
        with patch.object(client, '_call_gemini', return_value="gemini_resp") as mock_gemini:
            resp = client._call_llm("sys", "user")
            self.assertEqual(resp, "gemini_resp")
            mock_gemini.assert_called_once()

        # Test Ollama
        self.mock_llm_settings.llm_provider = "ollama"
        client = LLMClient()
        
        with patch.object(client, '_call_ollama', return_value="ollama_resp") as mock_ollama:
            resp = client._call_llm("sys", "user")
            self.assertEqual(resp, "ollama_resp")
            mock_ollama.assert_called_once()

    @patch('chromadb.PersistentClient')
    def test_vector_store_embedding_selection(self, mock_chroma):
        """Test that VectorStore selects the correct embedding function."""
        
        # Test Gemini configuration
        self.mock_vector_settings.embedding_provider = "gemini"
        self.mock_vector_settings.gemini_api_key = "fake_key"
        self.mock_vector_settings.chroma_path = Path("/tmp/chroma")
        
        # We need to ensure lazy loading is triggered, so reset private var if any
        # Since we create new instance, it should be clean.
        store = VectorStore(persist_dir=Path("/tmp/chroma_test"))
        
        # Configure behaviors
        # get_vector_store uses settings.chroma_path, but here we pass persist_dir
        
        ef = store.embedding_function
        self.assertIsInstance(ef, GoogleGeminiEmbeddingFunction)
        self.assertEqual(ef.api_key, "fake_key")
        
        # Test Ollama
        # Force re-evaluation by creating new store or clearing cached property
        store = VectorStore(persist_dir=Path("/tmp/chroma_test"))
        
        self.mock_vector_settings.embedding_provider = "ollama"
        self.mock_vector_settings.ollama_base_url = "http://localhost:11434"
        self.mock_vector_settings.ollama_embedding_model = "nomic-embed-text"
        
        ef = store.embedding_function
        self.assertIsInstance(ef, OllamaEmbeddingFunction)
        self.assertEqual(ef.base_url, "http://localhost:11434")
        self.assertEqual(ef.model_name, "nomic-embed-text")

if __name__ == '__main__':
    unittest.main()
