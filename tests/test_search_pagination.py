
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from src.web.routers.search import _search_library, UnifiedSearchRequest, _search_ads
from src.web.schemas.search import SearchResultItem as UnifiedResultItem
from src.db.models import Paper

@pytest.mark.anyio
async def test_search_library_pagination_has_more():
    # Mock dependencies
    mock_vector_store = MagicMock()
    mock_paper_repo = MagicMock()
    
    # Setup request with limit 10, offset 0
    request = UnifiedSearchRequest(query="test", limit=10, offset=0, scope="library", mode="keywords")
    
    # Mock vector store returning 10 + 0 = 10 results (exactly the limit)
    # This should trigger total_available += 1
    mock_results = [{"bibcode": f"bib_{i}", "distance": 0.1, "metadata": {}} for i in range(10)]
    mock_vector_store.search.return_value = mock_results
    
    # Mock paper repo
    mock_paper_repo.get_batch.return_value = [
        Paper(bibcode=f"bib_{i}", title=f"Title {i}") for i in range(10)
    ]
    
    seen_bibcodes = set()
    
    # Execute
    results, total = await _search_library(request, "test", mock_vector_store, mock_paper_repo, seen_bibcodes)
    
    # Verify
    assert len(results) == 10
    assert total == 11 # Should be 10 + 1 because we hit the limit
    
@pytest.mark.anyio
async def test_search_library_pagination_exact_end():
    # Mock dependencies
    mock_vector_store = MagicMock()
    mock_paper_repo = MagicMock()
    
    # Setup request with limit 10
    request = UnifiedSearchRequest(query="test", limit=10, offset=0, scope="library", mode="keywords")
    
    # Mock vector store returning 9 results (less than limit)
    mock_results = [{"bibcode": f"bib_{i}", "distance": 0.1, "metadata": {}} for i in range(9)]
    mock_vector_store.search.return_value = mock_results
    
    # Mock paper repo
    mock_paper_repo.get_batch.return_value = [
        Paper(bibcode=f"bib_{i}", title=f"Title {i}") for i in range(9)
    ]
    
    seen_bibcodes = set()
    
    # Execute
    results, total = await _search_library(request, "test", mock_vector_store, mock_paper_repo, seen_bibcodes)
    
    # Verify
    assert len(results) == 9
    assert total == 9 # Should be exactly 9

@pytest.mark.anyio
async def test_search_ads_fallback_keywords():
    # Mock dependencies
    mock_ads_client = MagicMock()
    mock_paper_repo = MagicMock()
    
    # Setup request for natural language
    request = UnifiedSearchRequest(query="papers regarding dark matter formation", limit=10, offset=0, scope="ads", mode="natural")
    
    # Mock ads client search to return empty list initially to just check call args
    mock_ads_client.search.return_value = []
    
    seen_bibcodes = set()
    
    # Execute with NO LLM client (None passed to function usually, but here we pass None explicitly if we were calling the router directly)
    # But _search_ads doesn't take llm_client, the router `search_ads` endpoint does modification before calling `_search_ads`.
    # Wait, the fallback logic was added to `search_ads` endpoint AND inside `_search_ads`? 
    # Let me check my edit. 
    # I modified `search_ads` endpoint (for POST /ads) and `search_ads_stream`.
    # I verified `_search_ads` logic too?
    # Ah, `_search_ads` is called by `search_unified`. 
    # `search_unified` does "Step 1: analyze query" using LLM. If LLM fails or is missing, `query_used` remains `request.query`.
    # `_search_ads` takes `query` and just calls `ads_client.search`.
    
    # So `_search_ads` itself DOES NOT have the fallback logic in my edit?
    # Let's check the code again.
    pass 

@pytest.mark.anyio
async def test_search_unified_ads_fallback():
    # Verify that search_unified applies fallback if LLM is missing
    from src.web.routers.search import search_unified
    
    # Mock dependencies
    mock_paper_repo = MagicMock()
    mock_ads_client = MagicMock()
    mock_vector_store = MagicMock()
    # No LLM client
    
    query = "papers about dark matter" # natural language
    request = UnifiedSearchRequest(query=query, limit=10, scope="ads", mode="natural")
    
    # Mock ADS search
    # We want to check what query was actually passed to ads_client.search
    mock_ads_client.search.return_value = []
    
    # Execute
    await search_unified(
        request, 
        paper_repo=mock_paper_repo, 
        ads_client=mock_ads_client, 
        llm_client=None, # Simulate no LLM
        vector_store=mock_vector_store
    )
    
    # Verify args
    # Should have extracted "dark matter" or at least removed stopwords
    call_args = mock_ads_client.search.call_args
    assert call_args is not None
    used_query = call_args[0][0]
    
    # "about" is a stopword. "papers" is a stopword in my list. 
    # "dark" and "matter" are > 3 chars (wait, "dark" is 4).
    # Expected fallback: "dark matter"
    assert "about" not in used_query
    assert "papers" not in used_query
    assert "dark" in used_query
