
import pytest
from unittest.mock import MagicMock, patch
import json
from src.core.llm_client import LLMClient, ContextAnalysis, CitationType, RankedPaper
from src.db.models import Paper

# We need to mock settings before creating the client
@pytest.fixture
def mock_settings():
    with patch("src.core.llm_client.settings") as mock:
        mock.llm_provider = "openai"
        mock.anthropic_api_key = "test_anthropic_key"
        mock.openai_api_key = "test_openai_key"
        mock.anthropic_model = "claude-3-opus"
        mock.openai_model = "gpt-4"
        yield mock

@pytest.fixture
def client(mock_settings):
    with patch("src.core.llm_client.ApiUsageRepository") as mock_repo:
        # LLMClient now takes no args, reads from settings
        return LLMClient()

class TestLLMClient:
    def test_init(self, client):
        assert client.provider == "openai"
        assert client._anthropic_client is None
        assert client._openai_client is None
        assert client.usage_repo is not None

    def test_analyze_context(self, client):
        # Mock the LLM response
        mock_response = json.dumps({
            "topic": "Dark Matter",
            "claim": "Halos exist",
            "citation_type": "foundational",
            "keywords": ["dark matter", "halo"],
            "search_query": "dark matter halo",
            "reasoning": "Test reasoning"
        })
        
        with patch.object(client, "_call_llm", return_value=mock_response):
            analysis = client.analyze_context("Some latex context")
            
            assert isinstance(analysis, ContextAnalysis)
            assert analysis.topic == "Dark Matter"
            assert analysis.claim == "Halos exist"
            assert analysis.citation_type == CitationType.FOUNDATIONAL
            assert analysis.keywords == ["dark matter", "halo"]

    def test_analyze_context_fallback(self, client):
        # Mock invalid JSON response to trigger fallback
        with patch.object(client, "_call_llm", return_value="Not JSON"):
            context = "This is a study about dark matter halos."
            analysis = client.analyze_context(context)
            
            assert isinstance(analysis, ContextAnalysis)
            assert analysis.citation_type == CitationType.GENERAL
            # Fallback should extract keywords
            assert "dark" in analysis.keywords or "matter" in analysis.keywords

    def test_rank_papers(self, client):
        # Prepare data
        paper1 = Paper(bibcode="p1", title="Paper 1", abstract="Abs 1", citation_count=100)
        paper2 = Paper(bibcode="p2", title="Paper 2", abstract="Abs 2", citation_count=10)
        papers = [paper1, paper2]
        
        context_analysis = ContextAnalysis(
            topic="Test", claim="Test", citation_type=CitationType.GENERAL,
            keywords=[], search_query="", reasoning=""
        )
        
        # Mock batch response
        mock_ranking = json.dumps([
            {"id": 0, "relevance_score": 0.9, "explanation": "Good", "citation_type": "foundational"},
            {"id": 1, "relevance_score": 0.1, "explanation": "Bad", "citation_type": "general"}
        ])
        
        with patch.object(client, "_call_llm", return_value=mock_ranking):
             # Patch NoteRepository where it is defined/imported
             with patch("src.db.repository.NoteRepository") as mock_note_repo:
                 mock_note_repo.return_value.get_batch.return_value = []
                 
                 ranked = client.rank_papers(papers, "context", context_analysis)
                 
                 assert len(ranked) == 2
                 assert ranked[0].paper.bibcode == "p1"
                 assert ranked[0].relevance_score == 0.9
                 assert ranked[1].paper.bibcode == "p2"
                 assert ranked[1].relevance_score == 0.1

    def test_extract_keywords(self, client):
        mock_response = '["keyword1", "keyword2"]'
        with patch.object(client, "_call_llm", return_value=mock_response):
            keywords = client.extract_keywords_only("some text")
            assert keywords == ["keyword1", "keyword2"]

    def test_extract_keywords_fallback(self, client):
        with patch.object(client, "_call_llm", side_effect=Exception("Fail")):
            text = "These are some important keywords for astronomy."
            keywords = client.extract_keywords_only(text)
            assert len(keywords) > 0
            assert "keywords" in keywords or "important" in keywords
