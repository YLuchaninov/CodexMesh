from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import pathspec

DEFAULT_IGNORE = [
    ".git/",
    ".venv/",
    "venv/",
    "__pycache__/",
    "node_modules/",
    ".idea/",
    ".vscode/",
    ".codex_mesh/",
    ".codexmesh/",
    ".cache/",
    ".lancedb/",
    "*.pyc",
    "*.min.js",
    "*.map",
    "dist/",
    "build/",
]

IGNORE_FILES = [".codexignore", ".codexmeshignore", ".gitignore"]


@dataclass(frozen=True)
class IgnoreMatcher:
    root: Path
    spec: pathspec.PathSpec

    @staticmethod
    def _read_lines(p: Path) -> list[str]:
        lines: list[str] = []
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            for raw in content.splitlines():
                s = raw.strip()
                if not s or s.startswith("#"):
                    continue
                lines.append(s)
        except Exception:
            pass  # Fail safe if file cannot be read
        return lines

    @classmethod
    def load(cls, root: Path, extra_patterns: Iterable[str] = ()) -> IgnoreMatcher:
        patterns = list(DEFAULT_IGNORE)

        for fname in IGNORE_FILES:
            fp = root / fname
            if fp.exists() and fp.is_file():
                patterns.extend(cls._read_lines(fp))

        patterns.extend([p.strip() for p in extra_patterns if str(p).strip()])

        spec = pathspec.PathSpec.from_lines("gitignore", patterns)
        return cls(root=root, spec=spec)

    def is_ignored(self, path: Path, *, is_dir: bool | None = None) -> bool:
        """
        Check if a path is ignored.
        Args:
            path: The path to check. Can be absolute or relative to root.
            is_dir: Explicitly state if the path is a directory.
                    If None, it will be inferred from filesystem if possible,
                    but for hypothetical paths (like in tests or before creation),
                    it's better to pass True/False if known.
        """
        try:
            # pathspec expects relative paths
            rel = path.relative_to(self.root).as_posix() if path.is_absolute() else path.as_posix()
        except ValueError:
            # If path is not relative to root (e.g. outside project),
            # we might want to ignore it or handle it.
            # For safety, let's say it's not matched by *project* ignore rules,
            # but usually we shouldn't be asking about external files?
            return False

        if rel == ".":
            return False

        if is_dir is None:
            # Try to infer from filesystem
            try:
                if path.is_dir():
                    is_dir = True
            except OSError:
                pass

        # "gitwildmatch" in pathspec handles trailing slash as directory indicator
        if is_dir is True:
            rel = rel.rstrip("/") + "/"

        return self.spec.match_file(rel)
