# Project Architecture & Context: CodexMesh

This document is the **Source of Truth** for the CodexMesh project structure and technical decisions.

## 1. Technology Stack
- **Language:** Python 3.12+ (Strict typing mandatory)
- **Protocol:** [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) for AI interaction using `FastMCP`.
- **Parsing:** `tree-sitter` via `tree-sitter-language-pack`. Achieves feature parity (Symbols, Imports, Calls, Bases) across 15+ languages.

- **Graph Engine:** `rustworkx` for high-performance graph operations.
- **Persistence:**
    - **Vector Storage:** `lancedb` for embedding storage and semantic search.
    - **Metadata/Graph:** `rustworkx` (Snapshot-based) and file system.
- **Embeddings:** `fastembed` (BAAI/bge-small-en-v1.5) for local embedding generation.
- **Validation:** `pydantic v2` for configuration and data schemas.
- **Web UI:** `FastAPI`, `uvicorn`, and `React` for the management dashboard.
- **LLM Agent:** `LangChain` & `Gemini` for integrated code reasoning and intent classification.
- **Workflow Engine:** JSON-based multi-step procedural logic.
- **Testing:** `pytest` with `pytest-asyncio`.
- **Formatting/Linting:** `ruff` (PEP 8 compliance).

## 2. Conventions & Policies
- **Naming Strategy:**
    - **Python:** `snake_case` for variables, functions, and modules. `PascalCase` for classes. `SCREAMING_SNAKE_CASE` for constants.
- **No Global State:** Use explicit contexts and dependency injection. Avoid singletons or mutable global variables.
- **Strict Separation:** Data models (dataclasses/Pydantic) are strictly separated from logic services.
- **Async I/O:** Favor non-blocking I/O for filesystem and network operations.
- **English Only:** All code, comments, documentation, and commit messages must be in English.

## 3. Directory Map
The project is structured into modular components within `src/codex_mesh/`.

| Component | Directory | Responsibility |
| :--- | :--- | :--- |
| **API Layer** | [api/](file:///Users/user/Documents/workspace/researches/CodexMesh/src/codex_mesh/api) | MCP server (FastMCP), tool registration, and project lifecycle management. |
| **Contracts** | [contracts/](file:///Users/user/Documents/workspace/researches/CodexMesh/src/codex_mesh/contracts) | Unified Pydantic data models shared across all layers for consistent serialization. |
| **Core Logic** | [core/](file:///Users/user/Documents/workspace/researches/CodexMesh/src/codex_mesh/core) | Graph abstractions (rustworkx), node/edge definitions, and semantic field engine. |
| **Embeddings** | [embeddings/](file:///Users/user/Documents/workspace/researches/CodexMesh/src/codex_mesh/embeddings) | Interface and implementations for text embedding engines (FastEmbed). |
| **Extractors** | [extractors/](file:///Users/user/Documents/workspace/researches/CodexMesh/src/codex_mesh/extractors) | Decoupled parsers using `tree-sitter` for most languages and `sqlglot` for SQL. |
| **Metrics** | [metrics/](file:///Users/user/Documents/workspace/researches/CodexMesh/src/codex_mesh/metrics) | Scoring algorithms ( estructural complexity, coupling, churn, linting). |
| **Storage** | [storage/](file:///Users/user/Documents/workspace/researches/CodexMesh/src/codex_mesh/storage) | Persistence adapters: LanceDB (vectors) and Git-aware graph snapshots. |
| **Services Layer** | [services/](file:///Users/user/Documents/workspace/researches/CodexMesh/src/codex_mesh/services) | Business logic: `FileSystemService`, `ProjectService`, `AnalysisService`, and `WatcherService`. |
| **Web UI** | [web/](file:///Users/user/Documents/workspace/researches/CodexMesh/src/codex_mesh/web) | FastAPI backend and React frontend management dashboard. |
| **LLM Agent** | [llm/](file:///Users/user/Documents/workspace/researches/CodexMesh/src/codex_mesh/llm) | Reasoning engine and code intent classification using Gemini. |
| **Workflows** | [workflows/](file:///Users/user/Documents/workspace/researches/CodexMesh/src/codex_mesh/workflows) | Procedural JSON-based multi-step reasoning "Intents". |
| **Plugins** | [plugins/](file:///Users/user/Documents/workspace/researches/CodexMesh/src/codex_mesh/plugins) | Runtime-loadable extensions for new languages or metrics. |
| **Review** | [review/](file:///Users/user/Documents/workspace/researches/CodexMesh/src/codex_mesh/review) | Graph rendering (Mermaid) and visual analysis. |


## 4. Key Architectural Patterns
1. **Plugin-Friendly:** The system uses a registry pattern to allow new extractors, metrics, and skills to be added without modifying core logic.
2. **Incremental Updates:** The system is designed to allow delta updates to the graph, reflecting codebase evolution over time.
3. **JSON-Native:** All configurations, workflows, and MCP communications are serialized as clean JSON.
4. **Graph-Based Reasoning:** The core of CodexMesh is a persistent, extensible graph that structures code intent and relationships.

## 5. Deployment Modes
CodexMesh can be deployed in two primary modes:
1. **Headless MCP (Standard):** Pure stdio-based server for agents (Cursor, Claude). No Web UI or LLM dependencies are active.
2. **Control Plane (Extended):** Includes the FastAPI web server, React dashboard, and Gemini-powered Chat system. This mode requires `google-generativeai` and `sqlite3` for persistence.

3. **Live Sync (Development):** Uses the `WatcherService` to monitor project files and automatically rebuild the graph on changes. Ideal for continuous integration during active development.

## 6. Security & Governance
- **Secrets:** Never store or output API keys or tokens. Use environment variables or secure config files.
- **Performance:** Complex graph traversals or large-scale embeddings must be offloaded to worker threads or optimized with async I/O.
