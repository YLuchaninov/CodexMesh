from unittest.mock import MagicMock

import pytest

from codex_mesh.services.fs_service import FileSystemService


@pytest.fixture
def mock_project_manager(tmp_path):
    pm = MagicMock()
    pm.server.project_root = tmp_path
    return pm


def test_read_file_raw_truncation(mock_project_manager, tmp_path):
    fs = FileSystemService(mock_project_manager)

    # Create large file
    f = tmp_path / "large.txt"
    f.write_text("a" * 150)

    # Read with limit 100
    content, truncated = fs.read_file_raw("large.txt", max_bytes=100)

    assert len(content) == 100
    assert truncated is True
    assert content == "a" * 100


def test_read_file_raw_no_truncation(mock_project_manager, tmp_path):
    fs = FileSystemService(mock_project_manager)
    f = tmp_path / "small.txt"
    f.write_text("abc")

    content, truncated = fs.read_file_raw("small.txt", max_bytes=100)

    assert content == "abc"
    assert truncated is False


def test_fs_error_handling(mock_project_manager):
    fs = FileSystemService(mock_project_manager)

    with pytest.raises(FileNotFoundError):
        fs.read_file_raw("non_existent.txt")

    with pytest.raises(ValueError):
        # Path traversal attempt
        fs.read_file_raw("../outside.txt")
