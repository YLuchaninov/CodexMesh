"""Unit tests for services."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from codex_mesh.api.manager import ProjectManager, ProjectStatus
from codex_mesh.services.analysis_service import AnalysisService
from codex_mesh.services.fs_service import FileSystemService
from codex_mesh.services.project_service import ProjectService


@pytest.fixture
def mock_manager():
    manager = MagicMock(spec=ProjectManager)
    manager.status = ProjectStatus.READY
    manager.progress = 100
    manager.message = "Ready"
    manager.project_path = "/mock/project"
    manager.server = MagicMock()
    # Explicitly mock async method
    from unittest.mock import AsyncMock

    manager.server.start_watcher = AsyncMock()
    manager.server.project_root = Path("/mock/project")
    return manager


# --- ProjectService Tests ---


@pytest.mark.asyncio
async def test_project_service_get_status(mock_manager):
    service = ProjectService(mock_manager)
    status = service.get_status_snapshot()
    assert status["status"] == "READY"
    assert status["progress"] == 100


@pytest.mark.asyncio
async def test_project_service_connect(mock_manager):
    service = ProjectService(mock_manager)
    await service.connect("/new/path")
    mock_manager.connect.assert_called_with(
        "/new/path", background=True, auto_index=True, force_reindex=False, enable_watcher=False
    )


@pytest.mark.asyncio
async def test_project_service_connect_with_watcher(mock_manager):
    service = ProjectService(mock_manager)
    await service.connect("/new/path", enable_watcher=True)

    mock_manager.connect.assert_called_with(
        "/new/path", background=True, auto_index=True, force_reindex=False, enable_watcher=True
    )


@pytest.mark.asyncio
async def test_project_service_connect_without_watcher(mock_manager):
    service = ProjectService(mock_manager)
    await service.connect("/new/path", enable_watcher=False)

    mock_manager.connect.assert_called_with(
        "/new/path", background=True, auto_index=True, force_reindex=False, enable_watcher=False
    )


# --- FileSystemService Tests ---


def test_fs_service_read_file(mock_manager):
    service = FileSystemService(mock_manager)

    # Mock file content
    mock_file = MagicMock()
    mock_file.exists.return_value = True
    mock_file.is_file.return_value = True
    mock_file.read_text.return_value = "line1\nline2"

    with patch("codex_mesh.services.fs_service.Path.resolve") as mock_resolve:
        # Complex path mocking to pass relative_to check
        mock_resolve.return_value = mock_file
        mock_file.relative_to.return_value = Path("test.py")

        content = service.read_file("test.py")
        assert "   1 | line1" in content
        assert "   2 | line2" in content


def test_fs_service_list_directory(mock_manager):
    service = FileSystemService(mock_manager)

    mock_dir = MagicMock()
    mock_dir.exists.return_value = True
    mock_dir.is_dir.return_value = True

    item1 = MagicMock(spec=Path)
    item1.is_dir.return_value = True
    item1.relative_to.return_value = Path("subdir")
    item1.__lt__ = lambda self, other: True  # Allow sorting dummy mocks

    item2 = MagicMock(spec=Path)
    item2.is_dir.return_value = False
    item2.stat.return_value.st_size = 123
    item2.relative_to.return_value = Path("file.txt")
    item2.__lt__ = lambda self, other: False

    mock_dir.iterdir.return_value = [item1, item2]

    with patch("codex_mesh.services.fs_service.Path.resolve") as mock_resolve:
        mock_resolve.return_value = mock_dir
        mock_dir.relative_to.return_value = Path(".")

        listing = service.list_directory(".")
        assert "📁 subdir/" in listing
        assert "📄 file.txt (123 bytes)" in listing


# --- AnalysisService Tests ---


def test_analysis_service_search_code(mock_manager):
    service = AnalysisService(mock_manager)
    mock_server = mock_manager.server

    from codex_mesh.core.nodes import FunctionNode, NodeType

    mock_node = MagicMock(spec=FunctionNode)
    mock_node.id = "func::my_func"
    mock_node.name = "my_func"
    mock_node.node_type = NodeType.FUNCTION
    mock_node.file_path = "test.py"
    mock_node.line_start = 10
    mock_node.line_end = 20
    mock_node.signature = "def my_func()"
    mock_node.is_method = False
    mock_node.class_name = None

    mock_server.graph_search.search_by_name.return_value = [mock_node]

    result = service.search_code("my_func")
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["name"] == "my_func"
    assert result[0]["type"] == "function"


def test_analysis_service_search_code_md(mock_manager):
    service = AnalysisService(mock_manager)
    mock_server = mock_manager.server

    from codex_mesh.core.nodes import FunctionNode, NodeType

    mock_node = MagicMock(spec=FunctionNode)
    mock_node.id = "func::my_func"
    mock_node.name = "my_func"
    mock_node.node_type = NodeType.FUNCTION
    mock_node.file_path = "test.py"
    mock_node.line_start = 10
    mock_node.line_end = 20
    mock_node.signature = "def my_func()"
    mock_node.is_method = False
    mock_node.class_name = None

    mock_server.graph_search.search_by_name.return_value = [mock_node]

    result_md = service.search_code_md("my_func")
    assert "⚡ def my_func()" in result_md
    assert "📍 test.py:10" in result_md
