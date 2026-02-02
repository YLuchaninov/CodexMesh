"""
Entrypoint Detection Module.
Identifies potential entry points in the codebase using heuristics, graph signals, and AST markers.
"""

from typing import Any


class EntrypointDetector:
    def __init__(self, server):
        self.server = server

    def detect(self, limit: int = 50) -> dict[str, Any]:
        """
        Detect entrypoints using multiple strategies.
        """
        entries: list[dict[str, Any]] = []
        found_ids: set[str] = set()

        # Strategy 1: Known file names (High confidence)
        self._detect_by_filename(entries, found_ids)

        # Strategy 2: Known function names (Medium confidence)
        self._detect_by_funcname(entries, found_ids)

        # Strategy 3: Framework Decorators (High/Medium confidence)
        self._detect_by_decorators(entries, found_ids)

        # 4) Score and Sort with Reachability
        # Weighting: signals (detectors) = 0.7, reachability = 0.3
        for e in entries:
            # Basic reachability score: how many nodes can be reached using CALLS edges?
            # For large graphs, we might limit the depth.
            # Use graph_search.compute_reachability which returns (ids, count)
            try:
                from ..core.edges import EdgeType

                _, node_count = self.server.graph_search.compute_reachability(
                    [e["id"]], max_depth=5, edge_types=[EdgeType.CALLS]
                )
            except Exception:
                node_count = 0

            reach_score = min(1.0, node_count / 100.0)  # normalize: 100+ nodes = 1.0
            orig_score = e.get("score", 0.5)
            e["score"] = (orig_score * 0.7) + (reach_score * 0.3)
            e["reasons"].append(f"Reachability: {node_count} nodes in call tree (depth 5)")

        entries.sort(key=lambda x: x.get("score", 0), reverse=True)

        return {"entrypoints": entries[:limit], "count": len(entries)}

    def _detect_by_filename(self, entries: list[dict], found_ids: set[str]):
        """Find files like main.py, app.py, etc."""
        # Weighted targets
        targets = {
            "main.py": 0.95,
            "app.py": 0.9,
            "cli.py": 0.9,
            "manage.py": 0.9,
            "server.py": 0.9,
            "index.js": 0.9,
            "server.js": 0.9,
            "app.ts": 0.9,
            "main.go": 0.95,
            "main.rs": 0.95,
        }

        # We search primarily by exact filename match in the graph
        # Since graph search by name is fuzzy or exact, we iterate file nodes if possible or search
        # Iterating all files is O(N_files), usually fast enough (<10k files).
        files = self.server.graph_builder.get_files()

        for f in files:
            if f.id in found_ids:
                continue

            basename = f.relative_path.split("/")[-1].lower()
            if basename in targets:
                entries.append(
                    {
                        "id": f.id,
                        "type": "file",
                        "kind": "file",
                        "category": "cli",
                        "name": f.name,
                        "file_path": f.relative_path,
                        "span": {"start_line": 0, "end_line": 0},
                        "score": targets[basename],
                        "reasons": [f"Filename '{basename}' is a common entrypoint"],
                    }
                )
                found_ids.add(f.id)

    def _detect_by_funcname(self, entries: list[dict], found_ids: set[str]):
        """Find functions like main, run, start."""
        # We can scan all functions or search. Scanning is more robust against fuzzy duplicates.
        functions = self.server.graph_builder.get_functions()

        targets = {"main": 0.9, "run": 0.6, "start": 0.6, "cli": 0.8, "execute": 0.5, "serve": 0.6}

        for fn in functions:
            if fn.id in found_ids:
                continue

            name_lower = fn.name.lower()
            if name_lower in targets:
                # Reduce score for methods unless static/main
                score = targets[name_lower]
                if fn.is_method:
                    score *= 0.5

                # Boost if inside main.py/app.py
                if fn.file_path and any(
                    x in fn.file_path.lower() for x in ["main.py", "app.py", "cli.py"]
                ):
                    score = min(0.95, score + 0.3)

                entries.append(
                    {
                        "id": fn.id,
                        "type": "function",
                        "kind": "function",
                        "category": "logic",
                        "name": fn.name,
                        "file_path": fn.file_path,
                        "span": {"start_line": fn.line_start, "end_line": fn.line_end},
                        "score": score,
                        "reasons": [f"Function name '{fn.name}' suggests entrypoint"],
                    }
                )
                found_ids.add(fn.id)

    def _detect_by_decorators(self, entries: list[dict], found_ids: set[str]):
        """Detect framework entrypoints via decorators."""
        nodes = self.server.graph_builder.get_functions()  # + class methods included

        # Mapping decorator substring -> score
        framework_sigs = {
            # CLI
            "@app.command": 0.95,  # Typer/Click
            "@click.command": 0.95,  # Click
            "@click.group": 0.9,
            "main_guard": 0.98,  # Special synthetic marker for if __name__ == "__main__"
            # Web/API
            "@app.get": 0.9,  # FastAPI/Flask
            "@app.post": 0.9,
            "@app.put": 0.9,
            "@app.delete": 0.9,
            "@app.route": 0.9,
            "@router.get": 0.85,
            "@router.post": 0.85,
            "@router.route": 0.85,
            "@RestController": 0.9,  # Java Spring
            "@GetMapping": 0.9,
            "@PostMapping": 0.9,
            # Workers/Tasks
            "@task": 0.7,  # Celery/prefect
            "@celery.task": 0.8,
            "@cron": 0.8,
            "@scheduler": 0.8,
            "@on_message": 0.8,  # Messaging
        }

        for n in nodes:
            if n.id in found_ids:
                continue

            matched = []
            max_score = 0.0

            # Check explicit decorators
            if n.decorators:
                for d in n.decorators:
                    d_lower = d.lower()
                    for sig, score in framework_sigs.items():
                        if sig.startswith("@") and sig in d_lower:
                            matched.append(d)
                            max_score = max(max_score, score)

            # Check synthetic markers (e.g. from treesitter extractor identifying main guard or hard entrypoints)
            if hasattr(n, "meta") and n.meta:
                if n.meta.get("is_main_guard"):
                    matched.append("if __name__ == '__main__'")
                    max_score = max(max_score, framework_sigs["main_guard"])
                elif n.meta.get("is_entrypoint"):
                    matched.append("Language Entry Point (main)")
                    max_score = max(max_score, 0.98)

            if matched:
                entries.append(
                    {
                        "id": n.id,
                        "type": "function",
                        "kind": "function",
                        "category": "web"
                        if any(x in str(matched).lower() for x in ["get", "post", "route"])
                        else "cli",
                        "name": n.name,
                        "file_path": n.file_path,
                        "span": {"start_line": n.line_start, "end_line": n.line_end},
                        "score": max_score,
                        "reasons": [f"Entrypoint markers: {', '.join(matched)}"],
                    }
                )
                found_ids.add(n.id)
