"""
Safe shell execution wrapper.

Per advanced.md: All subprocesses and tools must run in safe, time-limited environments.
"""

import logging
import subprocess
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


def _to_text(x: Any) -> str:
    """Convert subprocess output to text reliably across text/binary modes."""
    if x is None:
        return ""
    if isinstance(x, (bytes, bytearray)):
        return x.decode("utf-8", errors="replace")
    if isinstance(x, str):
        return x
    # Best-effort
    return str(x)


@dataclass
class ShellResult:
    """Result of a shell execution."""

    stdout: str
    stderr: str
    returncode: int
    success: bool
    timeout_expired: bool = False


def safe_shell(
    cmd: list[str],
    cwd: str | None = None,
    timeout: int = 30,
    text: bool = True,
    **kwargs: Any,
) -> ShellResult:
    """
    Execute a shell command in a safe, time-limited environment.

    Args:
        cmd: List of command arguments.
        cwd: Optional working directory.
        timeout: Execution timeout in seconds.
        text: Whether to return output as text (defaults to True).
        kwargs: Additional arguments for subprocess.run.

    Returns:
        ShellResult object.
    """
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            timeout=timeout,
            capture_output=True,
            text=text,
            check=False,
            **kwargs,
        )
        return ShellResult(
            stdout=_to_text(result.stdout),
            stderr=_to_text(result.stderr),
            returncode=result.returncode,
            success=result.returncode == 0,
        )
    except subprocess.TimeoutExpired as e:
        logger.warning(f"Command timed out after {timeout}s: {' '.join(cmd)}")
        return ShellResult(
            stdout=e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or ""),
            stderr=e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or ""),
            returncode=-1,
            success=False,
            timeout_expired=True,
        )
    except Exception as e:
        logger.error(f"Error executing command {' '.join(cmd)}: {e}")
        return ShellResult(
            stdout="",
            stderr=str(e),
            returncode=-1,
            success=False,
        )
