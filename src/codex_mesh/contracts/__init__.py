"""
CodexMesh API Contracts.

Unified Pydantic models shared between MCP and Web API for consistent data formats.
"""

from .analysis import (
    HotspotItem,
    HotspotsRequest,
    HotspotsResponse,
    RepoMapRequest,
    RepoMapResponse,
    ResolvedSymbol,
    ResolveRequest,
    ResolveResponse,
    SearchMatch,
    SearchRequest,
    SearchResponse,
    SemanticRequest,
    SemanticResponse,
    SemanticResult,
    SymbolInfo,
    SymbolRequest,
    SymbolResponse,
)
from .errors import ApiError, ErrorBody, ErrorEnvelope
from .fs import FSEntry, FSListRequest, FSListResponse, FSReadRequest, FSReadResponse
from .graph import (
    CyclesResponse,
    DependencyTreeRequest,
    DependencyTreeResponse,
    EdgeDTO,
    EntrypointItem,
    EntrypointsRequest,
    EntrypointsResponse,
    FindPathRequest,
    FindPathResponse,
    NodeDTO,
    ReachableSetRequest,
    ReachableSetResponse,
    SubgraphRequest,
    SubgraphResponse,
    TreeNode,
)
from .intents import (
    IntentExecuteOptions,
    IntentExecuteRequest,
    IntentExecuteResponse,
    IntentItem,
    IntentsListResponse,
    ToolTraceStep,
)
from .status import ConnectOptions, ConnectRequest, ConnectResponse, StatusSnapshot
from .tools import ToolFormField, ToolMeta, ToolsRegistryResponse, ToolUIHints
from .utils import dump_model

__all__ = [
    # Utils
    "dump_model",
    # Errors
    "ApiError",
    "ErrorBody",
    "ErrorEnvelope",
    # Status
    "StatusSnapshot",
    "ConnectOptions",
    "ConnectRequest",
    "ConnectResponse",
    # FS
    "FSListRequest",
    "FSListResponse",
    "FSReadRequest",
    "FSReadResponse",
    "FSEntry",
    # Analysis
    "SearchRequest",
    "SearchResponse",
    "SearchMatch",
    "SemanticRequest",
    "SemanticResponse",
    "SemanticResult",
    "RepoMapRequest",
    "RepoMapResponse",
    "HotspotsRequest",
    "HotspotsResponse",
    "HotspotItem",
    "ResolveRequest",
    "ResolveResponse",
    "ResolvedSymbol",
    "SymbolRequest",
    "SymbolResponse",
    "SymbolInfo",
    # Graph
    "NodeDTO",
    "EdgeDTO",
    "SubgraphRequest",
    "SubgraphResponse",
    "DependencyTreeRequest",
    "DependencyTreeResponse",
    "TreeNode",
    "FindPathRequest",
    "FindPathResponse",
    "EntrypointsRequest",
    "EntrypointsResponse",
    "EntrypointItem",
    "ReachableSetRequest",
    "ReachableSetResponse",
    "CyclesResponse",
    # Intents
    "IntentItem",
    "IntentsListResponse",
    "ToolTraceStep",
    "IntentExecuteOptions",
    "IntentExecuteRequest",
    "IntentExecuteResponse",
    # Tools
    "ToolFormField",
    "ToolUIHints",
    "ToolMeta",
    "ToolsRegistryResponse",
]
