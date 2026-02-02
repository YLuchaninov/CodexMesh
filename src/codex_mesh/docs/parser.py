from __future__ import annotations

import re
from dataclasses import dataclass

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


@dataclass
class DocSection:
    title: str
    level: int
    start_line: int
    end_line: int
    content: str


def split_markdown_sections(text: str, max_chars: int = 4000) -> list[DocSection]:
    lines = text.splitlines()
    headings: list[tuple[int, int, str]] = []  # (line_idx, level, title)

    for i, line in enumerate(lines):
        m = HEADING_RE.match(line)
        if m:
            level = len(m.group(1))
            title = m.group(2).strip()
            headings.append((i, level, title))

    if not headings:
        # Single section fallback
        content = "\n".join(lines)[:max_chars]
        return [
            DocSection(
                title="Document", level=1, start_line=1, end_line=len(lines), content=content
            )
        ]

    sections: list[DocSection] = []

    for idx, (h_line, level, title) in enumerate(headings):
        start = h_line
        end = headings[idx + 1][0] - 1 if idx + 1 < len(headings) else len(lines) - 1

        chunk = "\n".join(lines[start : end + 1]).strip()
        if len(chunk) > max_chars:
            chunk = chunk[:max_chars] + "\n<!-- truncated -->"

        sections.append(
            DocSection(
                title=title,
                level=level,
                start_line=start + 1,
                end_line=end + 1,
                content=chunk,
            )
        )

    return sections
