"""
File System API Router.
"""

from fastapi import APIRouter, Depends

from ....contracts.errors import ApiError
from ....contracts.fs import (
    FSEntry,
    FSListRequest,
    FSListResponse,
    FSReadRequest,
    FSReadResponse,
    FSReadSpanRequest,
    FSReadSpanResponse,
)
from ....services.fs_service import FileSystemService
from ....services.project_service import ProjectService
from ...dependencies import get_fs_service, get_project_service

router = APIRouter(prefix="/fs", tags=["fs"])


def ensure_ready(ps: ProjectService) -> None:
    ps.ensure_ready()


@router.post("/list", response_model=FSListResponse)
async def fs_list(
    req: FSListRequest,
    ps: ProjectService = Depends(get_project_service),
    fs: FileSystemService = Depends(get_fs_service),
):
    """List directory contents."""
    ensure_ready(ps)
    try:
        entries = fs.list_directory_structured(
            req.path,
            recursive=req.recursive,
            include_hidden=req.include_hidden,
            include_ignored=req.include_ignored,
        )
        return FSListResponse(entries=[FSEntry(**e) for e in entries])
    except FileNotFoundError as e:
        raise ApiError(404, "NotFound", str(e)) from e
    except PermissionError as e:
        raise ApiError(403, "Forbidden", str(e)) from e
    except ValueError as e:
        raise ApiError(400, "BadRequest", str(e)) from e
    except Exception as e:
        raise ApiError(500, "Internal", str(e)) from e


@router.post("/read", response_model=FSReadResponse)
async def fs_read(
    req: FSReadRequest,
    ps: ProjectService = Depends(get_project_service),
    fs: FileSystemService = Depends(get_fs_service),
):
    """Read file contents."""
    ensure_ready(ps)
    try:
        content, truncated = fs.read_file_raw(req.path, max_bytes=req.max_bytes)
        return FSReadResponse(path=req.path, content=content, truncated=truncated)
    except FileNotFoundError as e:
        raise ApiError(404, "NotFound", str(e)) from e
    except PermissionError as e:
        raise ApiError(403, "Forbidden", str(e)) from e
    except ValueError as e:
        raise ApiError(400, "BadRequest", str(e)) from e
    except Exception as e:
        raise ApiError(500, "Internal", str(e)) from e


@router.post("/read-span", response_model=FSReadSpanResponse)
async def fs_read_span(
    req: FSReadSpanRequest,
    ps: ProjectService = Depends(get_project_service),
    fs: FileSystemService = Depends(get_fs_service),
):
    """Read a span of lines from a file with context."""
    ensure_ready(ps)
    try:
        res = fs.read_file_span(
            req.path, req.start_line, req.end_line, req.context_lines, req.max_bytes
        )
        return FSReadSpanResponse(**res)
    except FileNotFoundError as e:
        raise ApiError(404, "NotFound", str(e)) from e
    except PermissionError as e:
        raise ApiError(403, "Forbidden", str(e)) from e
    except ValueError as e:
        raise ApiError(400, "BadRequest", str(e)) from e
    except Exception as e:
        raise ApiError(500, "Internal", str(e)) from e
