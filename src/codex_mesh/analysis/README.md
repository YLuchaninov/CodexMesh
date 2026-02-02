# CodexMesh Analysis Module

This module provides specialized analysis capabilities on top of the code graph.

## Components

### Call Graph Builder (`call_graph.py`)
Builds and formats subgraphs specifically for call relationship analysis. Supports:
- Subgraph extraction with depth and direction control.
- Mermaid diagram generation.
- Caller/Callee identification.
- Reachability paths from entrypoints.

### Entrypoint Detector (`entrypoints.py`)
Identifies potential entry points in the codebase using:
- Filename heuristics (e.g., `main.py`, `app.py`).
- Function name heuristics (`main`, `start`).
- Framework-specific decorators (`@app.get`, `@click.command`).
- Graph-based reachability scoring.

## Usage

These components are typically orchestrated by the `AnalysisService`.
