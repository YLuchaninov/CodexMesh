"""
Web API Error Handlers.

Provides consistent error handling for v1 API endpoints.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ..contracts.errors import ApiError


def install_error_handlers(app: FastAPI) -> None:
    """Install custom error handlers for the app."""

    @app.exception_handler(ApiError)
    async def api_error_handler(_: Request, exc: ApiError) -> JSONResponse:
        """Handle ApiError exceptions with consistent format."""
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_body(),
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(_: Request, exc: Exception) -> JSONResponse:
        """Handle unexpected exceptions."""
        import logging
        import traceback

        logger = logging.getLogger("codex_mesh.api")
        logger.error(f"Unhandled exception: {exc}", exc_info=True)

        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "Internal",
                    "message": f"Internal Server Error: {str(exc)}",
                    "details": {
                        "type": type(exc).__name__,
                        "trace": traceback.format_exc().splitlines()[
                            -5:
                        ],  # Last 5 lines for client safety/brevity
                    },
                }
            },
        )
