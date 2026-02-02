"""Node type definitions for the code graph."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    """Types of nodes in the code graph."""

    FILE = "file"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    VARIABLE = "variable"
    TABLE = "table"
    COLUMN = "column"
    QUERY = "query"
    DOC_SECTION = "doc_section"


class BaseNode(BaseModel):
    """Base class for all graph nodes."""

    id: str = Field(..., description="Unique node identifier")
    name: str = Field(..., description="Human-readable name")
    node_type: NodeType = Field(..., description="Type of the node")
    meta: dict[str, Any] = Field(default_factory=dict, description="Custom metadata")

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, BaseNode):
            return self.id == other.id
        return False


class FileNode(BaseNode):
    """Represents a source code file."""

    node_type: NodeType = NodeType.FILE
    path: str = Field(..., description="Absolute file path")
    relative_path: str = Field(..., description="Path relative to project root")
    content_hash: str | None = Field(None, description="Hash of file content for change detection")
    mtime: float = Field(0.0, description="Modification timestamp")

    @classmethod
    def create(
        cls, path: str, relative_path: str, content_hash: str | None = None, mtime: float = 0.0
    ) -> FileNode:
        """Create a FileNode from a file path."""
        return cls(
            id=f"file::{relative_path}",
            name=relative_path,
            path=path,
            relative_path=relative_path,
            content_hash=content_hash,
            mtime=mtime,
        )


class ClassNode(BaseNode):
    """Represents a class definition."""

    node_type: NodeType = NodeType.CLASS
    file_path: str = Field(..., description="Path to the containing file")
    line_start: int = Field(..., description="Starting line number")
    line_end: int = Field(..., description="Ending line number")
    docstring: str | None = Field(None, description="Class docstring")
    bases: list[str] = Field(default_factory=list, description="Base class names")
    decorators: list[str] = Field(default_factory=list, description="Class decorators")
    modifiers: list[str] = Field(
        default_factory=list, description="Access modifiers (public/private/export)"
    )

    @classmethod
    def create(
        cls,
        name: str,
        file_path: str,
        line_start: int,
        line_end: int,
        docstring: str | None = None,
        bases: list[str] | None = None,
        decorators: list[str] | None = None,
        modifiers: list[str] | None = None,
        meta: dict[str, Any] | None = None,
    ) -> ClassNode:
        """Create a ClassNode."""
        return cls(
            id=f"class::{file_path}::{name}",
            name=name,
            file_path=file_path,
            line_start=line_start,
            line_end=line_end,
            docstring=docstring,
            bases=bases or [],
            decorators=decorators or [],
            modifiers=modifiers or [],
            meta=meta or {},
        )


class FunctionNode(BaseNode):
    """Represents a function or method definition."""

    node_type: NodeType = NodeType.FUNCTION
    file_path: str = Field(..., description="Path to the containing file")
    line_start: int = Field(..., description="Starting line number")
    line_end: int = Field(..., description="Ending line number")
    docstring: str | None = Field(None, description="Function docstring")
    signature: str | None = Field(None, description="Function signature")
    is_method: bool = Field(False, description="Whether this is a class method")
    class_name: str | None = Field(None, description="Parent class name if method")
    decorators: list[str] = Field(default_factory=list, description="Function decorators")
    modifiers: list[str] = Field(
        default_factory=list, description="Access modifiers (public/private/async)"
    )

    @classmethod
    def create(
        cls,
        name: str,
        file_path: str,
        line_start: int,
        line_end: int,
        docstring: str | None = None,
        signature: str | None = None,
        is_method: bool = False,
        class_name: str | None = None,
        decorators: list[str] | None = None,
        modifiers: list[str] | None = None,
        meta: dict[str, Any] | None = None,
    ) -> FunctionNode:
        """Create a FunctionNode."""
        if class_name:
            node_id = f"method::{file_path}::{class_name}.{name}"
        else:
            node_id = f"function::{file_path}::{name}"

        return cls(
            id=node_id,
            name=name,
            node_type=NodeType.METHOD if is_method else NodeType.FUNCTION,
            file_path=file_path,
            line_start=line_start,
            line_end=line_end,
            docstring=docstring,
            signature=signature,
            is_method=is_method,
            class_name=class_name,
            decorators=decorators or [],
            modifiers=modifiers or [],
            meta=meta or {},
        )


class DocSectionNode(BaseNode):
    """Represents a section in a documentation file."""

    node_type: NodeType = NodeType.DOC_SECTION

    file_path: str = Field(..., description="Doc file path relative to project root")
    line_start: int = Field(..., description="Section start line")
    line_end: int = Field(..., description="Section end line")

    title: str = Field(..., description="Heading title")
    level: int = Field(..., description="Heading level 1..6")
    anchor: str | None = Field(None, description="Slug/anchor for the section")

    content: str = Field(..., description="Section content (trimmed)")
    content_hash: str | None = Field(None, description="Hash for change tracking")
    refs: list[str] = Field(default_factory=list, description="Raw references extracted from text")

    @classmethod
    def create(
        cls,
        *,
        doc_rel_path: str,
        title: str,
        level: int,
        line_start: int,
        line_end: int,
        content: str,
        anchor: str | None = None,
        content_hash: str | None = None,
        refs: list[str] | None = None,
    ) -> DocSectionNode:
        safe_anchor = anchor or title.lower().strip().replace(" ", "-")
        # Ensure ID uniqueness by including line number
        node_id = f"doc::{doc_rel_path}::{safe_anchor}::{line_start}"
        return cls(
            id=node_id,
            name=f"{doc_rel_path}#{safe_anchor}",
            node_type=NodeType.DOC_SECTION,
            file_path=doc_rel_path,
            line_start=line_start,
            line_end=line_end,
            title=title,
            level=level,
            anchor=safe_anchor,
            content=content,
            content_hash=content_hash,
            refs=refs or [],
        )


FileNode.model_rebuild()
ClassNode.model_rebuild()
FunctionNode.model_rebuild()
DocSectionNode.model_rebuild()
