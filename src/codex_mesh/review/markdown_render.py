"""
Markdown rendering utilities for CodexMesh.
Decouples presentation logic from analysis services.
"""

from typing import Any


class MarkdownRenderer:
    """Centralized renderer for analysis results."""

    @staticmethod
    def render_search_results(results_data: list[dict[str, Any]], query: str) -> str:
        """Render name-based search results."""
        if not results_data:
            return f"No results found for '{query}'"

        lines = [f"Found {len(results_data)} results for '{query}':", ""]

        for item in results_data:
            ntype = item.get("type")
            if ntype == "function":
                icon = "⚡" if not item.get("is_method") else "🔹"
                location = f"{item['file_path']}:{item['line_start']}"
                sig = item.get("signature") or f"def {item['name']}()"
                lines.append(f"{icon} {sig}")
                lines.append(f"   📍 {location}")
            elif ntype == "class":
                location = f"{item['file_path']}:{item['line_start']}"
                lines.append(f"🔷 class {item['name']}")
                lines.append(f"   📍 {location}")
            else:
                lines.append(f"• {item['name']}")
            lines.append("")

        return "\n".join(lines).strip()

    @staticmethod
    def render_semantic_search_results(results: list[dict[str, Any]], query: str) -> str:
        """Render semantic search results."""
        if not results:
            return f"No semantic matches found for '{query}'"

        lines = [f"Semantic search results for '{query}':", ""]

        for result in results:
            score_pct = int(result.get("score", 0.0) * 100)
            lines.append(f"📌 {result['name']} (relevance: {score_pct}%)")
            lines.append(f"   📍 {result['file_path']}:{result['line_start']}-{result['line_end']}")
            lines.append("   ```python")
            content = result.get("content", "")
            content_lines = content.splitlines()[:5]
            for line in content_lines:
                lines.append(f"   {line}")
            if len(content.splitlines()) > 5:
                lines.append("   # ...")
            lines.append("   ```")
            lines.append("")

        return "\n".join(lines).strip()

    @staticmethod
    def render_hotspot_report(scores: list[dict[str, Any]], path: str = "") -> str:
        """Render high-hotspot report."""
        if not scores:
            return "No hotspot data available"

        # Check if all scores are 0
        if not any(s.get("total", 0.0) > 0 for s in scores):
            return "✅ No hotspot issues found - code looks good!"

        lines = ["# Hotspot Report", ""]
        if path:
            lines[0] = f"# Hotspot Report for {path}"

        top_scores = scores[:10]
        for score in top_scores:
            if score.get("total", 0.0) == 0:
                continue
            lines.append(f"## {score['node_id']}")
            lines.append(f"- Structural: {score.get('structural', 0.0):.1f}")
            lines.append(f"- Semantic: {score.get('semantic', 0.0):.1f}")
            lines.append(f"- **Total: {score.get('total', 0.0):.1f}**")

            issues = score.get("issues", [])
            if issues:
                lines.append("- Issues:")
                for issue in issues[:5]:
                    msg = issue.get("message", "Unknown issue")[:60]
                    lines.append(f"  - [{issue.get('type', 'issue')}] {msg}")
            lines.append("")

        return "\n".join(lines).strip()

    @staticmethod
    def render_function_info(info: dict[str, Any], name: str) -> str:
        """Render detailed function information."""
        if not info or not info.get("found", True):  # get_function_info returns {} if not found
            return f"Function '{name}' not found"

        lines = [f"# Function: {info['name']}", ""]
        lines.append(
            f"**Location:** {info.get('file_path')}:{info.get('line_start')}-{info.get('line_end')}"
        )

        if info.get("is_method") and info.get("class_name"):
            lines.append(f"**Class:** {info['class_name']}")

        if info.get("signature"):
            lines.append(f"**Signature:** `{info['signature']}`")

        if info.get("docstring"):
            lines.append(f"**Docstring:** {info['docstring']}")

        callers = info.get("callers")
        if callers:
            lines.append("\n**Called by:**")
            for caller in callers[:5]:
                lines.append(f"- {caller['name']}")

        return "\n".join(lines).strip()

    @staticmethod
    def render_dead_code_candidates(candidates: list[Any]) -> str:
        """Render dead code candidates."""
        if not candidates:
            return "No dead code candidates found."

        lines = []
        for n in candidates[:20]:
            # Expecting dict with name, file_path, line_start (from find_dead_code)
            # Or node objects if refactored.
            name = n.get("name") if isinstance(n, dict) else getattr(n, "name", "unknown")
            fp = n.get("file_path") if isinstance(n, dict) else getattr(n, "file_path", "unknown")
            ls = n.get("line_start") if isinstance(n, dict) else getattr(n, "line_start", "?")
            lines.append(f"- `{name}` in {fp}:{ls}")

        if len(candidates) > 20:
            lines.append(f"... and {len(candidates) - 20} more.")

        return "\n".join(lines).strip()

    @staticmethod
    def render_symbol_summary(name: str, ntype: str, location: str) -> str:
        """Render short symbol summary."""
        return f"**{name}** ({ntype})\nLocation: `{location}`"

    @staticmethod
    def render_hotspot_summary(report: list[dict[str, Any]], limit: int = 10) -> str:
        """Render simple hotspot summary list."""
        if not report:
            return "No hotspots found."

        lines = []
        for r in report[:limit]:
            lines.append(
                f"- **{r['node_id']}**: Score {r['total']:.2f} (Issues: {len(r.get('issues', []))})"
            )

        return "\n".join(lines).strip()
