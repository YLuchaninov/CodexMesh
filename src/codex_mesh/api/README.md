# CodexMesh API Module

## Purpose
This module implements the Model Context Protocol (MCP) server for CodexMesh. It exposes the core analysis capabilities (graph, search, hotspot metrics) as tools that can be consumed by LLM agents.

## Structure
- `server.py`: Executable entry point for the MCP server.
- `instance.py`: `CodexMeshServer` class. Handles initialization and component orchestration for a specific project.
- `manager.py`: `ProjectManager` class. Manages project switching and server lifecycle.
- `tools.py`: Registry of MCP tools (`read_file`, `search_code`, `get_hotspot`, etc.).

## Usage
This module is the entry point for the application logic. It is typically invoked via the main CLI wrapper.

```python
from codex_mesh.api.server import main

# Run the server
if __name__ == "__main__":
    main()
```

## Dependencies
- **External**: `mcp`, `asyncio`
- **Internal**: 
    - `codex_mesh.core` (Graph construction)
    - `codex_mesh.metrics` (Hotspot analysis)
    - `codex_mesh.storage` (Search and RepoMap)
    - `codex_mesh.embeddings` (Vector search)
