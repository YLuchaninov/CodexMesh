# CodexMesh Workflows Module

## Purpose
This module implements a JSON-defined workflow engine. It allows orchestrating multiple tool calls and logic steps (branching, composition, etc.) to handle complex user intents. These workflows are used by the `ReviewerAgent` and the MCP tools to provide high-level analysis.

## Structure
- `engine/`: Core logic for workflow execution.
    - `runner.py`: `JsonWorkflowRunner` that executes workflow steps.
    - `registry.py`: `IntentRegistry` that loads and manages intents from JSON files.
    - `router.py`: `IntentRouter` that maps user queries to intents.
    - `input_prep.py`: Prepares and validates input for workflows based on user queries and heuristics.
    - `templating.py`: Simple string interpolation for workflow parameters.
- `definitions/`: Directory containing JSON definitions for supported user intents.
    - `intent.codebase_overview.json`: High-level summary of the project.
    - `intent.refactor_guidance.json`: Detailed steps for refactoring a specific component.
    - `intent.change_plan.json`: Identification of files to modify for a new feature.
    - `intent.dead_code.json`: Detect unused functions or symbols.
    - `intent.change_impact.json`: Analyze what might break if a symbol is changed.
    - `intent.architecture_consistency.json`: Check code against architectural rules.
    - `intent.security_review.json`: Basic security scan using graph patterns.
    - `intent.execution_graph_static.json`: Trace static call paths.
    - `intent.symbol_lookup.json`: Deep search for symbol definitions and references.
- `runtime.py`: `RuntimeFactory` for creating pre-configured workflow runners with all available tools.

## Usage
Workflows are typically triggered via the `ReviewerAgent` or the `execute_intent` MCP tool.

```python
from codex_mesh.workflows import IntentRegistry, IntentRouter
from codex_mesh.workflows.runtime import RuntimeFactory

# Register intents
registry = IntentRegistry("path/to/intents")
registry.load()

# Create runner
runner = RuntimeFactory.create(analysis_service, registry)

# Run a workflow
workflow = registry.get("my_intent").workflow
result = runner.run(workflow, context={"input": {"symbol": "MyClass"}})
```

## Workflow Schema
Workflows are lists of steps. Each step has an `action`:
- `tool`: Call an MCP tool.
- `branch`: Conditional execution of sub-steps.
- `compose`: Create a formatted string using context variables.
- `set`: Store a value in the context.
- `return`: End workflow and return a value.
- `vis`: Specifically for graph visualization.

## Advanced Templating
The workflow engine supports a rich templating system based on mustache-style `{{ expression }}`:
- **Path Access**: `{{ foo.bar }}` or `{{ items[0].id }}`.
- **Mapping**: `{{ items[*].id }}` returns a list of IDs.
- **Filters**: `{{ val | length }}`, `{{ items | join(',') }}`, `{{ list | map(attribute='name') }}`.
- **Type Preservation**: If an input is exactly `{{ expr }}`, the result retains its native type (list, int, bool) instead of being cast to string.

## Dependencies
- **External**: `jinja2` (for advanced templating, if enabled), `fastembed` (for routing).
- **Internal**: `codex_mesh.services`, `codex_mesh.api.manager`.
