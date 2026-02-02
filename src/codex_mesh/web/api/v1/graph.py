"""
Graph API Router.
"""

from fastapi import APIRouter, Depends

from ....contracts.errors import ApiError
from ....contracts.graph import (
    CyclesResponse,
    DependencyTreeRequest,
    DependencyTreeResponse,
    EntrypointsRequest,
    EntrypointsResponse,
    FindPathRequest,
    FindPathResponse,
    ReachableSetRequest,
    ReachableSetResponse,
    SubgraphRequest,
    SubgraphResponse,
)
from ....services.analysis_service import AnalysisService
from ....services.project_service import ProjectService
from ...dependencies import get_analysis_service, get_project_service

router = APIRouter(prefix="/graph", tags=["graph"])


def ensure_ready(ps: ProjectService) -> None:
    ps.ensure_ready()


@router.post("/subgraph", response_model=SubgraphResponse)
async def graph_subgraph(
    req: SubgraphRequest,
    ps: ProjectService = Depends(get_project_service),
    an: AnalysisService = Depends(get_analysis_service),
):
    """Get subgraph from roots."""
    ensure_ready(ps)
    try:
        result = an.get_subgraph(
            req.roots,
            depth=req.depth,
            direction=req.direction,
            edge_types=req.edge_types,
            max_nodes=req.max_nodes,
        )
        return SubgraphResponse(
            nodes=result.get("nodes", []),
            edges=result.get("edges", []),
            mermaid=result.get("mermaid"),
            stats=result.get("stats", {}),
        )
    except Exception as e:
        raise ApiError(400, "BadRequest", str(e)) from e


@router.post("/dependency-tree", response_model=DependencyTreeResponse)
async def graph_dependency_tree(
    req: DependencyTreeRequest,
    ps: ProjectService = Depends(get_project_service),
    an: AnalysisService = Depends(get_analysis_service),
):
    """Get dependency tree."""
    ensure_ready(ps)
    try:
        result = an.get_dependency_tree(
            req.root_id,
            depth=req.depth,
            direction=req.direction,
            edge_types=req.edge_types,
        )
        return DependencyTreeResponse(
            root=result.get("root", req.root_id),
            tree=result.get("tree"),
            nodes=result.get("nodes", []),
            edges=result.get("edges", []),
            direction=result.get("direction", req.direction),
        )
    except Exception as e:
        raise ApiError(400, "BadRequest", str(e)) from e


@router.post("/find-path", response_model=FindPathResponse)
async def graph_find_path(
    req: FindPathRequest,
    ps: ProjectService = Depends(get_project_service),
    an: AnalysisService = Depends(get_analysis_service),
):
    """Find path between nodes."""
    ensure_ready(ps)
    try:
        result = an.find_path(
            req.source_id, req.target_id, edge_types=req.edge_types, max_hops=req.max_hops
        )
        path = result.get("path", [])
        path_ids = [n["id"] if isinstance(n, dict) else n.id for n in path]
        return FindPathResponse(
            found=result.get("found", False),
            path=path,
            path_ids=path_ids,
            length=result.get("length", 0),
        )
    except Exception as e:
        raise ApiError(400, "BadRequest", str(e)) from e


@router.post("/entrypoints", response_model=EntrypointsResponse)
async def graph_entrypoints(
    req: EntrypointsRequest,
    ps: ProjectService = Depends(get_project_service),
    an: AnalysisService = Depends(get_analysis_service),
):
    """List entrypoints."""
    ensure_ready(ps)
    try:
        result = an.entrypoints_list(limit=max(req.limit, 50))
        eps = result.get("entrypoints", [])
        kind = req.kind.lower()
        if kind in ("file", "function"):
            eps = [e for e in eps if str(e.get("kind", e.get("type", ""))).lower() == kind]
        if req.query:
            q = req.query.lower()
            eps = [
                e
                for e in eps
                if q in str(e.get("name", "")).lower() or q in str(e.get("file_path", "")).lower()
            ]
        return EntrypointsResponse(entrypoints=eps[: req.limit], count=len(eps))
    except Exception as e:
        raise ApiError(400, "BadRequest", str(e)) from e


@router.post("/reachable-set", response_model=ReachableSetResponse)
async def graph_reachable(
    req: ReachableSetRequest,
    ps: ProjectService = Depends(get_project_service),
    an: AnalysisService = Depends(get_analysis_service),
):
    """Compute reachable set."""
    ensure_ready(ps)
    try:
        result = an.compute_reachable_set(
            req.roots, req.edge_types, max_depth=req.max_depth, max_nodes=req.max_nodes
        )
        ids = result.get("reachable_ids", [])
        return ReachableSetResponse(reachable_ids=ids, count=len(ids))
    except Exception as e:
        raise ApiError(400, "BadRequest", str(e)) from e


@router.get("/cycles", response_model=CyclesResponse)
async def graph_cycles(
    scope: str = "module",
    edge_type: str = "imports",
    limit: int = 50,
    max_nodes: int = 200,
    ps: ProjectService = Depends(get_project_service),
    an: AnalysisService = Depends(get_analysis_service),
):
    """Detect cycles in module graph."""
    ensure_ready(ps)
    try:
        if scope != "module":
            raise ApiError(400, "BadRequest", "Only scope=module supported for now")

        cycles = an.detect_cycles(
            scope=scope, edge_type=edge_type, limit=limit, max_nodes=max_nodes
        )

        return CyclesResponse(
            scope=scope, edge_type=edge_type, cycles=cycles, cycle_count=len(cycles)
        )
    except Exception as e:
        raise ApiError(400, "BadRequest", str(e)) from e
