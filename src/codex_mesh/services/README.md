# CodexMesh Services Module

## Purpose
This module provides high-level service abstractions that wrap the core components and API logic. It adheres to the service layer pattern to keep business logic separate from implementation details.

## Structure
- `analysis_service.py`: High-level code analysis API (searching, graph navigation, hotspots).
- `fs_service.py`: Safe, hardened filesystem operations. Supports encoding-safe reads and large-file streaming.

- `project_service.py`: Manages project lifecycle and connection status.
- `chat_service.py`: High-level chat management (threads, messages, persistence).
- `watcher_service.py`: Live-sync file watcher (debounced background rebuilds).
- `tracing_service.py`: Provides execution tracing for workflows.

## Usage
Services are typically initialized with a `ProjectManager` and used by the API layer or AI agents.

```python
from codex_mesh.services.analysis_service import AnalysisService
from codex_mesh.api.manager import ProjectManager

manager = ProjectManager()
analysis = AnalysisService(manager)

# Use service
results = analysis.search_code("my_function")
```

## Principles
- **No Global State**: All services are instantiated with explicit dependencies.
- **Structured Output**: Public methods return JSON-serializable dictionaries or clean Markdown strings.
- **Fail Fast**: Services validate project connectivity before performing operations.

## Dependencies
- **External**: `langchain_core` (for some service consumers), `mcp`.
- **Internal**: `codex_mesh.core`, `codex_mesh.api.manager`, `codex_mesh.metrics`, `codex_mesh.storage`.
