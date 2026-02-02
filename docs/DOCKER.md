# CodexMesh Docker Guide

CodexMesh ships two containers:
- `web` (HTTP API + UI)
- `mcp` (stdio MCP server; optional profile)

## Build & run

```bash
PROJECT_PATH=/path/to/repo docker compose up --build
```

Open:
- http://localhost:8000

## MCP profile

```bash
docker compose --profile mcp up --build mcp
```

The MCP service is stdio-based. You typically attach to it from an MCP client or via `docker exec`.

## Volumes

- `codexmesh-data` → `/data` (graph DB / index / config)
- `fastembed-cache` → `/home/codexmesh/.cache/fastembed` (embedding model cache)

## Common env vars

- `PROJECT_PATH` – host path to repo to analyze
- `CODEX_MESH_PROJECT_ROOT=/workspace` – container path (read-only mount)
- `CODEX_MESH_STORAGE_PATH=/data` – persistent storage
