import functools
import inspect
import logging
import sys
import traceback
from collections.abc import Callable, Coroutine
from typing import Any

# Create logger for this module
logger = logging.getLogger("codex_mesh.services.logging")


def setup_logging(
    level: str = "INFO", json_format: bool = False, log_file: str | None = None
) -> None:
    """
    Configure global logging settings.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Whether to use JSON formatting for logs (not implemented in this MVP)
        log_file: Optional path to a log file. If set, logs will be written to this file.
    """
    root_logger = logging.getLogger()

    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # set root level
    log_level = getattr(logging, level.upper(), logging.INFO)
    root_logger.setLevel(log_level)

    # Create stderr handler (MCP uses stdout for protocol)
    stream_handler = logging.StreamHandler(sys.stderr)

    # Create formatter
    # We use a robust format that includes time, level, and module
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S"
    )
    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)

    # Optional: File Handler
    if log_file:
        file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
        file_handler.setFormatter(formatter)
        # Always use at least INFO for file, usually DEBUG if requested
        file_handler.setLevel(log_level)
        root_logger.addHandler(file_handler)

    # Set levels for noisy libraries
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("sse_starlette").setLevel(logging.WARNING)

    logger.info(
        f"Logging configured at level {level}" + (f" (file: {log_file})" if log_file else "")
    )


def safe_tool(
    func: Callable[..., Coroutine[Any, Any, Any]],
) -> Callable[..., Coroutine[Any, Any, Any]]:
    """
    Decorator for MCP tool functions to catch and log exceptions.
    Returns structured JSON error on failure for consistent API contracts.
    """
    import json

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"Error in tool '{func.__name__}': {e}\n{tb}")
            # Return structured error as JSON string for MCP type compatibility (P0 fix)
            # Clients can parse this JSON to detect and handle errors programmatically
            error_obj = {
                "ok": False,
                "error": {
                    "tool": func.__name__,
                    "type": type(e).__name__,
                    "message": str(e),
                },
            }
            return json.dumps(error_obj)

    # IMPORTANT: Preserve signature for FastMCP introspection
    wrapper.__signature__ = inspect.signature(func)  # type: ignore[attr-defined]
    return wrapper
