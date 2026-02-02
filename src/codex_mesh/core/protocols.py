"""
Core protocols and abstractions for CodexMesh.

Defines the key interfaces that all subsystems must implement.
Per architecture.md: All major subsystems expose interfaces via ABCs or Protocols.
"""

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

# ========== Schema Version ==========
# Rule: All graph structures and node types must be versioned (advanced.md)

GRAPH_SCHEMA_VERSION = "v1"


# ========== Data Models ==========


@dataclass(frozen=True)
class GraphNode:
    """Immutable graph node per architecture.md spec."""

    id: str
    type: str  # file, function, symbol, intent
    data: dict


@dataclass
class Hotspot:
    """Hotspot score for a code element."""

    node_id: str
    score: float
    reasons: dict[str, float]


@dataclass
class WorkflowResult:
    """Result from workflow execution."""

    success: bool
    logs: list[str]
    changes: dict[str, Any]


# ========== Protocol Definitions ==========


@runtime_checkable
class GraphProvider(Protocol):
    """
    Protocol for graph operations.

    Per architecture.md: Core abstraction for graph access.
    """

    def get_node(self, id: str) -> GraphNode | None:
        """Get a node by its ID."""
        ...

    def neighbors(self, id: str, depth: int = 1) -> list[GraphNode]:
        """Get neighboring nodes up to specified depth."""
        ...

    def add_edge(self, from_id: str, to_id: str, type: str) -> None:
        """Add an edge between two nodes."""
        ...


@runtime_checkable
class EmbeddingEngine(Protocol):
    """
    Protocol for embedding operations.

    Per architecture.md: Core abstraction for vector embeddings.
    """

    def embed(self, text: str) -> list[float]:
        """Generate embedding vector for text."""
        ...

    def similarity(self, v1: list[float], v2: list[float]) -> float:
        """Calculate similarity between two vectors."""
        ...


@runtime_checkable
class HotspotCalculator(Protocol):
    """
    Protocol for hotspot/quality metric calculation.

    Per architecture.md: Core abstraction for code quality scoring.
    """

    def compute(self, node: GraphNode) -> float:
        """Compute hotspot score for a node."""
        ...

    def explain(self, node: GraphNode) -> dict:
        """Explain the hotspot score components."""
        ...


@runtime_checkable
class WorkflowRunner(Protocol):
    """
    Protocol for workflow execution.

    Per architecture.md: Core abstraction for JSON-defined workflows.
    """

    def run(self, workflow_json: dict, context: dict) -> WorkflowResult:
        """Execute a workflow with given context."""
        ...


# ========== Schema Migration ==========


def migrate_graph(schema_from: str, schema_to: str) -> None:
    """
    Migrate graph schema between versions.

    Per advanced.md: Schema versioning enables migrations.
    """
    if schema_from == "v1" and schema_to == "v2":
        # Future: apply structural transformations
        pass
