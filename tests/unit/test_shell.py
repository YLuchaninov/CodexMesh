"""
Unit tests for the safe_shell wrapper.
"""

import subprocess
from unittest.mock import Mock, patch

from codex_mesh.core.shell import safe_shell


def test_safe_shell_success():
    """Test successful command execution."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(stdout="hello world", stderr="", returncode=0)

        result = safe_shell(["echo", "hello"])

        assert result.success is True
        assert result.stdout == "hello world"
        assert result.returncode == 0
        assert result.timeout_expired is False


def test_safe_shell_failure():
    """Test command failure (non-zero return code)."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(stdout="", stderr="error occurred", returncode=1)

        result = safe_shell(["false"])

        assert result.success is False
        assert result.stderr == "error occurred"
        assert result.returncode == 1


def test_safe_shell_timeout():
    """Test command timeout."""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd=["sleep", "10"], timeout=1, output=b"partial output", stderr=b"some error"
        )

        result = safe_shell(["sleep", "10"], timeout=1)

        assert result.success is False
        assert result.timeout_expired is True
        assert result.stdout == "partial output"
        assert result.stderr == "some error"
        assert result.returncode == -1


def test_safe_shell_exception():
    """Test general exception during execution."""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = Exception("OS error")

        result = safe_shell(["invalid-cmd"])

        assert result.success is False
        assert result.returncode == -1
        assert "OS error" in result.stderr
