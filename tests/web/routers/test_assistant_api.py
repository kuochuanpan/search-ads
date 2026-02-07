import pytest
from pathlib import Path
from unittest.mock import patch


@patch("src.web.routers.assistant.settings")
def test_assistant_insights_disabled_returns_404(mock_settings, client):
    mock_settings.assistant_enabled = False

    resp = client.get("/api/assistant/insights")
    assert resp.status_code == 404


@patch("src.web.routers.assistant.settings")
def test_assistant_insights_enabled_returns_default_payload_when_missing(mock_settings, client, tmp_path):
    mock_settings.assistant_enabled = True
    mock_settings.data_dir = Path(tmp_path)

    resp = client.get("/api/assistant/insights")
    assert resp.status_code == 200

    data = resp.json()
    assert data["last_updated"] is None
    assert data["recommendations"] == []
    assert data["insights"] == []
