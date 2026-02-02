"""Integration tests for Web API."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from codex_mesh.api.manager import ProjectStatus
from codex_mesh.web.app import app

client = TestClient(app)


@pytest.fixture
def mock_pm_ready():
    # Mock the project manager stored in app.state
    from unittest.mock import AsyncMock

    pm = MagicMock()
    pm.status = ProjectStatus.READY
    pm.progress = 100
    pm.message = "Ready"
    pm.project_path = "/mock/project"
    pm.server = MagicMock()
    pm.server.project_root = MagicMock()
    pm.server.project_root.__truediv__.return_value = MagicMock()
    pm.server.start_watcher = AsyncMock()
    pm.connect = AsyncMock()

    # Inject into app state
    app.state.project_manager = pm
    return pm


def test_api_status(mock_pm_ready):
    response = client.get("/api/v1/project/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"]["status"] == "READY"
    assert data["status"]["progress"] == 100


def test_api_connect(mock_pm_ready):
    # Connect response check
    response = client.post(
        "/api/v1/project/connect",
        json={"project_path": "/new/project", "options": {"auto_index": True}},
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True
    # Connect is called in background
    mock_pm_ready.connect.assert_called()


def test_api_search(mock_pm_ready):
    # Mock analysis service side
    # V1 uses search_code_raw which returns dict with 'matches'
    mock_pm_ready.server.graph_search.search_by_name.return_value = []

    # Needs to mock search_code_raw on AnalysisService or mock server component logic
    # AnalysisService.search_code_raw calls server.graph_search.search_by_name(query, limit)

    response = client.post("/api/v1/analysis/search", json={"query": "test", "limit": 10})
    # If it fails with 500/Internal due to mock structure, we might need better mocking,
    # but let's try assuming AnalysisService wraps it safely.
    assert response.status_code == 200
    assert "matches" in response.json()


def test_api_fs_list(mock_pm_ready):
    # Mock FS service side
    # fs_service.list_directory_structured is called by V1
    # We need to mock FileSystemService methods or the underlying FS op

    # NOTE: The test uses patch on fs_service.Path.resolve.
    # V1 calls fs.list_directory_structured -> ...

    with patch("codex_mesh.services.fs_service.Path.resolve") as mock_resolve:
        mock_dir = MagicMock()
        mock_dir.exists.return_value = True
        mock_dir.is_dir.return_value = True
        mock_dir.iterdir.return_value = []
        mock_resolve.return_value = mock_dir

        response = client.post("/api/v1/fs/list", json={"path": "."})
        assert response.status_code == 200
        assert "entries" in response.json()
