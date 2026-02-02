# syntax=docker/dockerfile:1
# CodexMesh MCP Server Dockerfile

# Stage 1: Builder with uv for fast dependency management
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

WORKDIR /app

# Copy project files
COPY pyproject.toml .
# Added COPY README.md - required by the build system.
COPY README.md .
COPY src/ src/
# NOTE: For fully reproducible builds, generate and commit uv.lock (see docs/REPRODUCIBLE_BUILDS.md).

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --extra web

# Stage 2: Runtime
FROM python:3.11-slim-bookworm AS runtime

# Install system dependencies for tree-sitter
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash codex

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY --from=builder /app/src /app/src

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"
ENV PYTHONUNBUFFERED=1
ENV FASTEMBED_CACHE_PATH="/home/codex/.cache/fastembed"

# Create cache and data directories
RUN mkdir -p /home/codex/.cache/fastembed /data/db \
    && chown -R codex:codex /home/codex /app /data

# Switch to non-root user
USER codex

# Entry point
ENTRYPOINT ["python", "-m", "codex_mesh.api.server"]
