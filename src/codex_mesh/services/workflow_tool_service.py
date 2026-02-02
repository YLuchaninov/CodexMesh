"""
Workflow Tool Service.

Contains the implementation of tools used within JSON workflows.
Decouples workflow logic from the RuntimeFactory and AnalysisService.
"""

import logging
from typing import Any

from ..services.analysis_service import AnalysisService
from ..services.tracing_service import TracingService

logger = logging.getLogger(__name__)


class WorkflowToolService:
    """Service providing helper logic for workflow tool execution."""

    def __init__(self, analysis: AnalysisService, tracing: TracingService):
        self.analysis = analysis
        self.tracing = tracing

    def resolve_seeds(
        self,
        semantic_hits: list[dict] | None = None,
        lex_hits: list[dict] | None = None,
        # aliases from intents:
        semantic_matches: list[dict] | None = None,
        lex_matches: list[dict] | None = None,
        max_seeds: int = 5,
        **_,
    ) -> dict[str, Any]:
        # Accept both naming variants
        if semantic_hits is None:
            semantic_hits = semantic_matches
        if lex_hits is None:
            lex_hits = lex_matches

        candidates: dict[str, dict[str, Any]] = {}  # id -> {obj, score}

        if semantic_hits:
            hits = (
                semantic_hits.get("matches", [])
                if isinstance(semantic_hits, dict)
                else semantic_hits
            )
            for h in hits:
                nid = h.get("id") or h.get("node_id")
                if nid:
                    data = dict(h)
                    data["id"] = nid
                    candidates[nid] = {"data": data, "score": float(h.get("score", 0.5))}

        if lex_hits:
            hits = lex_hits.get("matches", []) if isinstance(lex_hits, dict) else lex_hits
            for h in hits:
                nid = h.get("id") or h.get("node_id")
                if not nid:
                    continue
                if nid in candidates:
                    candidates[nid]["score"] += 0.5
                else:
                    data = dict(h)
                    data["id"] = nid
                    candidates[nid] = {"data": data, "score": 0.5}

        sorted_cands = sorted(candidates.values(), key=lambda x: x["score"], reverse=True)
        top = [c["data"].get("id") for c in sorted_cands[:max_seeds] if c.get("data", {}).get("id")]
        # IMPORTANT: keep backward/forward compatibility for intents
        return {"ids": top, "root_ids": top, "count": len(top)}

    def rank_subgraph_nodes(
        self, nodes: list[dict] | None = None, edges: list[dict] | None = None, top_k: int = 10
    ) -> dict[str, Any]:
        nodes = nodes or []
        edges = edges or []
        degrees = {n["id"]: 0 for n in nodes}
        for e in edges:
            s, t = e.get("source"), e.get("target")
            if s in degrees:
                degrees[s] += 1
            if t in degrees:
                degrees[t] += 1

        sorted_nodes = sorted(nodes, key=lambda n: degrees.get(n["id"], 0), reverse=True)
        top = sorted_nodes[:top_k]

        md_lines = []
        for n in top:
            d = degrees.get(n["id"], 0)
            md_lines.append(f"- **{n['name']}** ({n['type']}) - Degree: {d}")

        return {"markdown_list": "\n".join(md_lines), "top_n": top}

    def pick_best_entrypoint(
        self, query: str = "", entrypoints: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        if not entrypoints:
            return {"best": None}
        eps = entrypoints.get("entrypoints", [])
        if not eps:
            return {"best": None}

        # Heuristic: name match
        if query:
            for ep in eps:
                if query.lower() in ep["name"].lower():
                    return {"best": ep}
        return {"best": eps[0]}

    def hotspot_in_scope(self, nodes: list[dict] | None = None) -> dict[str, Any]:
        if not nodes:
            return {"report": [], "summary_md": "No scope."}
        hs = self.analysis.get_hotspot()
        report = hs.get("report", [])

        node_ids = {n["id"] for n in nodes}
        filtered = [r for r in report if r["node_id"] in node_ids]

        lines = []
        for r in filtered[:10]:
            lines.append(f"- **{r['node_id']}**: Score {r['total']:.2f}")

        return {"report": filtered, "summary_md": "\n".join(lines)}

    def join_hotspot_scores(self, ranked: list[dict], hotspots: list[dict]) -> dict[str, Any]:
        hs_map = {
            h["node_id"]: h
            for h in (hotspots if isinstance(hotspots, list) else hotspots.get("report", []))
        }
        joined = []
        for n in ranked:
            h = hs_map.get(n["id"])
            item = n.copy()
            if h:
                item["hotspot_score"] = h["total"]
                item["issues"] = h["issues"]
            joined.append(item)
        joined.sort(key=lambda x: x.get("hotspot_score", -1), reverse=True)

        lines = []
        for item in joined:
            score = item.get("hotspot_score", 0)
            icon = "🔥" if score > 5 else "⚠️" if score > 0 else "✅"
            lines.append(f"- {icon} **{item['name']}**: {score:.2f}")

        return {"top_markdown_list": "\n".join(lines), "joined": joined}

    def detect_cycles(
        self, edges: list[dict] | None = None, edge_types: list[str] | None = None
    ) -> dict[str, Any]:
        if not edges:
            return {"summary_md": "No edges."}
        adj: dict[str, list[str]] = {}
        for e in edges:
            # Filter types if needed
            if edge_types and e.get("type", "unknown").upper() not in [
                t.upper() for t in edge_types
            ]:
                continue

            s, t = e["source"], e["target"]
            if s not in adj:
                adj[s] = []
            adj[s].append(t)

        visited = set()
        rec_stack = set()
        cycles = []

        def dfs(u, path):
            visited.add(u)
            rec_stack.add(u)
            path.append(u)

            if u in adj:
                for v in adj[u]:
                    if v not in visited:
                        dfs(v, path)
                    elif v in rec_stack:
                        try:
                            idx = path.index(v)
                            cycles.append(path[idx:] + [v])
                        except ValueError:
                            pass

            rec_stack.remove(u)
            path.pop()

        for node in list(adj.keys()):
            if node not in visited:
                dfs(node, [])

        lines = []
        if cycles:
            lines.append(f"Found {len(cycles)} cycles:")
            for c in cycles[:5]:
                lines.append(f"- {' -> '.join(c)}")
        else:
            lines.append("No cycles detected.")
        return {"summary_md": "\n".join(lines), "cycles": cycles}

    def summarize_hotspots(self, report: dict[str, Any], limit: int = 10) -> dict[str, Any]:
        params = report if isinstance(report, dict) else {"report": report}
        actual_report = params.get("report", [])
        lines = []
        for r in actual_report[:limit]:
            lines.append(
                f"- **{r['node_id']}**: Score {r['total']:.2f} (Issues: {len(r.get('issues', []))})"
            )
        return {"markdown": "\n".join(lines) if lines else "No hotspots found."}

    def path_to_subgraph(self, path_result: dict[str, Any]) -> dict[str, Any]:
        if "path" in path_result:
            # Reconstruct edges from sequential path nodes
            nodes = path_result["path"]
            edges = []
            for i in range(len(nodes) - 1):
                edges.append(
                    {"source": nodes[i]["id"], "target": nodes[i + 1]["id"], "type": "path"}
                )
            return {"nodes": nodes, "edges": edges}
        return {"nodes": [], "edges": []}

    def render_graph(
        self,
        nodes: list[dict] | None = None,
        edges: list[dict] | None = None,
        format: str = "mermaid",
    ) -> dict[str, Any]:
        from ..review.graph_render import to_mermaid

        return {"content": to_mermaid(nodes or [], edges or [])}

    def dead_code_candidates(
        self, reachable_ids: list[str] | None = None, mode: str = "conservative"
    ) -> dict[str, Any]:
        if reachable_ids is None:
            return {"likely_dead_md": "Reachability analysis required."}
        return self.analysis.find_dead_code(reachable_ids, mode)

    def build_module_graph(self, max_nodes: int = 100) -> dict[str, Any]:
        return self.analysis.build_module_graph(max_nodes)

    def check_layering_rules(
        self, ruleset: str = "default", module_graph: dict | None = None
    ) -> dict[str, Any]:
        if not module_graph:
            return {"markdown": "No graph provided."}

        edges = module_graph.get("edges", [])
        violations = []
        for e in edges:
            s, t = e["source"], e["target"]
            if "core" in s and "web" in t:
                violations.append(f"Core module '{s}' depends on Web module '{t}'")

        if violations:
            return {
                "markdown": "Layering violations:\n" + "\n".join([f"- {v}" for v in violations])
            }
        return {"markdown": "No obvious layering violations found."}

    def rank_impact(
        self,
        target_id: str | None = None,
        up_nodes: list | None = None,
        up_edges: list | None = None,
    ) -> dict[str, Any]:
        if not up_nodes:
            return {"markdown_list": "No impact data."}
        lines = []
        for n in up_nodes[:15]:
            lines.append(f"- **{n.get('name', n.get('id'))}**")
        return {"markdown_list": "\n".join(lines)}

    def summarize_security_hits(self, matches: list[dict] | None = None) -> dict[str, Any]:
        if not matches:
            return {"markdown": "No security risks found."}
        lines = []
        for m in matches[:10]:
            lines.append(
                f"- ⚠️ **{m.get('name', 'match')}**: {m.get('content', '').strip()[:60]}..."
            )
        return {"markdown": "\n".join(lines)}

    def trace_start(
        self, id: str | None = None, trace_id: str | None = None, scenario: str | None = None, **_
    ) -> dict[str, Any]:
        tid = self.tracing.start_trace(trace_id or id or scenario)
        if scenario:
            self.tracing.log_step("scenario", "trace_start", input_data={"scenario": scenario})
        return {"id": tid, "status": "started", "scenario": scenario}

    def trace_wait(
        self,
        duration_sec: float = 0.0,
        duration: float | None = None,
        trace_id: str | None = None,
        **_,
    ) -> dict[str, Any]:
        dur = duration_sec if duration is None else duration
        if trace_id:
            if trace_id not in getattr(self.tracing, "_traces", {}):
                self.tracing.start_trace(trace_id)
            self.tracing._active_trace = trace_id
        self.tracing.log_step("wait", "trace_wait", duration=dur)
        return {
            "id": trace_id or getattr(self.tracing, "_active_trace", None),
            "status": "done",
            "duration_sec": dur,
        }

    def trace_stop(self, id: str | None = None, trace_id: str | None = None, **_) -> dict[str, Any]:
        tid = trace_id or id
        self.tracing.stop_trace(tid)
        return {"id": tid, "status": "stopped"}

    def trace_to_subgraph(
        self,
        id: str | None = None,
        trace_id: str | None = None,
        trace: dict[str, Any] | None = None,
        **_,
    ) -> dict[str, Any]:
        tid = trace_id or id or (trace.get("id") if isinstance(trace, dict) else None)
        return self.tracing.get_trace_subgraph(tid)
