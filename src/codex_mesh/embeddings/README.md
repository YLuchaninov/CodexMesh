# CodexMesh Embeddings Module

## Purpose
This module implements vector-based semantic search. It indexes code chunks (functions and classes) using embeddings and stores them in a local LanceDB database for fast semantic retrieval.

## Structure
- `engine.py`: `VectorSearch` class. Handles:
  - Embeddings generation (via `FastEmbed`).
  - Vector storage and retrieval (via `LanceDB`).
  - Code chunking strategy.

## Usage
```python
from codex_mesh.embeddings.engine import VectorSearch

# Initialize (uses db_path from config)
search_engine = VectorSearch(db_path=config.storage.path, config=config)

# Index codebase
search_engine.index_codebase(graph_builder, "/path/to/project")

# Search
results = search_engine.search("how to parse python files", k=5)
for res in results:
    print(f"{res.name}: {res.score}")
```

## Dependencies
- **External**: `lancedb`, `fastembed`
- **Internal**: `codex_mesh.core`, `codex_mesh.config`
