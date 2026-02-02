"""
Reporting Service for CodexMesh Analysis.
"""

import logging
from typing import Any

from ...review.markdown_render import MarkdownRenderer

logger = logging.getLogger(__name__)


class ReportingService:
    """Handles hotspot reports and repository map generation."""

    def __init__(self, service):
        self.service = service

    @property
    def config(self):
        return self.service.config

    def get_hotspot(self, path: str = "") -> dict[str, Any]:
        """Get hotspot metrics for the specified scope."""
        server = self.service._get_server()

        if path:
            path = self.service._normalize_to_rel(path) or path

        if path:
            score = server.hotspot_calc.calculate_file_hotspot(path)
            scores = [score]
        else:
            file_paths = [f.relative_path for f in server.graph_builder.get_files()]
            server.hotspot_calc.calculate_all(file_paths)
            scores = server.hotspot_calc.get_high_hotspot_nodes(threshold=0.0)

        logger.info(f"ReportingService.get_hotspot: scope='{path}', found {len(scores)} scores")

        scores.sort(key=lambda s: s.total, reverse=True)
        report = []
        for s in scores:
            report.append(
                {
                    "node_id": s.node_id,
                    "total": s.total,
                    "structural": s.structural,
                    "semantic": s.semantic,
                    "issues": s.issues,
                    "file_path": s.file_path if hasattr(s, "file_path") else None,
                }
            )

        return {"report": report, "summary": f"Analyzed {len(scores)} files."}

    def get_hotspot_md(self, path: str = "") -> str:
        """Get hotspot metrics (Markdown output)."""
        data = self.get_hotspot(path)
        return MarkdownRenderer.render_hotspot_report(data["report"], path)

    def get_repo_map(
        self,
        token_budget: int | None = None,
        include_entrypoints: bool = False,
        include_hotspots: bool = False,
        include_clusters: bool = False,
        format: str = "md",
    ) -> str:
        """Generate repository map."""
        if token_budget is None:
            token_budget = self.config.search.repo_map_token_budget

        server = self.service._get_server()
        if not server.repomap_gen:
            return "RepoMap generator not initialized"

        rmap = server.repomap_gen.generate(
            token_budget=token_budget,
            include_signatures=True,
            include_docstrings=False,
        )

        extra_sections = []

        if include_entrypoints:
            eps = self.service.detect_entrypoints(limit=10).get("entrypoints", [])
            if eps:
                extra_sections.append("\n## Entrypoints")
                for e in eps:
                    extra_sections.append(
                        f"- [{e.get('kind', '?')}] {e['name']} ({e['file_path']})"
                    )

        if include_hotspots:
            hots = self.get_hotspot(path="").get("report", [])
            if hots:
                extra_sections.append("\n## Top Hotspots")
                for h in hots[:5]:
                    extra_sections.append(f"- {h['file_path']} (score: {h['total']:.1f})")

        if include_clusters:
            extra_sections.append("\n## Clusters (Modules)")
            mg = self.service.build_module_graph(max_nodes=10)
            for n in mg.get("nodes", [])[:10]:
                extra_sections.append(f"- {n['name']} ({n.get('size', 0)} files)")

        if extra_sections:
            rmap += "\n" + "\n".join(extra_sections)

        return rmap

    def detect_entrypoints(self, limit: int = 50) -> dict[str, Any]:
        """Detect entrypoints."""
        from ...analysis.entrypoints import EntrypointDetector

        detector = EntrypointDetector(self.service._get_server())
        return detector.detect(limit=limit)
