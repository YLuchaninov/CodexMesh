"""
Analysis MCP Tools.
"""

from typing import Any

from mcp.server.fastmcp import FastMCP

from ....services.analysis_service import AnalysisService
from ....services.logging import safe_tool
from ....services.project_service import ProjectService


def register_analysis_tools(
    server: FastMCP, analysis_service: AnalysisService, project_service: ProjectService
):
    def ensure_ready():
        project_service.ensure_ready()

    @server.tool()
    @safe_tool
    async def index_refresh(paths: list[str] | None = None) -> dict:
        """Incrementally refresh index."""
        ensure_ready()
        return analysis_service.refresh_index(paths)

    @server.tool()
    @safe_tool
    async def read_span(path: str, start_line: int, end_line: int, context: int = 0) -> Any:
        """Read line span with context."""
        ensure_ready()
        return analysis_service.read_span(path, start_line, end_line, context=context)

    @server.tool()
    @safe_tool
    async def search_code(query: str, limit: int = 10) -> Any:
        """Lexical search."""
        ensure_ready()
        return analysis_service.search_code(query, limit)

    @server.tool()
    @safe_tool
    async def semantic_search(query: str, k: int = 5) -> Any:
        """Semantic search."""
        ensure_ready()
        return analysis_service.semantic_search(query, k)

    @server.tool()
    @safe_tool
    async def get_hotspot(path: str = "") -> Any:
        """Hotspot metrics."""
        ensure_ready()
        return analysis_service.get_hotspot(path)

    @server.tool()
    @safe_tool
    async def get_repo_map(
        token_budget: int = 1024,
        include_entrypoints: bool = False,
        include_hotspots: bool = False,
        include_clusters: bool = False,
    ) -> str:
        """Generate RepoMap."""
        ensure_ready()
        return analysis_service.get_repo_map(
            token_budget, include_entrypoints, include_hotspots, include_clusters
        )

    @server.tool()
    @safe_tool
    async def get_function_info(name: str, include_body: bool = False) -> Any:
        """Function details."""
        ensure_ready()
        return analysis_service.get_function_info(name, include_body=include_body)

    @server.tool()
    @safe_tool
    async def resolve_symbol(
        query: str, prefer_types: list[str] | None = None, limit: int = 5
    ) -> Any:
        """Resolve symbol name."""
        ensure_ready()
        return analysis_service.resolve_symbol(query, prefer_types, limit)

    @server.tool()
    @safe_tool
    async def search_code_raw(query: str, limit: int = 10) -> Any:
        """Raw lexical search."""
        ensure_ready()
        return analysis_service.search_code_raw(query, limit)

    @server.tool()
    @safe_tool
    async def semantic_search_raw(query: str, k: int = 10) -> Any:
        """Raw semantic search."""
        ensure_ready()
        return analysis_service.semantic_search_raw(query, k)

    @server.tool()
    @safe_tool
    async def autotune_hotspots(
        target_rate: float = 0.05,
        percentile: int = 95,
        max_files: int = 800,
        apply: bool = False,
        path_filter: str | None = None,
    ) -> Any:
        """Auto-calibrate hotspot weights."""
        ensure_ready()
        return analysis_service.autotune_hotspot_weights(
            target_rate=target_rate,
            percentile=percentile,
            max_files=max_files,
            apply=apply,
            path_filter=path_filter,
        )
