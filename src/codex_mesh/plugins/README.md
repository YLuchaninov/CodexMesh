# CodexMesh Plugins Module

## Purpose
This module handles runtime loading of extensions and skills. It allows the system to be extended with new extractors, metrics, or workflows via Python entry points.

## Structure
- `loader.py`: Implements the logic to load plugins specified in `CodexMeshConfig`.

## Registration
Plugins register themselves via the `codex_mesh.extractors` entry point group in `pyproject.toml` (or equivalent).
A plugin module must expose a callable (factory or class) that returns an `Extractor` implementation.

Alternatively, `config.skills` can list python modules that expose a `register(registry)` function.

## Example
To enable a skill in your config:
```json
{
  "skills": ["my_custom_plugin"]
}
```
The `my_custom_plugin` module should have:
```python
def register(registry):
    registry.register(MyExtractor())
```
