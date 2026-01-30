import pytest
from unittest.mock import MagicMock, patch

from src.core.config import settings

# We use the 'client' fixture from conftest.py, so we don't need to import app or create TestClient here.

@patch("src.web.routers.settings.settings")
def test_get_models_openai(mock_settings, client):
    mock_settings.openai_api_key = "test-key"
    
    with patch("openai.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        # Mock models response
        mock_model_gpt = MagicMock()
        mock_model_gpt.id = "gpt-4o"
        mock_model_o1 = MagicMock()
        mock_model_o1.id = "o1-preview"
        mock_model_audio = MagicMock()
        mock_model_audio.id = "gpt-4o-audio-preview"
        
        mock_client.models.list.return_value.data = [mock_model_gpt, mock_model_o1, mock_model_audio]
        
        response = client.get("/api/settings/models/openai")
        assert response.status_code == 200
        # Audio should be filtered out
        assert response.json() == {"models": ["gpt-4o", "o1-preview"]}

@patch("src.web.routers.settings.settings")
def test_get_models_anthropic(mock_settings, client):
    mock_settings.anthropic_api_key = "test-key"
    
    response = client.get("/api/settings/models/anthropic")
    assert response.status_code == 200
    assert "claude-3-opus-20240229" in response.json()["models"]

@patch("src.web.routers.settings.settings")
def test_get_models_gemini(mock_settings, client):
    mock_settings.gemini_api_key = "test-key"
    
    with patch("google.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        
        # Mock models response
        m1 = MagicMock(); m1.name = "models/gemini-1.5-flash"
        m2 = MagicMock(); m2.name = "models/gemma-2b"
        
        mock_client.models.list.return_value = [m1, m2]
        
        response = client.get("/api/settings/models/gemini")
        assert response.status_code == 200
        assert "gemini-1.5-flash" in response.json()["models"]
        assert "gemma-2b" in response.json()["models"]

@patch("src.web.routers.settings.settings")
def test_get_models_ollama(mock_settings, client):
    mock_settings.ollama_base_url = "http://localhost:11434"
    
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "models": [{"name": "llama3"}, {"name": "nomic-embed-text"}]
        }
        
        response = client.get("/api/settings/models/ollama")
        assert response.status_code == 200
        assert "llama3" in response.json()["models"]
