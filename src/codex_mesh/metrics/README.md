# CodexMesh Metrics Module

## Purpose
This module calculates "hotspot" scores for code elements, which serve as a proxy for technical debt and code quality issues. It combines structural metrics (linter errors), semantic indicators (TODO/FIXME comments), behavioral data (Git churn), and graph-based relationships (coupling).

## Hotspot Scoring
The total score is a weighted sum of four components:

$$
Score_{total} = S_{structural} + S_{semantic} + S_{behavioral} + S_{graph}
$$

1. **Structural** (Code Quality):
   - Based on `ruff` linting.
   - **Errors (E/F)**: High weight (Default: 5.0).
   - **Warnings**: Lower weight (Default: 1.0).

2. **Semantic** (Intent):
   - Based on TODO/FIXME/HACK comments found via Tree-sitter or Regex.
   - **FIXME**: High weight (Default: 4.0).
   - **TODO**: Medium weight (Default: 3.0).
   - **HACK**: Lower weight (Default: 2.0).

3. **Behavioral** (Churn):
   - Based on Git churn (number of commits in the last N days, default 30).
   - Logic: `Count * Weight`.

4. **Graph** (Topology):
   - Based on coupling (in-degree and out-degree).
   - High in-degree = Critical dependency.
   - High out-degree = Complex/Fragile.

## Function-Level Aggregation
Hotspot scores can be aggregated for specific functions by filtering file-level issues (lint, todos) that fall within the function's line range. This allows for granular debt analysis down to individual symbols.

## Example Output

```json
{
  "node_id": "file::src/processing.py",
  "structural": 5.0,  # 1 Error
  "behavioral": 20.0, # 10 Commits * 2.0
  "semantic": 1.0,    # 1 TODO
  "graph": 15.0,      # High coupling
  "total": 41.0,
  "issues": [
    {"type": "lint", "code": "E501", "line": 45},
    {"type": "churn", "count": 10},
    {"type": "coupling", "in": 5, "out": 10}
  ]
}
```

Weights for each component are configurable via the system configuration.

## Structure
- `hotspot.py`: Contains `HotspotCalculator` and `HotspotScore`.
- Runs external `ruff` linter for structural hotspot.
- Uses Tree-sitter or Regex to find semantic markers (TODOs).
- Uses `git log` to calculate behavioral churn.
- Uses the project graph to calculate coupling metrics.

## Usage
```python
from codex_mesh.metrics.hotspot import HotspotCalculator

calculator = HotspotCalculator("/path/to/project")
# Optional: bind graph builder for coupling metrics
# calculator.bind_graph(graph_builder)

score = calculator.calculate_file_hotspot("src/main.py")
print(f"Total hotspot: {score.total}")
print(f"Structural: {score.structural}, Semantic: {score.semantic}")
print(f"Behavioral: {score.behavioral}, Graph: {score.graph}")
```

## Dependencies
- **External**: `ruff` (CLI tool), `tree-sitter`, `tree-sitter-python`, `git`
- **Internal**: `codex_mesh.core`, `codex_mesh.config`
