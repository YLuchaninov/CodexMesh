"""
Graph contracts.

Models for graph operations: subgraph, dependency tree, find path, entrypoints, reachable set, cycles.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field

Direction = Literal["in", "out", "both"]


class NodeDTO(BaseModel):
    """Graph node data transfer object."""

    id: str
    name: str
    type: str
    file_path: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class EdgeDTO(BaseModel):
    """Graph edge data transfer object."""

    source: str
    target: str
    type: str
    weight: float | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


# --- Subgraph ---


class SubgraphRequest(BaseModel):
    """Subgraph extraction request."""

    roots: list[str] = Field(..., description="Root node IDs")
    depth: int = Field(1, ge=0, le=50)
    direction: Direction = "both"
    edge_types: list[str] | None = None
    max_nodes: int = Field(200, ge=10, le=5000)


class SubgraphResponse(BaseModel):
    """Subgraph response."""

    nodes: list[NodeDTO] = Field(default_factory=list)
    edges: list[EdgeDTO] = Field(default_factory=list)
    mermaid: str | None = None
    stats: dict[str, Any] = Field(default_factory=dict)


# --- Dependency Tree ---


class TreeNode(BaseModel):
    """Recursive tree node."""

    node: NodeDTO
    children: list["TreeNode"] = Field(default_factory=list)


# Rebuild for self-reference (Pydantic v2)
TreeNode.model_rebuild()


class DependencyTreeRequest(BaseModel):
    """Dependency tree request."""

    root_id: str
    depth: int = Field(2, ge=0, le=50)
    direction: Direction = "out"
    edge_types: list[str] | None = None


class DependencyTreeResponse(BaseModel):
    """Dependency tree response."""

    root: str
    tree: str | dict[str, Any] | None = None  # Tree structure or text representation
    nodes: list[NodeDTO] = Field(default_factory=list)
    edges: list[EdgeDTO] = Field(default_factory=list)
    direction: str = "out"
    stats: dict[str, Any] = Field(default_factory=dict)


# --- Find Path ---


class FindPathRequest(BaseModel):
    """Find path between nodes request."""

    source_id: str
    target_id: str
    edge_types: list[str] | None = None
    max_hops: int | None = Field(None, ge=1, le=200)


class FindPathResponse(BaseModel):
    """Find path response."""

    found: bool = False
    path: list[NodeDTO] = Field(default_factory=list)
    path_ids: list[str] = Field(default_factory=list)
    edges: list[EdgeDTO] = Field(default_factory=list)
    length: int = 0
    stats: dict[str, Any] = Field(default_factory=dict)


# --- Entrypoints ---


class EntrypointsRequest(BaseModel):
    """Entrypoints list request."""

    kind: str = Field("all", description="all|file|function")
    query: str = ""
    limit: int = Field(50, ge=1, le=500)


class EntrypointItem(BaseModel):
    """An entrypoint item."""

    id: str
    name: str
    type: str
    kind: str | None = None
    file_path: str | None = None
    line_start: int | None = None
    line_end: int | None = None


class EntrypointsResponse(BaseModel):
    """Entrypoints response."""

    entrypoints: list[EntrypointItem] = Field(default_factory=list)
    count: int = 0


# --- Reachable Set ---


class ReachableSetRequest(BaseModel):
    """Reachable set computation request."""

    roots: list[str]
    edge_types: list[str]
    max_depth: int = Field(10, ge=0, le=200)
    max_nodes: int = Field(1000, ge=10, le=20000)


class ReachableSetResponse(BaseModel):
    """Reachable set response."""

    reachable_ids: list[str] = Field(default_factory=list)
    count: int = 0


# --- Cycles ---


class CyclesResponse(BaseModel):
    """Cycle detection response."""

    scope: str = "module"
    edge_type: str = "imports"
    cycles: list[list[str]] = Field(default_factory=list)
    cycle_count: int = 0
