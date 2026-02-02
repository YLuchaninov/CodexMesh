"""
Extractor registry + plugin loading via entry points.

Entry point group: "codex_mesh.extractors"
Each entry point must resolve to either:
- an Extractor instance, OR
- a callable () -> Extractor
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from importlib.metadata import entry_points
from pathlib import Path

from .protocols import Extractor

logger = logging.getLogger(__name__)

ExtractorFactory = Callable[[], Extractor]


@dataclass(frozen=True)
class RegistryStats:
    extractors: int
    extensions: int


class ExtractorRegistry:
    """Maps file extensions to extractors."""

    def __init__(self) -> None:
        self._by_ext: dict[str, Extractor] = {}
        self._errors: list[str] = []

    def record_error(self, source: str, error: str) -> None:
        """Record an initialization error."""
        self._errors.append(f"{source}: {error}")
        logger.warning(f"ExtractorRegistry error [{source}]: {error}")

    @property
    def validation_errors(self) -> list[str]:
        return list(self._errors)

    def register(self, extractor: Extractor) -> None:
        for ext in extractor.extensions:
            if not ext.startswith("."):
                raise ValueError(
                    f"Invalid extension '{ext}' for extractor '{extractor.language_id}'"
                )
            self._by_ext[ext.lower()] = extractor

    def get_for_path(self, path: Path) -> Extractor | None:
        return self._by_ext.get(path.suffix.lower())

    def supported_extensions(self) -> set[str]:
        return set(self._by_ext.keys())

    def supports_extension(self, ext: str) -> bool:
        """Check if a file extension is supported."""
        return ext.lower() in self._by_ext

    def stats(self) -> RegistryStats:
        return RegistryStats(
            extractors=len(set(self._by_ext.values())), extensions=len(self._by_ext)
        )

    def load_entry_points(self) -> None:
        eps = entry_points(group="codex_mesh.extractors")
        for ep in eps:
            obj = ep.load()
            extractor: Extractor
            extractor = obj() if callable(obj) else obj
            self.register(extractor)

    @classmethod
    def default(cls, include_docs: bool = False) -> ExtractorRegistry:
        reg = cls()

        # Built-ins (lazy import to avoid circular dependencies)
        # Note: We will implement these modules in subsequent steps
        try:
            from .python_treesitter import PythonTreeSitterExtractor

            reg.register(PythonTreeSitterExtractor())

        except ImportError as e:
            reg.record_error("python_treesitter", str(e))

        try:
            from .builtin_treesitter import register_defaults

            register_defaults(reg)
        except ImportError as e:
            reg.record_error("builtin_treesitter", str(e))

        try:
            from .sqlglot_extractor import SqlGlotExtractor

            reg.register(SqlGlotExtractor())

        except ImportError as e:
            reg.record_error("sqlglot", str(e))

        # Optional plugins
        reg.load_entry_points()

        if include_docs:
            from ..docs.extractor import MarkdownDocsExtractor

            reg.register(MarkdownDocsExtractor())

        return reg
