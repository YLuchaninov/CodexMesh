# Reproducible builds (uv.lock)

Right now the repo does not include `uv.lock`, so Docker builds resolve dependencies dynamically.
For stable, reproducible builds you should commit a lockfile.

## Generate lockfile

```bash
uv lock
git add uv.lock
git commit -m "Add uv.lock for reproducible builds"
```

## Enforce lock usage

After `uv.lock` is committed you can switch Docker installs to frozen mode:

```bash
uv sync --frozen --no-dev --extra web
```

Same for MCP builds (`--extra llm-core --extra llm-google`).

## Why it matters

- Prevents “works yesterday, breaks today” due to dependency drift
- Stabilizes tree-sitter bindings behavior across environments
- Makes hotspot/scoring results more reproducible
