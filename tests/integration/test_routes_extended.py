from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from codex_mesh.api.manager import ProjectStatus
from codex_mesh.web.app import create_app
from codex_mesh.web.dependencies import (
    get_analysis_service,
    get_fs_service,
    get_project_manager,
    get_project_service,
)


@pytest.fixture
def mock_pm():
    pm = MagicMock()
    # Mocking status with .value attribute for snapshotting
    pm.status = ProjectStatus.READY
    pm.project_path = "/mock/project"
    pm.progress = 100
    pm.message = "Ready"
    pm.server = MagicMock()
    return pm


@pytest.fixture
def client(mock_pm):
    app = create_app()
    app.dependency_overrides[get_project_manager] = lambda: mock_pm

    # Overriding all services to bypass ensure_ready and other logic
    mock_ps = MagicMock()
    mock_ps.ensure_ready.return_value = None
    app.dependency_overrides[get_project_service] = lambda: mock_ps

    mock_fs = MagicMock()
    app.dependency_overrides[get_fs_service] = lambda: mock_fs

    mock_an = MagicMock()
    app.dependency_overrides[get_analysis_service] = lambda: mock_an

    return TestClient(app)


def test_project_status_v1(client):
    ps = client.app.dependency_overrides[get_project_service]()
    ps.get_status_snapshot.return_value = {
        "status": "READY",
        "progress": 100,
        "message": "Ready",
        "project_path": "/mock/project",
    }
    response = client.get("/api/v1/project/status")
    assert response.status_code == 200
    assert response.json()["status"]["status"] == "READY"


def test_fs_list_v1(client):
    fs = client.app.dependency_overrides[get_fs_service]()
    # FIX: Add missing 'path' and ensure 'type' is 'file' or 'dir'
    fs.list_directory_structured.return_value = [
        {"name": "file.txt", "path": "file.txt", "type": "file"}
    ]

    response = client.post("/api/v1/fs/list", json={"path": "."})
    if response.status_code != 200:
        print(f"DEBUG FS LIST: {response.json()}")
    assert response.status_code == 200
    assert response.json()["entries"][0]["name"] == "file.txt"


def test_fs_read_v1(client):
    fs = client.app.dependency_overrides[get_fs_service]()
    fs.read_file_raw.return_value = ("content", False)

    response = client.post("/api/v1/fs/read", json={"path": "file.py"})
    assert response.status_code == 200
    assert response.json()["content"] == "content"


def test_analysis_search_v1(client):
    an = client.app.dependency_overrides[get_analysis_service]()
    an.search_code_raw.return_value = {
        "matches": [{"id": "m1", "file_path": "a/b.py", "content": "match"}]
    }

    response = client.post("/api/v1/analysis/search", json={"query": "q", "path_prefix": "a/"})
    assert response.status_code == 200
    assert len(response.json()["matches"]) == 1


def test_analysis_semantic_v1(client):
    an = client.app.dependency_overrides[get_analysis_service]()
    # FIX: Use 'results' key and add missing 'name' and other fields
    an.semantic_search_raw.return_value = {
        "results": [{"id": "n1", "name": "Node1", "score": 0.9}],
        "matches": [{"id": "n1", "name": "Node1", "score": 0.9}],
    }

    response = client.post("/api/v1/analysis/semantic", json={"query": "test", "limit": 5})
    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_analysis_repomap_v1(client):
    an = client.app.dependency_overrides[get_analysis_service]()
    an.get_repo_map.return_value = "REPO MAP CONTENT"

    # FIX: token_budget must be >= 200
    response = client.post("/api/v1/analysis/repomap", json={"token_budget": 200})
    assert response.status_code == 200
    assert response.json()["map"] == "REPO MAP CONTENT"


def test_analysis_hotspots_v1(client):
    an = client.app.dependency_overrides[get_analysis_service]()
    an.get_hotspot_raw.return_value = {
        "report": [{"node_id": "n1", "total": 5.0}],
        "summary": "hot",
    }

    response = client.post("/api/v1/analysis/hotspots", json={"path": "src/", "top_n": 10})
    assert response.status_code == 200
    assert len(response.json()["report"]) == 1


def test_graph_entrypoints_v1(client):
    an = client.app.dependency_overrides[get_analysis_service]()
    # FIX: Ensure it matches EntrypointItem: id, name, type are required
    an.entrypoints_list.return_value = {
        "entrypoints": [{"id": "e1", "name": "main", "type": "function", "kind": "function"}]
    }

    response = client.post("/api/v1/graph/entrypoints", json={"kind": "all", "limit": 10})
    assert response.status_code == 200
    assert len(response.json()["entrypoints"]) == 1


def test_graph_subgraph_v1(client):
    an = client.app.dependency_overrides[get_analysis_service]()
    # FIX: Ensure it matches NodeDTO: id, name, type are required
    an.get_subgraph.return_value = {
        "nodes": [{"id": "n1", "name": "N1", "type": "file"}],
        "edges": [],
    }

    response = client.post("/api/v1/graph/subgraph", json={"roots": ["n1"], "depth": 1})
    if response.status_code != 200:
        print(f"DEBUG SUBGRAPH: {response.json()}")
    assert response.status_code == 200


def test_intents_v1(client):
    with patch("codex_mesh.web.api.v1.intents._get_intent_registry") as MockReg:
        mock_reg = MockReg.return_value
        intent = MagicMock()
        intent.id = "test"
        intent.title = "Test"
        intent.description = "desc"
        intent.slots = {}
        intent.examples = []
        intent.tags = []
        intent.workflow = {"steps": []}
        mock_reg.list.return_value = [intent]
        mock_reg.get.return_value = intent

        # Patch At source
        with patch("codex_mesh.workflows.engine.runner.JsonWorkflowRunner") as MockRunner:
            runner = MockRunner.return_value
            runner.run.return_value = MagicMock(success=True, changes={"result": "ok"}, logs=[])
            with patch(
                "codex_mesh.workflows.engine.input_prep.prepare_intent_input", return_value={}
            ):
                response = client.post("/api/v1/intents/execute", json={"intent_id": "test"})
                assert response.status_code == 200


def test_tools_registry_v1(client):
    response = client.get("/api/v1/tools")
    assert response.status_code == 200
