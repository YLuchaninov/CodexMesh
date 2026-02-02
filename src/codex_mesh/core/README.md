# CodexMesh Core Module

## Purpose
This module defines the core data structures and logic for the code dependency graph. It handles the parsing of source code (via Tree-sitter) and the construction of the graph (via rustworkx).

## Structure
- `graph.py`: Contains `CodeGraphBuilder`, responsible for parsing files and building the graph.
- `nodes.py`: Defines graph node types (`FileNode`, `ClassNode`, `FunctionNode`) using Pydantic.
- `edges.py`: Defines edge types (`CONTAINS`, `IMPORTS`, `CALLS`, etc.) and weights.
- `protocols.py`: Defines core interfaces for the system.
- `events.py`: Defines internal events for the event bus.
- `context.py`: Application context dataclass for dependency injection (`AppContext`).

## Usage
The `CodeGraphBuilder` is the primary entry point for this module.

```python
from codex_mesh.core.graph import CodeGraphBuilder

builder = CodeGraphBuilder("/path/to/project")
graph = builder.build()
```

## Dependencies
- **External**: `rustworkx`, `tree-sitter`, `tree-sitter-python`, `pydantic`
- **Internal**: None (Leveled at the bottom of the dependency tree)
