"""Unit tests for ProjectManager."""

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from codex_mesh.api.instance import CodexMeshServer
from codex_mesh.api.manager import ProjectManager, ProjectStatus


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the ProjectManager singleton before each test."""
    ProjectManager._reset_singleton()
    yield


@pytest.fixture
def mock_server():
    with patch("codex_mesh.api.manager.CodexMeshServer") as MockServer:
        mock_instance = MockServer.return_value
        mock_instance.initialize = MagicMock()
        mock_instance.project_root = "/mock/path"
        yield MockServer


@pytest.mark.asyncio
async def test_connect_success(mock_server):
    """Test successful connection to a project (synchronous)."""
    manager = ProjectManager()

    # Mock resolved path
    mock_resolved = MagicMock(spec=Path)
    mock_resolved.exists.return_value = True
    mock_resolved.is_dir.return_value = True
    mock_resolved.name = "test_project"
    mock_resolved.__str__.return_value = "/mock/path"

    with patch("codex_mesh.api.manager.Path") as MockPath:
        MockPath.return_value.resolve.return_value = mock_resolved

        # Start connection with background=False (waits for init)
        await manager.connect("/mock/path", background=False)

        assert manager.status == ProjectStatus.READY
        assert manager.progress == 100
        assert "Ready" in manager.message
        assert manager.server is not None
        mock_server.assert_called()
        manager.server.initialize.assert_called_once()


@pytest.mark.asyncio
async def test_connect_invalid_path(mock_server):
    """Test connection with invalid path."""
    manager = ProjectManager()

    # Mock resolved path that doesn't exist
    mock_resolved = MagicMock(spec=Path)
    mock_resolved.exists.return_value = False

    with patch("codex_mesh.api.manager.Path") as MockPath:
        MockPath.return_value.resolve.return_value = mock_resolved

        await manager.connect("/invalid/path", background=False)

        assert manager.status == ProjectStatus.ERROR
        assert manager.server is None
        assert "Invalid project path" in manager.message


@pytest.mark.asyncio
async def test_connect_cancellation(mock_server):
    """Test that starting a new connection cancels the previous one."""
    manager = ProjectManager()

    # Mock resolved path
    mock_resolved = MagicMock(spec=Path)
    mock_resolved.exists.return_value = True
    mock_resolved.is_dir.return_value = True
    mock_resolved.__str__.return_value = "/mock/path"

    import time

    # Mock resolved paths
    mock_path1 = MagicMock(spec=Path)
    mock_path1.exists.return_value = True
    mock_path1.is_dir.return_value = True
    mock_path1.__str__.return_value = "/path1"

    mock_path2 = MagicMock(spec=Path)
    mock_path2.exists.return_value = True
    mock_path2.is_dir.return_value = True
    mock_path2.__str__.return_value = "/path2"

    def slow_init_impl(*args, **kwargs):
        # This runs in a thread via asyncio.to_thread
        # We can't easily set status from here safely in some cases, but let's try
        # Actually, manager.status is already LOADING before this is called in _initialize_project
        time.sleep(0.5)
        return MagicMock(spec=CodexMeshServer)

    with (
        patch("codex_mesh.api.manager.Path") as MockPath,
        patch.object(manager, "_create_and_init_server") as mock_create,
    ):
        MockPath.side_effect = lambda p: mock_path1 if "path1" in str(p) else mock_path2
        mock_path1.resolve.return_value = mock_path1
        mock_path2.resolve.return_value = mock_path2
        mock_create.side_effect = slow_init_impl

        # Start first connection in background
        asyncio.create_task(manager.connect("/path1", background=True))

        # Wait a bit for the thread to start
        await asyncio.sleep(0.1)

        assert manager.status == ProjectStatus.LOADING
        assert manager.project_path == "/path1"

        # Start second connection - this should cancel the internal _init_task
        await manager.connect("/path2", background=False)

        assert manager.project_path == "/path2"
        assert manager.status == ProjectStatus.READY
        assert mock_create.call_count == 2
