# CodexMesh – HOWTOUSE

This document is intentionally concise. It exists to make packaging reliable (sdist includes this file)
and to give a quick operational reference.

## Local (uv)

```bash
uv sync
uv run codex-mesh
```

### Web UI

```bash
uv sync --extra web
uv sync --extra web
# To enable ALL LLM features (Gemini, Anthropic, OpenAI, etc):
uv sync --extra web --extra llm-google --extra llm-anthropic --extra llm-openai --extra llm-mistral --extra llm-ollama
uv run python -m codex_mesh.web.server

```

## Docker Compose

```bash
PROJECT_PATH=/path/to/your/repo docker compose up --build
```

Services:
- `web`: HTTP API + UI on port 8000
- `mcp`: stdio MCP server (opt-in profile)

Start MCP:
```bash
docker compose --profile mcp up --build mcp
```

## Environment variables

- `CODEX_MESH_PROJECT_ROOT` – path to mounted repo (e.g. `/workspace`)
- `CODEX_MESH_STORAGE_PATH` – where CodexMesh stores DB/index/config (e.g. `/data`)
- `GOOGLE_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` – optional LLM provider keys
