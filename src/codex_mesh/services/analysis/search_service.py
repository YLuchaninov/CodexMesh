"""
Search Service for CodexMesh Analysis.
"""

import logging
from typing import Any

from ...core.nodes import ClassNode, FunctionNode
from ...review.markdown_render import MarkdownRenderer

logger = logging.getLogger(__name__)


class SearchService:
    """Handles lexical and semantic search operations."""

    def __init__(self, service):
        self.service = service

    @property
    def config(self):
        return self.service.config

    def search_code(self, query: str, limit: int | None = None) -> list[dict[str, Any]]:
        """Search for code elements by name."""
        if limit is None:
            limit = self.config.search.lexical_limit

        server = self.service._get_server()
        logger.info(f"SearchService.search_code: query='{query}', limit={limit}")
        results = server.graph_search.search_by_name(query, limit=limit)

        data = []
        for node in results:
            l_start = node.line_start if hasattr(node, "line_start") else None
            l_end = node.line_end if hasattr(node, "line_end") else None
            fp = self.service._node_file_path(node)

            item = {
                "id": node.id,
                "node_id": node.id,
                "name": node.name,
                "type": node.node_type.value,
                "file_path": fp,
                "line_start": l_start,
                "line_end": l_end,
                "span": {"start_line": l_start, "end_line": l_end} if l_start is not None else None,
            }
            if isinstance(node, FunctionNode):
                item["signature"] = node.signature
                item["is_method"] = node.is_method
                item["class_name"] = node.class_name
            elif isinstance(node, ClassNode):
                item["bases"] = node.bases
            data.append(item)
        return data

    def search_code_md(self, query: str, limit: int | None = None) -> str:
        """Search for code elements by name (Markdown output)."""
        results_data = self.search_code(query, limit)
        return MarkdownRenderer.render_search_results(results_data, query)

    def semantic_search(self, query: str, k: int | None = None) -> list[dict[str, Any]]:
        """Search code semantically."""
        if k is None:
            k = self.config.search.semantic_k

        server = self.service._get_server()
        logger.info(f"SearchService.semantic_search: query='{query}', k={k}")
        results = server.vector_search.search(query, k=k)

        data = []
        for result in results:
            l_start = getattr(result, "line_start", None)
            if l_start is None and isinstance(result, dict):
                l_start = result.get("line_start")

            l_end = getattr(result, "line_end", None)
            if l_end is None and isinstance(result, dict):
                l_end = result.get("line_end")

            if l_end is None and l_start is not None:
                l_end = l_start

            node_id = getattr(result, "id", None) or getattr(result, "node_id", None)
            if node_id is None and isinstance(result, dict):
                node_id = result.get("id") or result.get("node_id")

            if node_id is None:
                continue

            data.append(
                {
                    "id": node_id,
                    "node_id": node_id,
                    "name": getattr(result, "name", "unknown"),
                    "file_path": getattr(result, "file_path", None),
                    "line_start": l_start,
                    "line_end": l_end,
                    "span": {"start_line": l_start, "end_line": l_end}
                    if l_start is not None
                    else None,
                    "score": getattr(result, "score", 0.0),
                    "content": getattr(result, "content", "") or "",
                    "snippet": (getattr(result, "content", "") or "")[
                        : self.config.search.snippet_length
                    ],
                }
            )
        return data

    def semantic_search_md(self, query: str, k: int | None = None) -> str:
        """Search code semantically (Markdown output)."""
        results = self.semantic_search(query, k)
        return MarkdownRenderer.render_semantic_search_results(results, query)

    def resolve_symbol(
        self, query: str, prefer_types: list[str] | None = None, limit: int = 5
    ) -> dict[str, Any]:
        """Resolve a string query to a specific graph node."""
        if not query or not query.strip():
            return {
                "best": None,
                "candidates": [],
                "count": 0,
                "confidence": 0.0,
                "error": "Query string is empty or None",
            }

        candidates = self.service._get_server().graph_search.search_by_name(query, limit=limit * 2)

        formatted = []
        for node in candidates:
            score = 1.0 if node.name == query else 0.8
            if prefer_types and node.node_type.value in prefer_types:
                score += 0.2

            fp = self.service._node_file_path(node)
            formatted.append(
                {
                    "id": node.id,
                    "name": node.name,
                    "type": node.node_type.value,
                    "file_path": fp,
                    "line_start": getattr(node, "line_start", None),
                    "line_end": getattr(node, "line_end", None),
                    "span": {"start_line": node.line_start, "end_line": node.line_end}
                    if hasattr(node, "line_start")
                    else None,
                    "qualified_name": f"{fp}::{node.name}" if fp else node.name,
                    "score": score,
                }
            )

        formatted.sort(key=lambda x: x["score"], reverse=True)
        top = formatted[:limit]

        return {
            "best": top[0] if top else None,
            "candidates": top,
            "count": len(top),
            "confidence": top[0]["score"] if top else 0.0,
        }

    def search_text(self, query: str, limit: int = 50) -> list[dict[str, Any]]:
        """
        Search for text pattern in project files (grep-like).
        """
        import re
        from pathlib import Path

        server = self.service._get_server()
        root = Path(server.project_root)

        # Get all relevant files from graph (already filtered by IgnoreMatcher)
        files = server.graph_builder.get_files()

        matches = []
        pattern = re.compile(re.escape(query), re.IGNORECASE)

        for f in files:
            try:
                abs_path = root / f.relative_path
                if not abs_path.is_file():
                    continue

                content = abs_path.read_text(encoding="utf-8")
                for i, line in enumerate(content.splitlines()):
                    if pattern.search(line):
                        matches.append(
                            {
                                "file_path": f.relative_path,
                                "line_number": i + 1,
                                "line_content": line.strip(),
                                "type": "text_match",
                            }
                        )
                        if len(matches) >= limit:
                            return matches
            except Exception as e:
                logger.warning(f"Failed to search in {f.relative_path}: {e}")

        return matches

    def refresh_index(
        self,
        paths: list[str] | None = None,
        progress_callback: Any = None,
    ) -> dict[str, Any]:
        """
        Refresh the semantic search index.

        Args:
            paths: Optional list of file paths to re-index.
                   If None, re-indexes the entire codebase (auto_index logic).
            progress_callback: Optional callback for progress reporting.

        Returns:
            Dictionary with indexing results.
        """
        server = self.service._get_server()
        logger.info(f"SearchService.refresh_index: paths={paths}")

        try:
            if paths:
                # Incremental re-index for specific paths only
                # For now, we re-index the whole codebase - incremental is a future enhancement
                logger.info("Incremental re-indexing not yet supported, performing full re-index")

            chunk_count = server.vector_search.index_codebase(
                server.graph_builder,
                str(server.project_root),
                force_reindex=True,
                progress_callback=progress_callback,
            )
            return {
                "success": True,
                "chunks_indexed": chunk_count,
                "message": f"Re-indexed {chunk_count} code chunks",
            }
        except Exception as e:
            logger.error(f"Failed to refresh index: {e}", exc_info=True)
            return {
                "success": False,
                "chunks_indexed": 0,
                "error": str(e),
                "message": f"Indexing failed: {e}",
            }
