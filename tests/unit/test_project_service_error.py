from unittest.mock import MagicMock

import pytest

from codex_mesh.api.manager import ProjectManager, ProjectStatus
from codex_mesh.contracts.errors import ApiError
from codex_mesh.services.project_service import ProjectService


def test_ensure_ready_raises_503_when_loading():
    # Setup
    mock_manager = MagicMock(spec=ProjectManager)
    mock_manager.status = ProjectStatus.LOADING
    mock_manager.progress = 45
    mock_manager.message = "Loading stuff"
    mock_manager.server = None  # key: server is None when loading

    service = ProjectService(mock_manager)

    # Act & Assert
    with pytest.raises(ApiError) as exc_info:
        service.ensure_ready()

    assert exc_info.value.status_code == 503
    assert exc_info.value.code == "ServiceUnavailable"
    assert "Server is busy" in exc_info.value.message
    assert exc_info.value.details["progress"] == 45


def test_ensure_ready_raises_500_when_error():
    # Setup
    mock_manager = MagicMock(spec=ProjectManager)
    mock_manager.status = ProjectStatus.ERROR
    mock_manager.message = "Something blew up"
    mock_manager.server = None

    service = ProjectService(mock_manager)

    # Act & Assert
    with pytest.raises(ApiError) as exc_info:
        service.ensure_ready()

    assert exc_info.value.status_code == 500
    assert exc_info.value.code == "Internal"
    assert "Project Error" in exc_info.value.message


def test_ensure_ready_raises_409_when_idle_no_server():
    # Setup
    mock_manager = MagicMock(spec=ProjectManager)
    mock_manager.status = ProjectStatus.IDLE
    mock_manager.server = None

    service = ProjectService(mock_manager)

    # Act & Assert
    with pytest.raises(ApiError) as exc_info:
        service.ensure_ready()

    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "NotReady"
