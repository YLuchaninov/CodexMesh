#!/usr/bin/env bash
# Entrypoint for CodexMesh MCP (stdio) service.
set -e

# Set defaults
export CODEX_MESH_STORAGE_PATH="${CODEX_MESH_STORAGE_PATH:-/data}"

# Ensure data directory exists
mkdir -p "$CODEX_MESH_STORAGE_PATH"

echo "[CodexMesh MCP] Starting stdio server" >&2
echo "[CodexMesh MCP] Storage: ${CODEX_MESH_STORAGE_PATH}" >&2

exec python -m codex_mesh.api.server
