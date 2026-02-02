#!/usr/bin/env bash
# Entrypoint for CodexMesh Web (HTTP/UI) service.
set -e

# Set defaults
export CODEX_MESH_STORAGE_PATH="${CODEX_MESH_STORAGE_PATH:-/data}"
export CODEX_MESH_HOST="${CODEX_MESH_HOST:-0.0.0.0}"
export CODEX_MESH_PORT="${CODEX_MESH_PORT:-8000}"

# Ensure data directory exists
mkdir -p "$CODEX_MESH_STORAGE_PATH"

echo "[CodexMesh Web] Starting on ${CODEX_MESH_HOST}:${CODEX_MESH_PORT}"
echo "[CodexMesh Web] Storage: ${CODEX_MESH_STORAGE_PATH}"

exec uvicorn codex_mesh.web.app:app \
    --host "$CODEX_MESH_HOST" \
    --port "$CODEX_MESH_PORT"
