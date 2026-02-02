# CodexMesh Review Module

## Purpose
This module provides utilities for visual code review and graph representation. It helps bridge the gap between abstract graph data and human-readable formats like Mermaid.

## Structure
- `graph_render.py`: Logic for converting graph nodes and edges into visual formats.

## Usage
The primary function is `to_mermaid`, used by the `render_graph` tool.

```python
from codex_mesh.review.graph_render import to_mermaid

mermaid_str = to_mermaid(nodes, edges)
```

## Dependencies
- **External**: None
- **Internal**: None (Operates on raw data lists)
