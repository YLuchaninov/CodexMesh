# CodexMesh

**MCP server for semantic code analysis** - provides LLM agents with structured context about codebases.

## Features

- **Code Graph** - Build dependency graphs using Tree-sitter AST parsing.
- **Hotspot Metrics** - Identify problem areas with linting, TODO detection, **PageRank centrality**, and **Multi-Axis analysis** (Logic, Concurrency, Risk).
- **Auto-Tuner** - Automatically calibrate hotspot weights to your repository's statistical profile (`autotune_hotspots`).
- **Live Updates** - Automatic background graph and hotspot updates when code changes (semantic index requires manual refresh via `index_refresh`).
- **Semantic Search:** RAG-based code search to find functionality by meaning.
- **Workflow Engine:** Intent-based multi-step reasoning system (e.g., "Plan Refactoring").
- **Web UI:** Central "Control Plane" for project management and visualization.

> **📚 Learn More**: Check out the [User Guide](docs/user_guide.md).
- **Integrated Reviewer:** Gemini-powered agent using LangChain for code assistance.

## Reproducible builds

To ensure reproducible builds, use the `uv.lock` file:

```bash
uv sync --locked
```

## Quick Start

### Using uv (recommended)

```bash
# Install dependencies
uv sync

# (Optional) install Web UI deps
uv sync --extra web

# Run the server (starts in IDLE mode)
uv run codex-mesh

# Run the Web UI
# Note: If you build the React frontend (src/codex_mesh/web/frontend), copy its output to src/codex_mesh/web/static/dist
# Otherwise the built-in fallback page (src/codex_mesh/web/static/index.html) will be served.
uv run python -m codex_mesh.web.server
```

### Using Docker

```bash
# Build image
docker build -t codex-mesh .

# Run (optional: mount projects)
docker-compose up
```

> **🐳 Docker Guide**: See [DOCKER.md](docs/DOCKER.md) for advanced configuration and project mounting.

### Claude Desktop Integration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "codex-mesh": {
      "command": "uv",
      "args": ["--directory", "/path/to/CodexMesh", "run", "codex-mesh"]
    }
  }
}
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `connect_to_project(path, ...)` | Connect to a project dynamically (control indexing, watcher) |
| `project_switch(project_id)` | Switch active project context (simulated) |
| `index_refresh(paths)` | Refresh the semantic search index (currently performs full re-index) |
| `get_server_status()` | Check "busy" status, progress, and current project |
| `get_status_snapshot()` | Get structured status object (JSON) |
| `read_file(path)` | Read file content from project root |
| `list_directory(path)` | List directory contents |
| `read_span(path, start, end, ...)` | Read a specific range of lines with optional context |
| `search_code(query, limit)` | Search for code elements by name (lexical) |
| `search_code_raw(query, limit)` | Raw JSON search for code elements |
| `semantic_search(query, k)` | Vector-based semantic search |
| `semantic_search_raw(query, k)` | Raw JSON semantic search |
| `get_hotspot(path)` | Get code quality metrics (Ruff + TODO + Churn + Structural + Logic + Risk) |
| `autotune_hotspots(apply, ...)` | Auto-calibrate hotspot weights based on project distribution |
| `get_repo_map(token_budget, ...)` | Generate repository map for context |
| `get_function_info(name, ...)` | Get detailed function info including callers |
| `callers_of(node_id, depth)` | Find functions that call the given node |
| `callees_of(node_id, depth)` | Find functions called by the given node |
| `get_subgraph(roots, depth, ...)` | Get subgraph centered at nodes |
| `get_dependency_tree(root_id, ...)` | Get dependency tree structure |
| `find_dependency_path(from, to)` | Find path between two code nodes |
| `find_path(from, to, max_hops)` | Find path with explicit hop limit |
| `resolve_symbol(query, types)` | Resolve symbol name to internal ID |
| `detect_entrypoints(limit)` | Automatically detect project entrypoints (CLI, Web, etc.) |
| `entrypoints_list(limit)` | Alias for detect_entrypoints |
| `build_call_graph(roots, depth)` | Build an explicit call graph from roots |
| `find_entrypoint_paths(id)` | Find paths from entrypoints to a target node |
| `compute_reachable_set(roots, ...)`| Compute set of nodes reachable from roots |
| `render_graph(format, nodes, edges)`| Render graph to Mermaid format |
| `list_tools_detailed()` | List all available intent tools with schemas |
| `search_tools(query)` | Search for intent tools by name or description |
| `list_intents()` | List available reasoning intents (workflows) |
| `execute_intent(id, args)` | Execute a multi-step reasoning workflow |

## Architecture

```
src/codex_mesh/
├── api/           # MCP server, tool registry and project manager
├── contracts/     # Unified Pydantic models (Schema)
├── core/          # Code graph (rustworkx) and node/edge definitions
├── embeddings/    # Vector embedding interface (FastEmbed)
├── extractors/    # Multi-language AST parsers (Tree-sitter)
├── llm/           # Reasoning engine and agent logic (LangChain)
├── metrics/       # Scoring algorithms (Hotspots, Coupling)
├── services/      # Business logic (FS, Analysis, Project, Watcher)
├── storage/       # Persistence (LanceDB + Git-aware snapshots)
├── web/           # FastAPI backend & React frontend dashboard
└── workflows/     # Intent-based procedural logic (JSON)
```

## Development

```bash
# Install with dev dependencies
uv sync --all-extras

# Run tests
uv run pytest

# Lint
uv run ruff check src/

# Test with MCP Inspector
uv run mcp dev src/codex_mesh/api/server.py
```

## License

Polyform Noncommercial License 1.0.0
