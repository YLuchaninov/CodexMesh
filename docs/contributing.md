# Contributing to CodexMesh

We welcome contributions! Please follow these guidelines to keep the codebase clean and reliable.

## Development Environment

1.  **Install locally**:
    ```bash
    uv sync --all-extras
    ```

2.  **Run Tests**:
    ```bash
    pytest tests/
    ```

## Coding Standards

-   **Type Hints**: Strict typing is required. No `Any` unless absolutely necessary.
-   **Docstrings**: All public classes and functions must have Google-style docstrings.
-   **Language**: English only for code, comments, and documentation.

## Universal Rules (Consolidated)
*Derived from `memory/universal.md`*

1.  **Architecture First**: modifying structure? Check `architecture.md`.
2.  **SOLID**: Single Responsibility Principle.
3.  **No Secrets**: Never commit keys or tokens.
4.  **Async**: Use `async def` for I/O bound operations where possible (though graph building is currently CPU-bound/sync).

## Pull Requests

1.  Describe *why* the change is needed.
2.  Update tests or add new ones.
3.  Ensure `ruff check .` passes.
