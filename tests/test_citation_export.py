import pytest
from unittest.mock import MagicMock

def test_get_citation_export_cached(client, sample_paper, session):
    """Test getting export when cached in DB."""
    # Set cached values
    sample_paper.bibtex = "@article{cached}"
    sample_paper.bibitem_aastex = "\\bibitem{cached}"
    session.add(sample_paper)
    session.commit()

    # papers.py: @router.get("/{bibcode}/citations-export")
    response = client.get(f"/api/papers/{sample_paper.bibcode}/citations-export")
    
    assert response.status_code == 200
    data = response.json()
    assert data["bibtex"] == "@article{cached}"
    assert data["bibitem_aastex"] == "\\bibitem{cached}"

def test_get_citation_export_fetch(client, sample_paper, mock_ads_client):
    """Test fetching export from ADS when not in DB."""
    # Ensure empty in DB
    sample_paper.bibtex = None
    # No need to commit here, fixture created it clean or previous test non-interference due to transaction rollback ideally? 
    # Actually conftest uses same session for clean db if configured right, but simplest is update logic.
    
    mock_ads_client.generate_bibtex.return_value = "@article{fetched}"
    mock_ads_client.generate_aastex.return_value = "\\bibitem{fetched}"

    response = client.get(f"/api/papers/{sample_paper.bibcode}/citations-export")
    
    assert response.status_code == 200
    data = response.json()
    assert data["bibtex"] == "@article{fetched}"
    assert data["bibitem_aastex"] == "\\bibitem{fetched}"
    
    # Verify ADS client was called
    mock_ads_client.generate_bibtex.assert_called_with(sample_paper.bibcode)
