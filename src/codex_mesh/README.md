# CodexMesh Source Code

This directory contains the core implementation of the CodexMesh system.

## Package Structure

- `api/`: MCP server and project management.
- `contracts/`: Shared data models and serialization utilities.
- `core/`: Graph engine, events, and core abstractions.
- `embeddings/`: Embedding generation implementation.
- `extractors/`: Language-specific parsers.
- `metrics/`: Code quality and hotspot scoring.
- `services/`: Business logic layer.
- `storage/`: Persistence for graphs and vectors.
- `web/`: Management dashboard (FastAPI + React).
- `workflows/`: Intent-based procedural logic.

## Configuration

The system is configured via `config.py` using Pydantic models.

## Entry Point

The main entry point for the system is `main.py` in the root (which calls `codex_mesh.api.server:main`).
