"""
Analysis Service.

Wraps CodexMeshServer components to provide analysis capabilities.
"""

import contextlib
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..analysis.call_graph import CallGraphBuilder
from ..analysis.entrypoints import EntrypointDetector
from ..core.edges import EdgeType
from ..review.markdown_render import MarkdownRenderer

if TYPE_CHECKING:
    from ..api.manager import ProjectManager


class AnalysisService:
    def __init__(self, project_manager: "ProjectManager"):
        self.manager = project_manager

        from .analysis.graph_service import GraphService
        from .analysis.reporting_service import ReportingService
        from .analysis.search_service import SearchService

        self._search = SearchService(self)
        self._graph = GraphService(self)
        self._reporting = ReportingService(self)

    @property
    def config(self):
        return self._get_server().context.config

    @property
    def call_graph_builder(self):
        return CallGraphBuilder(self._get_server())

    @property
    def entrypoint_detector(self):
        return EntrypointDetector(self._get_server())

    def read_span(
        self,
        path: str,
        start_line: int,
        end_line: int,
        context: int = 0,
        max_chars: int | None = None,
    ) -> dict[str, Any]:
        """
        Read a specific span of lines from a file.
        """
        if max_chars is None:
            max_chars = self.config.search.max_read_chars
        try:
            rel_path = self._normalize_to_rel(path)
            if not rel_path:
                return {"error": "Invalid path", "truncated": False}

            abs_path = Path(self._get_server().project_root) / rel_path
            if not abs_path.exists():
                return {"error": f"File not found: {rel_path}", "truncated": False}

            lines = abs_path.read_text(encoding="utf-8").splitlines()
            total_lines = len(lines)

            # 1-based to 0-based
            # Apply context
            s = max(1, start_line - context)
            e = min(total_lines, end_line + context)

            # Slice (0-based exclusive end)
            span_lines = lines[s - 1 : e]
            content = "\n".join(span_lines)

            truncated = False
            if len(content) > max_chars:
                content = content[:max_chars] + "\n... (truncated)"
                truncated = True

            return {
                "path": rel_path,
                "span": {"start": s, "end": e},
                "content": content,
                "total_lines": total_lines,
                "truncated": truncated,
            }
        except Exception as e:
            return {"error": str(e), "truncated": False}

    def _get_server(self):
        if not self.manager.server:
            raise RuntimeError("Project not connected")
        return self.manager.server

    def _parse_edge_types(self, types: list[str] | None) -> list[EdgeType] | None:
        if not types:
            return None
        valid = []
        for t in types:
            try:
                # Case insensitive matching
                t_upper = t.upper()
                if t_upper in EdgeType.__members__:
                    valid.append(EdgeType[t_upper])
            except KeyError:
                pass
        return valid

    def _normalize_to_rel(self, p: str | None) -> str | None:
        """Normalize a path to relative (to project root) if it's absolute.

        Returns None if path is outside project root (security: prevents path traversal).
        """
        if not p:
            return None
        from pathlib import Path

        try:
            pp = Path(p)
            root = Path(self._get_server().project_root).resolve()
            if pp.is_absolute():
                resolved = pp.resolve()
                try:
                    return str(resolved.relative_to(root))
                except ValueError:
                    # Path is outside project root - reject it for security
                    return None
            # Relative path - validate it doesn't escape via ..
            resolved = (root / pp).resolve()
            if root not in resolved.parents and resolved != root:
                return None
            return p
        except Exception:
            return None

    def _node_file_path(self, node) -> str | None:
        """
        Get the file path for any node type, normalized to relative path.

        FileNode has `relative_path`, FunctionNode/ClassNode have `file_path`.
        """
        # FileNode: use relative_path first
        if hasattr(node, "relative_path") and node.relative_path:
            return str(node.relative_path)
        # FunctionNode/ClassNode: use file_path
        if hasattr(node, "file_path") and node.file_path:
            return self._normalize_to_rel(node.file_path)
        # Fallback: try .path (FileNode absolute)
        if hasattr(node, "path") and node.path:
            return self._normalize_to_rel(node.path)
        return None

    # --- Delegated to SearchService ---

    def search_code(self, query: str, limit: int | None = None) -> list[dict[str, Any]]:
        return self._search.search_code(query, limit)

    def search_code_md(self, query: str, limit: int | None = None) -> str:
        return self._search.search_code_md(query, limit)

    def search_text(self, query: str, limit: int = 50) -> list[dict[str, Any]]:
        return self._search.search_text(query, limit)

    def search_text_raw(self, query: str, limit: int = 50) -> dict[str, Any]:
        results = self.search_text(query, limit)
        return {"matches": results, "query": query, "count": len(results)}

    def semantic_search(self, query: str, k: int | None = None) -> list[dict[str, Any]]:
        return self._search.semantic_search(query, k)

    def semantic_search_md(self, query: str, k: int | None = None) -> str:
        return self._search.semantic_search_md(query, k)

    def resolve_symbol(
        self, query: str, prefer_types: list[str] | None = None, limit: int = 5
    ) -> dict[str, Any]:
        return self._search.resolve_symbol(query, prefer_types, limit)

    # --- Delegated to GraphService ---

    def get_subgraph(
        self,
        roots: str | list[str],
        depth: int = 1,
        direction: str = "both",
        edge_types: list[str] | None = None,
        max_nodes: int = 200,
    ) -> dict[str, Any]:
        return self._graph.get_subgraph(roots, depth, direction, edge_types, max_nodes)

    def get_dependency_tree(
        self,
        root_id: str,
        depth: int = 2,
        direction: str = "out",
        edge_types: list[str] | None = None,
    ) -> dict[str, Any]:
        return self._graph.get_dependency_tree(root_id, depth, direction, edge_types)

    def compute_reachable_set(
        self, roots: list[str], edge_types: list[str], max_depth: int = 10, max_nodes: int = 1000
    ) -> dict[str, Any]:
        return self._graph.compute_reachable_set(roots, edge_types, max_depth, max_nodes)

    def find_dead_code(
        self, reachable_ids: list[str], mode: str = "conservative"
    ) -> dict[str, Any]:
        return self._graph.find_dead_code(reachable_ids, mode)

    def build_module_graph(self, max_nodes: int = 100) -> dict[str, Any]:
        return self._graph.build_module_graph(max_nodes)

    # --- Delegated to ReportingService ---

    def get_hotspot(self, path: str = "") -> dict[str, Any]:
        return self._reporting.get_hotspot(path)

    def get_hotspot_md(self, path: str = "") -> str:
        return self._reporting.get_hotspot_md(path)

    def get_repo_map(
        self,
        token_budget: int | None = None,
        include_entrypoints: bool = False,
        include_hotspots: bool = False,
        include_clusters: bool = False,
        format: str = "md",
    ) -> str:
        return self._reporting.get_repo_map(
            token_budget, include_entrypoints, include_hotspots, include_clusters, format
        )

    def detect_entrypoints(self, limit: int = 50) -> dict[str, Any]:
        return self._reporting.detect_entrypoints(limit)

    def get_hotspot_raw(self, path: str = "") -> dict[str, Any]:
        return self.get_hotspot(path)

    def get_repo_map_raw(
        self,
        token_budget: int | None = None,
        include_entrypoints: bool = False,
        include_hotspots: bool = False,
        include_clusters: bool = False,
    ) -> dict[str, Any]:
        m = self._reporting.get_repo_map(
            token_budget=token_budget,
            include_entrypoints=include_entrypoints,
            include_hotspots=include_hotspots,
            include_clusters=include_clusters,
        )
        return {"map": m, "token_count": len(m) / 4}

    def autotune_hotspot_weights(
        self,
        target_rate: float = 0.05,
        percentile: int = 95,
        max_files: int = 800,
        apply: bool = False,
        path_filter: str | None = None,
    ) -> dict[str, Any]:
        """Auto-calibrate hotspot weights."""
        from ..metrics.hotspot_tuner import HotspotWeightCalibrator

        server = self._get_server()
        calibrator = HotspotWeightCalibrator(self.config)

        # 1. Calculate current scores
        # We need actual scores to calibrate.
        # Use existing calculator but ensure we have enough data.
        paths: list[str] = []
        if path_filter:
            # Filter specific folder
            norm_filter = self._normalize_to_rel(path_filter)
            if norm_filter:
                paths = [
                    str(n.relative_path)
                    for n in server.graph_builder.get_all_nodes()
                    if hasattr(n, "relative_path")
                    and n.relative_path
                    and str(n.relative_path).startswith(norm_filter)
                ]
        else:
            # All files
            paths = [
                str(n.relative_path)
                for n in server.graph_builder.get_all_nodes()
                if hasattr(n, "relative_path") and n.relative_path
            ]

        # Limit if too many to avoid massive calc
        if len(paths) > max_files * 2:
            paths = paths[: max_files * 2]

        if not paths:
            return {"error": "No files found to analyze"}

        # Calculate scores
        scores_map = server.hotspot_calculator.calculate_all(paths)
        scores = list(scores_map.values())

        # 2. Run calibration
        result = calibrator.calibrate(
            scores,
            target_hotspot_rate=target_rate,
            percentile=percentile,
            max_files=max_files,
        )

        resp = {
            "recommended": result.recommended,
            "before": result.before,
            "after": result.after,
            "applied": False,
        }

        # 3. Apply if requested
        if apply and result.recommended:
            # Update config object locally
            hc = self.config.hotspot
            rec = result.recommended

            # Apply only real config fields (skip diagnostic keys like "_calibration_info").
            for key, value in rec.items():
                if key.startswith("_"):
                    continue
                if hasattr(hc, key):
                    setattr(hc, key, value)

            # Persist so UI reloads reflect applied values (best-effort).
            with contextlib.suppress(Exception):
                self.manager.save_user_config()

            # Reload calculator with new config
            server.hotspot_calculator.reload_config(self.config)
            resp["applied"] = True

        return resp

    # --- Legacy aliases and composite methods ---

    def entrypoints_list(self, limit: int = 50) -> dict[str, Any]:
        return self.detect_entrypoints(limit)

    def build_call_graph(
        self, roots: list[str], depth: int = 1, direction: str = "both", max_nodes: int = 200
    ) -> dict[str, Any]:
        return self.call_graph_builder.build(roots, depth, direction, max_nodes)

    def callers_of(self, node_id: str, depth: int = 1) -> dict[str, Any]:
        return self.call_graph_builder.callers_of(node_id, depth)

    def callees_of(self, node_id: str, depth: int = 1) -> dict[str, Any]:
        return self.call_graph_builder.callees_of(node_id, depth)

    def find_entrypoint_paths(
        self, target_id: str, limit: int = 20, max_hops: int = 10
    ) -> dict[str, Any]:
        eps = self.detect_entrypoints(limit=limit).get("entrypoints", [])
        ep_ids = [e["id"] for e in eps]
        return self.call_graph_builder.find_entrypoint_paths(target_id, ep_ids, max_hops=max_hops)

    def get_function_info(self, name: str, include_body: bool = False) -> dict[str, Any]:
        """
        Get detailed information about a function, including callers and callees.
        Accepts either an ID or a function name.
        """
        server = self._get_server()

        node = server.graph_builder.get_node_by_id(name)
        func = None
        if node and node.node_type.value in ("function", "method"):
            func = node

        if not func:
            # Fallback to search by name using the delegated search service
            results = self._search.search_code(name, limit=1)
            if results and results[0].get("id"):
                func = server.graph_builder.get_node_by_id(results[0]["id"])

        if not func:
            return {}

        # 1. Basic Info
        info = {
            "id": func.id,
            "name": func.name,
            "file_path": func.file_path,
            "line_start": func.line_start,
            "line_end": func.line_end,
            "signature": getattr(func, "signature", None),
            "docstring": getattr(func, "docstring", None),
            "class_name": getattr(func, "class_name", None),
            "is_method": getattr(func, "is_method", False),
            "callers": [],
            "callees": [],
        }

        # 2. Call Graph (1-hop)
        callers_res = self.callers_of(func.id)
        if callers_res and callers_res.get("callers"):
            info["callers"] = callers_res["callers"][:10]
            info["callers_count"] = callers_res["count"]

        callees_res = self.callees_of(func.id)
        if callees_res and callees_res.get("callees"):
            info["callees"] = callees_res["callees"][:10]
            info["callees_count"] = callees_res["count"]

        # 3. Code & Body
        if include_body:
            body_res = self.read_span(func.file_path, func.line_start, func.line_end)
            info["body"] = body_res.get("content", "")

        # 4. Context (Imports in file)
        # We need to query imports for the *file* containing this function
        # This requires traversing edges from the FileNode.
        # MVP: simplified.

        # 5. Hotspot Score
        hs_report = self.get_hotspot(func.file_path)
        if hs_report and hs_report.get("report"):
            # Find the specific file's hotspot score
            file_hotspot = next(
                (item for item in hs_report["report"] if item.get("file_path") == func.file_path),
                None,
            )
            if file_hotspot:
                info["hotspot_score"] = file_hotspot.get("total", 0.0)
            else:
                info["hotspot_score"] = 0.0
        else:
            info["hotspot_score"] = 0.0

        # 6. Entrypoint Paths (Not computed by default - expensive operation)
        # Client can call find_entrypoint_paths() separately if needed
        info["entrypoint_paths_count"] = None

        return info

    def refresh_index(
        self,
        paths: list[str] | None = None,
        progress_callback: Any = None,
    ) -> dict[str, Any]:
        """
        Refresh the semantic search index.
        Args:
            paths: Optional list of file paths to re-index.
                   If None, re-indexes the entire codebase (auto_index logic).
            progress_callback: Optional callback for progress reporting.
        """
        # Delegate to search service
        return self._search.refresh_index(paths, progress_callback)

    def get_function_info_md(self, name: str) -> str:
        info = self.get_function_info(name)
        return MarkdownRenderer.render_function_info(info, name)

    def get_symbol_info(self, name_or_id: str, include_body: bool = False) -> dict[str, Any]:
        """
        Get detailed symbol information from the graph.
        Accepts either a unique node ID or a name (which will be resolved).
        """
        server = self._get_server()
        node = None

        # 1. Try as ID
        node = server.graph_builder.get_node_by_id(name_or_id)

        # 2. Try as name
        if not node:
            res = self.resolve_symbol(name_or_id, limit=1)
            if res.get("best"):
                node = server.graph_builder.get_node_by_id(res["best"]["id"])

        if not node:
            return {"error": f"Symbol '{name_or_id}' not found", "found": False}

        info = {
            "id": node.id,
            "node_id": node.id,
            "name": node.name,
            "type": node.node_type.value,
            "found": True,
        }

        fp = self._node_file_path(node)
        if fp:
            info["file_path"] = fp

        l_start = getattr(node, "line_start", None)
        l_end = getattr(node, "line_end", None)
        if l_start is not None:
            info["line_start"] = l_start
            info["line_end"] = l_end
            info["span"] = {"start_line": l_start, "end_line": l_end}

        if include_body and fp:
            try:
                abs_file_path = Path(self._get_server().project_root) / fp
                lines = abs_file_path.read_text(encoding="utf-8").splitlines()
                start = l_start - 1 if l_start else 0
                end = l_end if l_end else start + 1
                if 0 <= start < len(lines):
                    info["body"] = "\n".join(lines[start:end])
            except (OSError, AttributeError, IndexError):
                info["body"] = "<error reading body>"

        loc = f"{fp}:{l_start}" if fp and l_start else (fp or "unknown")
        info["summary_md"] = MarkdownRenderer.render_symbol_summary(
            node.name, node.node_type.value, loc
        )

        if node.node_type.value in ("function", "method"):
            callers = self.callers_of(node.id, depth=1)
            callees = self.callees_of(node.id, depth=1)
            info["callers"] = callers["callers"]
            info["callees"] = callees["callees"]
            info["call_stats"] = {"callers": callers["count"], "callees": callees["count"]}

            if hasattr(node, "signature"):
                info["signature"] = node.signature
            if hasattr(node, "class_name"):
                info["class_name"] = node.class_name
            if hasattr(node, "is_method"):
                info["is_method"] = node.is_method

        return info

    def search_code_raw(self, query: str, limit: int | None = None) -> dict[str, Any]:
        results = self.search_code(query, limit)
        return {"matches": results, "query": query}

    def get_all_nodes_raw(self) -> dict[str, Any]:
        """Get all graph nodes (for advanced workflows)."""
        nodes = self._get_server().graph_builder.get_nodes()
        serialized = [n.to_dict() if hasattr(n, "to_dict") else n.__dict__ for n in nodes]
        return {"matches": serialized, "count": len(serialized)}

    def semantic_search_raw(
        self, query: str, k: int = 10, include_docs: bool = False
    ) -> dict[str, Any]:
        """Raw semantic search returning JSON."""
        ft = ["function", "class"]
        if include_docs:
            ft.append("doc_section")

        results = self._get_server().vector_search.search(query, k=k, filter_types=ft)

        # Normalize to API contracts (SemanticResult requires id + name + score; optional snippet/span).
        max_len = getattr(getattr(self.config, "search", None), "snippet_length", 200)
        formatted: list[dict[str, Any]] = []
        for r in results:
            d = r.__dict__ if hasattr(r, "__dict__") else dict(r)

            node_id = d.get("node_id") or d.get("id") or d.get("uid") or "unknown"
            node_id = str(node_id)

            content = d.get("content") or d.get("text") or ""
            snippet = " ".join(str(content).split())
            if isinstance(max_len, int) and len(snippet) > max_len:
                snippet = snippet[:max_len].rstrip() + "…"

            item: dict[str, Any] = {
                "id": node_id,
                "node_id": node_id,  # alias for clients that still expect node_id
                "name": d.get("name") or node_id,
                "file_path": d.get("file_path") or d.get("path"),
                "score": float(d.get("score", 0.0) or 0.0),
                "snippet": snippet if snippet else None,
                "line_start": d.get("line_start") or d.get("start_line"),
                "line_end": d.get("line_end") or d.get("end_line"),
            }

            ls = item.get("line_start")
            le = item.get("line_end")
            if isinstance(ls, int) and isinstance(le, int):
                item["span"] = {"start": ls, "end": le}

            formatted.append(item)

        # Keep both keys for backward compatibility (older clients/tools may read "matches").
        return {"results": formatted, "matches": formatted, "count": len(formatted)}

    def find_path(
        self,
        from_id: str,
        to_id: str,
        edge_types: list[str] | None = None,
        max_hops: int | None = None,
    ) -> dict[str, Any]:
        """Find path between nodes."""
        server = self._get_server()
        et = self._parse_edge_types(edge_types)

        path = server.graph_search.find_path(from_id, to_id, et, max_hops=max_hops)

        if not path:
            return {
                "from": from_id,
                "to": to_id,
                "found": False,
                "length": 0,
                "path_length": 0,
                "path": [],
            }

        # Serialize path nodes
        path_data = []
        for n in path:
            path_data.append({"id": n.id, "name": n.name, "type": n.node_type.value})

        hops = max(0, len(path_data) - 1)
        res = {
            "from": from_id,
            "to": to_id,
            "found": True,
            "length": len(path),
            "path_length": hops,
            "path": path_data,
        }
        if max_hops is not None:
            res["max_hops"] = max_hops
        return res

    def get_docs_map_raw(self) -> dict[str, Any]:
        """Get docs structure."""
        server = self._get_server()
        from ..core.nodes import DocSectionNode

        files: dict[str, list[dict[str, Any]]] = {}
        for n in server.graph_builder.get_all_nodes():
            if isinstance(n, DocSectionNode):
                if n.file_path not in files:
                    files[n.file_path] = []
                files[n.file_path].append(
                    {"id": n.id, "title": n.title, "level": n.level, "line_start": n.line_start}
                )

        # Sort sections by start line
        for fp in files:
            files[fp].sort(key=lambda x: x["line_start"])

        return {"files": files, "count": sum(len(v) for v in files.values())}

    def get_doc_coverage_raw(self, strict_conf: float = 0.7) -> dict[str, Any]:
        """Get documentation coverage metrics."""
        server = self._get_server()
        nodes = server.graph_builder.get_all_nodes()

        total = 0
        covered_strict = 0
        covered_soft = 0

        missing = []
        for n in nodes:
            if n.node_type.value in ("function", "class", "method"):
                total += 1
                has_docstring = bool(getattr(n, "docstring", None))

                if has_docstring:
                    covered_strict += 1
                    covered_soft += 1
                else:
                    missing.append(
                        {
                            "id": n.id,
                            "name": getattr(n, "name", n.id),
                            "type": n.node_type.value,
                            "file_path": getattr(n, "file_path", None),
                        }
                    )

        if total == 0:
            return {
                "coverage_strict": 0.0,
                "coverage_soft": 0.0,
                "total": 0,
                "missing_docs_top": [],
            }

        # Sort by file path and name, limit to top 20
        missing.sort(key=lambda x: (x["file_path"], x["name"]))

        return {
            "coverage_strict": covered_strict / total,
            "coverage_soft": covered_soft / total,
            "total": total,
            "missing_docs_top": missing[:20],
        }

    def semantic_search_docs_raw(self, query: str, k: int = 5) -> dict[str, Any]:
        """Search documentation specifically."""
        server = self._get_server()
        results = server.vector_search.search(query, k=k, filter_types=["doc_section"])

        data = []
        for result in results:
            data.append(
                {
                    "name": result.name,
                    "file_path": result.file_path,
                    "score": result.score,
                    "content": result.content,
                    "node_id": result.node_id,
                }
            )
        return {"matches": data, "count": len(data)}

    def summarize_hotspots(self, report: dict[str, Any], limit: int = 10) -> dict[str, Any]:
        """
        Summarize hotspot report into markdown.

        Args:
            report: The report dictionary returned by get_hotspot()
            limit: Max items to list

        Returns:
            Dictionary containing markdown string
        """
        params = report if isinstance(report, dict) else {"report": report}
        actual_report = params.get("report", [])

        # Robust handling for None
        if actual_report is None:
            actual_report = []

        return {"markdown": MarkdownRenderer.render_hotspot_summary(actual_report, limit)}

    def detect_cycles(
        self,
        scope: str = "module",
        edge_type: str = "imports",
        limit: int = 50,
        max_nodes: int = 200,
    ) -> list[list[str]]:
        """
        Detect cycles in the graph.

        Args:
            scope: Scope of analysis ("module" supported currently)
            edge_type: Filter by edge type (e.g. "imports")
            limit: Max number of cycles to return
            max_nodes: Max nodes to build in the graph

        Returns:
            List of cycles (each cycle is a list of node IDs/names)
        """
        if scope != "module":
            raise ValueError("Only scope=module supported for now")

        # Reuse existing build_module_graph logic
        mg = self.build_module_graph(max_nodes=max_nodes)
        edges = mg.get("edges", [])

        if not edges:
            return []

        # DFS Cycle Detection Logic (ported from routes.py)
        adj: dict[str, list[str]] = {}
        et = edge_type.upper() if edge_type else None

        for e in edges:
            t = str(e.get("type", "")).upper()
            if et and t != et:
                continue
            s, d = e.get("source"), e.get("target")
            if not s or not d:
                continue
            adj.setdefault(s, []).append(d)

        visited: set[str] = set()
        stack: set[str] = set()
        path: list[str] = []
        cycles: list[list[str]] = []

        def dfs(u: str) -> None:
            if len(cycles) >= limit:
                return
            visited.add(u)
            stack.add(u)
            path.append(u)
            for v in adj.get(u, []):
                if len(cycles) >= limit:
                    break
                if v not in visited:
                    dfs(v)
                elif v in stack:
                    try:
                        i = path.index(v)
                        cycles.append(path[i:] + [v])
                    except ValueError:
                        pass
            stack.remove(u)
            path.pop()

        for n in list(adj.keys()):
            if len(cycles) >= limit:
                break
            if n not in visited:
                dfs(n)

        return cycles
