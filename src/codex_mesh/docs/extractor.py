from __future__ import annotations

from hashlib import md5
from pathlib import Path

from ..core.edges import Edge, EdgeType
from ..core.nodes import BaseNode, DocSectionNode, FileNode
from ..extractors.protocols import ExtractionResult, ExtractorContext
from .parser import split_markdown_sections


class MarkdownDocsExtractor:
    language_id = "docs_markdown"
    extensions: tuple[str, ...] = (".md", ".mdx", ".rst", ".adoc")

    def can_extract(self, path: Path) -> bool:
        return path.suffix.lower() in self.extensions

    def extract(
        self, ctx: ExtractorContext, file_node: FileNode, source_text: str
    ) -> ExtractionResult:
        sections = split_markdown_sections(
            source_text, max_chars=ctx.config.get("docs_max_section_chars", 8000)
        )

        nodes: list[BaseNode] = []
        edges = []

        doc_rel = ctx.relative_path

        for s in sections:
            h = md5(s.content.encode("utf-8")).hexdigest()[:12]
            # Extract refs
            # Simple heuristic: find `Code` or [[Link]]
            import re

            refs = []
            # Explicit links [[...]] or @codex(ref=...)
            refs.extend(re.findall(r"\[\[(.+?)\]\]", s.content))
            refs.extend(re.findall(r"@codex\(ref=[\"'](.+?)[\"']\)", s.content))

            n = DocSectionNode.create(
                doc_rel_path=doc_rel,
                title=s.title,
                level=s.level,
                line_start=s.start_line,
                line_end=s.end_line,
                content=s.content,
                content_hash=h,
                refs=refs,
            )
            nodes.append(n)
            edges.append(Edge.create(file_node.id, n.id, EdgeType.CONTAINS))

            # Link section hierarchy if previous exists and level is higher
            # (Simplification: just linear for now or flat, relying on parser structure if implemented later)
            # For now, just File -> Section is enough for search.

        return ExtractionResult(nodes=nodes, edges=edges, pending_imports=[], pending_calls=[])
