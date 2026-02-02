"""
File system contracts.

Models for file and directory operations.
"""

from typing import Literal

from pydantic import BaseModel, Field

FSEntryType = Literal["file", "dir"]


class FSEntry(BaseModel):
    """File system entry (file or directory)."""

    name: str = Field(..., description="Entry name")
    path: str = Field(..., description="Relative path from project root")
    type: FSEntryType = Field(..., description="Entry type: file or dir")
    size: int | None = Field(None, description="Size in bytes (files only)")


class FSListRequest(BaseModel):
    """Request to list directory contents."""

    path: str = Field(".", description="Relative path to list")
    recursive: bool = Field(False, description="Include subdirectories recursively")
    include_hidden: bool = Field(False, description="Include hidden files")
    include_ignored: bool = Field(False, description="Include ignored files")


class FSListResponse(BaseModel):
    """Response with directory listing."""

    entries: list[FSEntry] = Field(default_factory=list)


class FSReadRequest(BaseModel):
    """Request to read file contents."""

    path: str = Field(..., description="Relative path to file")
    max_bytes: int = Field(200_000, ge=1, description="Maximum bytes to read")


class FSReadResponse(BaseModel):
    """Response with file contents."""

    path: str = Field(..., description="File path")
    content: str = Field(..., description="File content")
    truncated: bool = Field(False, description="Whether content was truncated")


class FSReadSpanRequest(BaseModel):
    """Request to read a specific span of lines from a file."""

    path: str = Field(..., description="Relative path to file")
    start_line: int = Field(..., ge=1, description="Start line (1-based)")
    end_line: int = Field(..., ge=1, description="End line (1-based)")
    context_lines: int = Field(
        20, ge=0, description="Number of context lines to include before/after"
    )
    max_bytes: int = Field(200_000, ge=1, description="Maximum bytes to read")


class FSReadSpanResponse(BaseModel):
    """Response with file span content."""

    path: str = Field(..., description="File path")
    content: str = Field(..., description="File content (span + context)")
    base_line: int = Field(..., description="The real line number of the first line in 'content'")
    highlight_start: int = Field(..., description="The start line relative to content origin")
    highlight_end: int = Field(..., description="The end line relative to content origin")
    truncated: bool = Field(False, description="Whether content was truncated")
