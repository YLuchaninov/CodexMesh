# CodexMesh Contracts Module

## Purpose
This module defines unified Pydantic data models (contracts) shared between MCP server and Web API. These contracts ensure consistent data formats across all API boundaries and provide automatic validation and serialization.

## Responsibilities
- Define request/response models for all API endpoints
- Provide type-safe data transfer objects (DTOs)
- Enable automatic JSON serialization/deserialization
- Enforce data validation rules
- Support both MCP tools and REST API endpoints

## Directory / File Structure
- `__init__.py`: Central export of all contract models
- `analysis.py`: Analysis-related contracts (search, hotspot, repo map, semantic search, symbol resolution)
- `errors.py`: Error response models (`ApiError`, `ErrorBody`, `ErrorEnvelope`)
- `fs.py`: File system contracts (list, read operations)
- `graph.py`: Graph navigation contracts (subgraph, dependency tree, paths, entrypoints, reachability, cycles)
- `intents.py`: Workflow intent contracts (list, execute, trace)
- `status.py`: Server status and connection contracts
- `tools.py`: Tool metadata and registry contracts for UI generation
- `utils.py`: Utility functions for model serialization

## Key Contracts

### Status & Connection
- `StatusSnapshot`: Server state (IDLE, INDEXING, READY, ERROR)
- `ConnectRequest`/`ConnectResponse`: Project connection flow
- `ConnectOptions`: Connection configuration (auto_index, force_reindex)

### File System
- `FSEntry`: File/directory metadata
- `FSListRequest`/`FSListResponse`: Directory listing
- `FSReadRequest`/`FSReadResponse`: File content reading

### Analysis
- `SearchRequest`/`SearchResponse`/`SearchMatch`: Code search by name
- `SemanticRequest`/`SemanticResponse`/`SemanticResult`: Vector-based semantic search
- `RepoMapRequest`/`RepoMapResponse`: Repository context map generation
- `HotspotsRequest`/`HotspotsResponse`/`HotspotItem`: Code quality hotspot analysis
- `ResolveRequest`/`ResolveResponse`/`ResolvedSymbol`: Symbol resolution
- `SymbolRequest`/`SymbolResponse`/`SymbolInfo`: Detailed symbol information

### Graph Navigation
- `NodeDTO`/`EdgeDTO`: Graph node and edge data transfer objects
- `SubgraphRequest`/`SubgraphResponse`: Subgraph extraction
- `DependencyTreeRequest`/`DependencyTreeResponse`/`TreeNode`: Dependency tree structure
- `FindPathRequest`/`FindPathResponse`: Pathfinding between nodes
- `EntrypointsRequest`/`EntrypointsResponse`/`EntrypointItem`: Codebase entry points
- `ReachableSetRequest`/`ReachableSetResponse`: Reachability analysis
- `CyclesResponse`: Circular dependency detection

### Intents (Workflows)
- `IntentItem`: Intent metadata (id, title, description)
- `IntentsListResponse`: Available intents
- `IntentExecuteRequest`/`IntentExecuteResponse`/`IntentExecuteOptions`: Workflow execution
- `ToolTraceStep`: Execution trace for debugging

### Tools Registry
- `ToolMeta`: Tool metadata for UI generation
- `ToolFormField`: Form field definition
- `ToolUIHints`: UI rendering hints
- `ToolsRegistryResponse`: Complete tools registry

## Usage Examples

### In MCP Tools
```python
from codex_mesh.contracts import SearchRequest, SearchResponse

# Tool receives typed request
request = SearchRequest(query="MyClass", limit=10)

# Tool returns typed response
response = SearchResponse(
    query="MyClass",
    results=[SearchMatch(id="...", name="MyClass", type="class", ...)]
)

return response.model_dump()  # Auto-serializes to JSON
```

### In Web API Routes  
```python
from fastapi import APIRouter
from codex_mesh.contracts import HotspotsRequest, HotspotsResponse

router = APIRouter()

@router.post("/analysis/hotspots", response_model=HotspotsResponse)
async def get_hotspots(request: HotspotsRequest):
    # FastAPI auto-validates request body
    # Returns response with automatic serialization
    return HotspotsResponse(...)
```

### Utilities
```python
from codex_mesh.contracts import dump_model

# Safely dump any Pydantic model or dict to JSON-compatible dict
data = dump_model(some_pydantic_model)
```

## Design Principles
- **Shared Contracts**: Same models used by MCP and Web API prevent drift
- **Strict Typing**: All fields are type-annotated for IDE support and validation
- **Defaults**: Sensible defaults reduce boilerplate in common cases
- **Validation**: Pydantic v2 provides automatic validation with helpful error messages
- **Serialization**: Models auto-convert to/from JSON via `.model_dump()` and `.model_validate()`
- **Backward Compatibility**: Use field aliases (e.g., `hotspot_score` with alias `total`) for API evolution

## Dependencies
- **External**: `pydantic` v2
- **Internal**: None (contracts are at the bottom of dependency hierarchy)

## Configuration
No runtime configuration needed. Models are declarative and self-contained.

## Testing
All contract models are tested in `tests/unit/test_contracts.py` for:
- Serialization/deserialization correctness
- Validation rules
- Default values
- Field aliases
