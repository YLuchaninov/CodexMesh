"""
Graph MCP Tools.
"""

from typing import Any

from mcp.server.fastmcp import FastMCP

from ....services.analysis_service import AnalysisService
from ....services.logging import safe_tool
from ....services.project_service import ProjectService


def register_graph_tools(
    server: FastMCP, analysis_service: AnalysisService, project_service: ProjectService
):
    def ensure_ready():
        project_service.ensure_ready()

    @server.tool()
    @safe_tool
    async def callers_of(node_id: str, depth: int = 1) -> Any:
        """Find callers."""
        ensure_ready()
        return analysis_service.callers_of(node_id, depth=depth)

    @server.tool()
    @safe_tool
    async def callees_of(node_id: str, depth: int = 1) -> Any:
        """Find callees."""
        ensure_ready()
        return analysis_service.callees_of(node_id, depth=depth)

    @server.tool()
    @safe_tool
    async def get_subgraph(
        root_id: str | None = None,
        roots: list[str] | None = None,
        depth: int = 1,
        direction: str = "both",
        edge_types: list[str] | None = None,
        max_nodes: int = 200,
    ) -> Any:
        """Get subgraph centered at root nodes."""
        ensure_ready()
        if roots is None:
            if not root_id:
                return {"error": "Provide either roots[] or root_id"}
            roots = [root_id]
        return analysis_service.get_subgraph(roots, depth, direction, edge_types, max_nodes)

    @server.tool()
    @safe_tool
    async def get_dependency_tree(
        root_id: str, depth: int = 2, direction: str = "out", edge_types: list[str] | None = None
    ) -> Any:
        """Get dependency tree."""
        ensure_ready()
        return analysis_service.get_dependency_tree(root_id, depth, direction, edge_types)

    @server.tool()
    @safe_tool
    async def find_path(
        from_id: str, to_id: str, edge_types: list[str] | None = None, max_hops: int | None = None
    ) -> Any:
        """Find path between nodes."""
        ensure_ready()
        return analysis_service.find_path(from_id, to_id, edge_types, max_hops)

    @server.tool()
    @safe_tool
    async def detect_entrypoints(limit: int = 50) -> Any:
        """Detect entrypoints."""
        ensure_ready()
        return analysis_service.detect_entrypoints(limit)

    @server.tool()
    @safe_tool
    async def entrypoints_list(limit: int = 50) -> Any:
        """List entrypoints (alias)."""
        ensure_ready()
        return analysis_service.detect_entrypoints(limit)

    @server.tool()
    @safe_tool
    async def build_call_graph(
        roots: list[str], depth: int = 1, direction: str = "out", max_nodes: int = 200
    ) -> Any:
        """Build call graph."""
        ensure_ready()
        return analysis_service.build_call_graph(roots, depth, direction, max_nodes)

    @server.tool()
    @safe_tool
    async def find_entrypoint_paths(target_id: str, limit: int = 20, max_hops: int = 10) -> Any:
        """Find paths from entrypoints."""
        ensure_ready()
        return analysis_service.find_entrypoint_paths(target_id, limit, max_hops)

    @server.tool()
    @safe_tool
    async def compute_reachable_set(
        roots: list[str], edge_types: list[str], max_depth: int = 10, max_nodes: int = 1000
    ) -> Any:
        """Compute reachable nodes."""
        ensure_ready()
        return analysis_service.compute_reachable_set(roots, edge_types, max_depth, max_nodes)

    @server.tool()
    @safe_tool
    async def render_graph(format: str, nodes: list[Any], edges: list[Any]) -> Any:
        """Render graph to string format."""
        if format == "mermaid":
            from ....review.graph_render import to_mermaid

            return {"content": to_mermaid(nodes, edges)}
        return {"content": f"Unsupported format: {format}"}
