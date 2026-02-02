"""
Extractor protocols for CodexMesh.

Per ARCHITECTURE.md + .agent rules: extractors must be decoupled and plugin-friendly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from codex_mesh.core.edges import Edge
    from codex_mesh.core.nodes import BaseNode, FileNode


@dataclass(frozen=True)
class ExtractorContext:
    """Immutable context for a single-file extraction."""

    project_root: Path
    file_path: Path
    relative_path: str
    config: dict = field(default_factory=dict)


@dataclass(frozen=True)
class PendingImport:
    """
    Import that must be resolved after all files are indexed.

    Attributes:
        source_file_id: ID of the file containing the import statement.
        raw: Raw import string as extracted from source.
        candidates: Relative paths (project-root-relative) that could match a FileNode.
        is_external: Whether this import refers to an external package/module.
        imported_names: Specific names imported (e.g., from `import {a, b}` or `from x import y`).
        alias_map: Mapping of original names to aliases (e.g., `{original: alias}`).
        is_star: Whether this is a star/wildcard import (`import *`).
        kind: Import statement kind (e.g., "import", "from", "require", "using", "include").
        module: Normalized module/package path.
    """

    source_file_id: str
    raw: str
    candidates: tuple[str, ...]
    is_external: bool
    imported_names: tuple[str, ...] | None = None
    alias_map: dict[str, str] | None = None
    is_star: bool = False
    kind: str | None = None
    module: str | None = None


@dataclass(frozen=True)
class PendingCall:
    """
    Call that must be resolved after all functions are indexed.

    callee_name is the best-effort string name (e.g., "helper", "run", "print").
    """

    source_id: str
    callee_name: str
    file_path: str
    line: int
    receiver: str | None = None


@dataclass
class ExtractionResult:
    """Extraction output for a single file."""

    nodes: list[BaseNode]
    edges: list[Edge]
    pending_imports: list[PendingImport]
    pending_calls: list[PendingCall]


class Extractor(Protocol):
    """
    Language/domain extractor.

    - extensions: file suffixes starting with dot (".py", ".ts", ...).
    - language_id: human-readable identifier ("python", "typescript", ...).
    """

    language_id: str
    extensions: tuple[str, ...]

    def extract(self, ctx: ExtractorContext, file_node: FileNode, content: str) -> ExtractionResult:
        """Extract nodes/edges from content."""
        ...
