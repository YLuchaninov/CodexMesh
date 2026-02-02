# CodexMesh Advanced Technical Guide

This document provides deep technical details about the inner workings of CodexMesh for contributors and advanced users.

## 1. Hotspot Scoring Algorithm

The `HotspotCalculator` uses a weighted sum of four signals to identify risk centers in the codebase:

### 1.1 Structural (Linter-based)
- **Tool**: [Ruff](https://docs.astral.sh/ruff/)
- **Logic**: For every Python file, the system runs Ruff.
- **Weights**: 
    - `error_weight`: Applied to rules starting with `E` or `F`.
    - `warning_weight`: Applied to all other rule codes.

### 1.2 Semantic (Intent markers)
- **Logic**: Scans files for specific tag patterns using regular expressions.
- **Tags**:
    - `FIXME`: Indicates critical debt (`fixme_weight`).
    - `TODO`: Indicates planned work (`todo_weight`).
    - `HACK`: Indicates fragile code (mapped to `warning_weight`).

### 1.3 Behavioral (Git Churn)
- **Logic**: `git log --oneline --since="N days ago" -- <file>`
- **Formula**: `total_commits * churn_commit_weight`.

### 1.4 Graph (Coupling)
- **Logic**: Aggregates function/class level dependencies into file-level connectivity.
- **In-Degree**: Number of files depending on this file (`import_in_weight`).
- **Out-Degree**: Number of files this file depends on (`import_out_weight`).

### 1.5 Graph (PageRank Centrality)
- **Logic**: Computes PageRank on the file-level dependency graph using `rustworkx`.
- **Weight**: `centrality_weight`.
- **Interpretation**: Identifies "hub" files that have significant structural influence.

### 1.6 Multi-Axis Scoring (Hotspot 2.0)
Specialized scorers analyze file content for specific risk patterns:

- **Logic/Complexity**: Penalizes high line counts (>300), deep nesting (>4 levels), and high control-flow keyword density (if, for, while, etc.).
- **Concurrency**: Detects async/await patterns, threading, locks, and parallelism markers.
- **Risk**: Identifies IO operations, environment variable access, network/DB library usage, and dangerous operations (eval, exec, subprocess).

---

## 2. Advanced Workflow Templating

The `JsonWorkflowRunner` uses a custom templating engine that surpasses simple variable injection.

### 2.1 JSONPath-style Access
- **Dot notation**: `{{ result.data.id }}`
- **List index**: `{{ result.matches[0].name }}`
- **List wildcard**: `{{ result.matches[*].id }}` (Extracts all IDs into a new list)
- **Attribute wildcard**: `{{ result.matches[*].metadata.name }}`

### 2.2 Functional Filters
- `|length`: Returns the size of a list or string.
- `|json`: Parses a JSON string or serializes an object.
- `|join(sep)`: Joins a list into a string.
- `|map(attribute='key')`: Extracts a property from every object in a list.
- `|int` / `|float` / `|bool` / `|str`: Explicit type casting.

### 2.3 Strict Type Preservation
If a template consists *only* of a single expression (e.g., `{{ my_list }}`), the runner preserves the native data type. This allows passing complex objects between tools without serializing/deserializing as strings.

### 2.4 Control Structures (Jinja2)
For complex logic, the engine detects `{% if %}`, `{% for %}`, etc., and automatically uses a **Sandboxed Jinja2 Environment** (if available) to render the template.

---

## 3. Live Sync Mechanism

The `WatcherService` provides real-time graph synchronization using the [watchfiles](https://pypi.org/project/watchfiles/) library.

### 3.1 Debouncing
Rebuilds are debounced (default: 1.0s) to prevent thrashing during rapid file saves or `git checkout` operations.

### 3.2 Automated Filtering
The watcher ignores files based on:
1. `.gitignore` and `.codexignore` rules.
2. File extension compatibility (registered extractors).
3. Explicit exclusion of `__pycache__`, `.git`, and build directories.

---

## 4. Rich Python Extraction

The `PythonTreeSitterExtractor` includes specific logic for identifying project entrypoints without manual configuration.

### 4.1 Main Guard Detection
Functions called inside the `if __name__ == "__main__":` block are automatically flagged with the `is_main_guard` metadata marker, allowing search tools to prioritize them as entrypoints.
