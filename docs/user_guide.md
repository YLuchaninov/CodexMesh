# CodexMesh User Guide

CodexMesh builds a **code graph** and computes **hotspots** to help LLM agents (and humans) navigate and refactor codebases.

## Typical flow

1. Connect a project root
2. Build/refresh graph + hotspots
3. Use search / analysis endpoints (or the Web UI)

## Web UI

Run via Docker Compose (`web` service) or locally (`python -m codex_mesh.web.server`).

The UI is a control plane for:
- Project connect/disconnect
- Graph status + refresh
- Hotspot browsing
- Analysis tools (entrypoints, call paths, etc.)
- **Interactive Chat** with multiple reasoning modes

See the [Web UI Guide](WEB_UI.md) for a detailed walkthrough of chat modes (Quick, Standard, Deep, Autopilot) and settings.

## MCP (Claude Desktop / other clients)

The MCP server runs in stdio mode and exposes tools for:
- project connection
- semantic search
- graph queries
- hotspot metrics & **auto-tuning**
- analysis workflows (**intents**)
- **documentation audit** (staleness, coverage)

See README for integration snippet.
