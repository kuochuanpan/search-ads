"""Tests for Gemini model-name normalization and embedding configuration."""

import pytest
from unittest.mock import MagicMock, patch

from src.core.llm_client import normalize_gemini_model_name, LLMClient


class TestNormalizeGeminiModelName:
    """Tests for the normalize_gemini_model_name helper."""

    def test_strips_models_prefix(self):
        assert normalize_gemini_model_name("models/gemini-2.0-flash") == "gemini-2.0-flash"

    def test_strips_arbitrary_prefix(self):
        assert normalize_gemini_model_name("publishers/google/models/gemini-pro") == "gemini-pro"

    def test_no_prefix_unchanged(self):
        assert normalize_gemini_model_name("gemini-1.5-flash") == "gemini-1.5-flash"

    def test_empty_string_returns_default(self):
        assert normalize_gemini_model_name("") == "gemini-2.0-flash"

    def test_empty_string_custom_default(self):
        assert normalize_gemini_model_name("", default="gemini-1.5-pro") == "gemini-1.5-pro"

    def test_none_returns_default(self):
        # Settings may yield None when unset
        assert normalize_gemini_model_name(None) == "gemini-2.0-flash"


class TestGeminiLLMCall:
    """Verify that _call_gemini uses the normalized model name."""

    @pytest.fixture
    def gemini_client(self):
        with patch("src.core.llm_client.settings") as mock_settings, \
             patch("src.core.llm_client.ApiUsageRepository") as mock_repo:
            mock_settings.llm_provider = "gemini"
            mock_settings.gemini_api_key = "test_key"
            mock_settings.gemini_model = "models/gemini-2.0-flash"
            mock_settings.openai_api_key = ""
            mock_settings.anthropic_api_key = ""
            client = LLMClient()
            yield client, mock_settings

    def test_call_gemini_strips_prefix(self, gemini_client):
        client, mock_settings = gemini_client
        mock_settings.gemini_model = "models/gemini-2.0-flash"

        fake_response = MagicMock()
        fake_response.text = "test response"

        fake_genai_client = MagicMock()
        fake_genai_client.models.generate_content.return_value = fake_response
        client._gemini_client = fake_genai_client

        result = client._call_gemini("system", "user")

        call_kwargs = fake_genai_client.models.generate_content.call_args
        assert call_kwargs.kwargs["model"] == "gemini-2.0-flash"
        assert result == "test response"

    def test_call_gemini_empty_model_uses_default(self, gemini_client):
        client, mock_settings = gemini_client
        mock_settings.gemini_model = ""

        fake_response = MagicMock()
        fake_response.text = "ok"

        fake_genai_client = MagicMock()
        fake_genai_client.models.generate_content.return_value = fake_response
        client._gemini_client = fake_genai_client

        client._call_gemini("system", "user")

        call_kwargs = fake_genai_client.models.generate_content.call_args
        assert call_kwargs.kwargs["model"] == "gemini-2.0-flash"


class TestGeminiEmbeddingConfig:
    """Verify Gemini embedding branch in VectorStore respects settings."""

    def test_gemini_embedding_uses_configured_model(self):
        with patch("src.core.config.settings") as mock_settings:
            mock_settings.embedding_provider = "gemini"
            mock_settings.gemini_api_key = "test_key"
            mock_settings.embedding_model = "models/text-embedding-004"

            from src.db.vector_store import VectorStore, GoogleGeminiEmbeddingFunction

            with patch.object(VectorStore, "__init__", lambda self: None):
                store = VectorStore.__new__(VectorStore)
                store._embedding_function = None

                with patch("src.db.vector_store.settings", mock_settings), \
                     patch("src.db.vector_store.GoogleGeminiEmbeddingFunction") as MockEmbFunc:
                    MockEmbFunc.return_value = MagicMock()
                    ef = store.embedding_function
                    MockEmbFunc.assert_called_once_with(
                        api_key="test_key",
                        model_name="models/text-embedding-004",
                    )

    def test_gemini_embedding_fallback_when_openai_value(self):
        with patch("src.core.config.settings") as mock_settings:
            mock_settings.embedding_provider = "gemini"
            mock_settings.gemini_api_key = "test_key"
            mock_settings.embedding_model = "openai"  # stale value

            from src.db.vector_store import VectorStore

            with patch.object(VectorStore, "__init__", lambda self: None):
                store = VectorStore.__new__(VectorStore)
                store._embedding_function = None

                with patch("src.db.vector_store.settings", mock_settings), \
                     patch("src.db.vector_store.GoogleGeminiEmbeddingFunction") as MockEmbFunc:
                    MockEmbFunc.return_value = MagicMock()
                    ef = store.embedding_function
                    MockEmbFunc.assert_called_once_with(
                        api_key="test_key",
                        model_name="models/text-embedding-004",
                    )
