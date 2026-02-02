"""
CodexMesh - MCP server for semantic code analysis.

Provides LLM agents with structured context about codebases through:
- Code Graph: Dependencies between files, classes, functions
- Hotspot Metrics: Problem area scoring
- RepoMap: Compact repository map for LLM context
- Semantic Search: RAG-based code embeddings
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "CodexMeshServer",
    "main",
    "CodexMeshConfig",
    "GRAPH_SCHEMA_VERSION",
    "CodeGraphBuilder",
    "EmbeddingEngine",
    "GraphProvider",
    "HotspotCalculator",
    "HotspotCalculatorProtocol",
]

# Keep type-checkers happy without importing heavy modules at runtime
if TYPE_CHECKING:
    from .api import (
        CodexMeshServer,  # noqa: F401
        main,  # noqa: F401
    )
    from .config import CodexMeshConfig  # noqa: F401
    from .core import (  # noqa: F401
        GRAPH_SCHEMA_VERSION,
        CodeGraphBuilder,
        EmbeddingEngine,
        GraphProvider,
        HotspotCalculator,
    )


_LAZY_ATTRS: dict[str, tuple[str, str]] = {
    # api
    "CodexMeshServer": ("codex_mesh.api", "CodexMeshServer"),
    "main": ("codex_mesh.api", "main"),
    # config
    "CodexMeshConfig": ("codex_mesh.config", "CodexMeshConfig"),
    # core
    "GRAPH_SCHEMA_VERSION": ("codex_mesh.core", "GRAPH_SCHEMA_VERSION"),
    "CodeGraphBuilder": ("codex_mesh.core", "CodeGraphBuilder"),
    "EmbeddingEngine": ("codex_mesh.core", "EmbeddingEngine"),
    "GraphProvider": ("codex_mesh.core", "GraphProvider"),
    "HotspotCalculator": ("codex_mesh.core", "HotspotCalculator"),
}


def __getattr__(name: str) -> Any:
    if name == "HotspotCalculatorProtocol":
        val = importlib.import_module("codex_mesh.core").HotspotCalculator
        globals()[name] = val
        return val

    spec = _LAZY_ATTRS.get(name)
    if not spec:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    mod_name, attr_name = spec
    mod = importlib.import_module(mod_name)
    val = getattr(mod, attr_name)
    globals()[name] = val  # cache
    return val
