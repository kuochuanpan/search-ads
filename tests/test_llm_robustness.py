
import pytest
from unittest.mock import MagicMock, patch
from src.core.llm_client import LLMClient, ContextAnalysis, CitationType

def test_analyze_context_fallback_on_error():
    """Test that analyze_context falls back when _call_llm fails."""
    client = LLMClient()
    
    # Mock _call_llm to raise exception
    with patch.object(client, '_call_llm', side_effect=Exception("API connection failed")):
        # Mock fallback to ensure it's called (or check result)
        # The fallback logic is internal, but we can check the return value
        
        context = "This text talks about dark matter formation."
        result = client.analyze_context(context)
        
        assert isinstance(result, ContextAnalysis)
        assert result.citation_type == CitationType.GENERAL
        # Fallback keyword extraction should work
        assert "dark" in result.keywords or "matter" in result.keywords
        assert "fallback" in result.reasoning.lower() or "failed" in result.reasoning.lower()

def test_analyze_context_fallback_on_json_error():
    """Test that analyze_context falls back when JSON parsing fails."""
    client = LLMClient()
    
    # Mock _call_llm to return invalid JSON
    with patch.object(client, '_call_llm', return_value="Not a JSON string"):
        context = "This text needs a citation."
        result = client.analyze_context(context)
        
        assert isinstance(result, ContextAnalysis)
        # Should rely on fallback logic
        assert "fallback" in result.reasoning.lower() or "valid" in result.reasoning.lower() # JSONDecodeError usually mentions expectation
