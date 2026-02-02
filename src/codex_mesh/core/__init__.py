"""
CodexMesh Core module.

Contains core abstractions: graph, nodes, edges, protocols, events.
"""

from .edges import EDGE_WEIGHTS, Edge, EdgeType
from .events import Event, EventBus
from .graph import CodeGraphBuilder
from .nodes import BaseNode, ClassNode, FileNode, FunctionNode, NodeType
from .protocols import (
    GRAPH_SCHEMA_VERSION,
    EmbeddingEngine,
    GraphNode,
    GraphProvider,
    Hotspot,
    HotspotCalculator,
    WorkflowResult,
    WorkflowRunner,
)

__all__ = [
    # Schema version
    "GRAPH_SCHEMA_VERSION",
    # Data models
    "GraphNode",
    "Hotspot",
    "WorkflowResult",
    # Protocols
    "GraphProvider",
    "EmbeddingEngine",
    "HotspotCalculator",
    "WorkflowRunner",
    # Events
    "Event",
    "EventBus",
    # Nodes
    "NodeType",
    "BaseNode",
    "FileNode",
    "ClassNode",
    "FunctionNode",
    # Edges
    "EdgeType",
    "Edge",
    "EDGE_WEIGHTS",
    # Graph
    "CodeGraphBuilder",
]
