# CodexMesh Storage Module

## Purpose
This module handles information retrieval and repository mapping. It implements graph-based search and generates compact context maps ("RepoMaps") for LLM consumption using PageRank.

## Structure
- `repomap.py`: `RepoMapGenerator`. Uses PageRank to identify important code nodes and generates a token-limited summary.
- `search.py`: `GraphSearch`. Implements graph traversal search (find by name, find callers, find references).
- `chat_store.py`: `ChatStore`. Persistent SQLite storage for chat threads and messages (Control Plane memory).

## Usage
```python
from codex_mesh.core.graph import CodeGraphBuilder
from codex_mesh.storage.repomap import RepoMapGenerator
from codex_mesh.storage.search import GraphSearch

builder = CodeGraphBuilder("/path/to/project")
builder.build()

# Generate RepoMap
repomap = RepoMapGenerator(builder)
context = repomap.generate(token_budget=1024)

# Search Graph
search = GraphSearch(builder)
functions = search.search_functions("my_function")
```

## Dependencies
- **External**: `rustworkx`
- **Internal**: `codex_mesh.core`
