"""
File System Service.

Handles safe file reading and directory listing.
"""

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..api.manager import ProjectManager


class FileSystemService:
    def __init__(self, project_manager: "ProjectManager"):
        self.manager = project_manager

    @property
    def project_root(self) -> Path:
        if not self.manager.server:
            raise RuntimeError("No project connected")
        return self.manager.server.project_root

    def _validate_path(self, path: str) -> Path:
        """Ensure path is within project root."""
        root = self.project_root
        try:
            target_path = (root / path).resolve()
            target_path.relative_to(root)
            return target_path
        except ValueError as err:
            raise ValueError(f"Path '{path}' is outside project root") from err

    def read_file_span(
        self,
        path: str,
        start_line: int,
        end_line: int,
        context_lines: int = 20,
        max_bytes: int = 200_000,
    ) -> dict:
        """Read a span of lines from a file with context."""
        file_path = self._validate_path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"File '{path}' not found")

        # Check ignore
        from ..core.ignore import IgnoreMatcher

        ignore = IgnoreMatcher.load(self.project_root)
        if ignore.is_ignored(file_path, is_dir=False):
            raise PermissionError(f"File '{path}' is ignored by system configuration")

        with file_path.open("r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        total = len(lines)
        # Normalize lines (1-based)
        start = max(1, start_line)
        end = min(total, end_line)
        if start > end:
            start, end = end, start

        real_start = max(1, start - context_lines)
        real_end = min(total, end + context_lines)

        span_lines = lines[real_start - 1 : real_end]
        content = "".join(span_lines)

        truncated = False
        if len(content.encode("utf-8")) > max_bytes:
            content = content.encode("utf-8")[:max_bytes].decode("utf-8", errors="replace")
            truncated = True

        return {
            "path": path,
            "content": content,
            "base_line": real_start,
            "highlight_start": start,
            "highlight_end": end,
            "truncated": truncated,
        }

    def read_file(self, path: str) -> str:
        """Read file content with line numbers."""
        file_path = self._validate_path(path)

        if not file_path.exists():
            raise FileNotFoundError(f"File '{path}' not found")

        if not file_path.is_file():
            raise ValueError(f"'{path}' is not a file")

        # Check ignore
        from ..core.ignore import IgnoreMatcher

        ignore = IgnoreMatcher.load(self.project_root)
        if ignore.is_ignored(file_path, is_dir=False):
            raise PermissionError(f"File '{path}' is ignored by system configuration")

        content = file_path.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()
        # Add line numbers (1-indexed)
        numbered = [f"{i + 1:4d} | {line}" for i, line in enumerate(lines)]
        return "\n".join(numbered)

    def list_directory(self, path: str = ".", include_ignored: bool = False) -> str:
        """List directory contents."""
        dir_path = self._validate_path(path)

        if not dir_path.exists():
            raise FileNotFoundError(f"Directory '{path}' not found")

        if not dir_path.is_dir():
            raise ValueError(f"'{path}' is not a directory")

        from ..core.ignore import IgnoreMatcher

        ignore = IgnoreMatcher.load(self.project_root)
        # If the directory itself is ignored, we shouldn't list it?
        # But usually we list CONTENTS of it.
        # If the requested dir is ignored, we probably should allow listing if user requested it specifically?
        # But if 'include_ignored' is False, maybe we block?
        # Let's check listing contents filter.

        entries = []
        for item in sorted(dir_path.iterdir()):
            if not include_ignored and ignore.is_ignored(item):
                continue

            rel_path = item.relative_to(self.project_root)
            if item.is_dir():
                entries.append(f"📁 {rel_path}/")
            else:
                try:
                    size = item.stat().st_size
                except OSError:
                    size = None
                if size is None:
                    entries.append(f"📄 {rel_path}")
                else:
                    entries.append(f"📄 {rel_path} ({size} bytes)")

        return "\n".join(entries) if entries else "(empty directory)"

    def read_file_raw(self, path: str, max_bytes: int = 200_000) -> tuple[str, bool]:
        """
        Read file content without line numbers.

        Args:
            path: Relative path to file
            max_bytes: Maximum bytes to read

        Returns:
            Tuple of (content, truncated)
        """
        file_path = self._validate_path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"File '{path}' not found")
        if not file_path.is_file():
            raise ValueError(f"'{path}' is not a file")

        from ..core.ignore import IgnoreMatcher

        ignore = IgnoreMatcher.load(self.project_root)
        if ignore.is_ignored(file_path, is_dir=False):
            raise PermissionError(f"File '{path}' is ignored by system configuration")

        with file_path.open("rb") as f:
            data = f.read(max_bytes + 1)

        truncated = len(data) > max_bytes
        if truncated:
            data = data[:max_bytes]
        return data.decode("utf-8", errors="replace"), truncated

    def list_directory_structured(
        self,
        path: str = ".",
        recursive: bool = False,
        include_hidden: bool = False,
        include_ignored: bool = False,
    ) -> list[dict]:
        """
        List directory contents as structured data.

        Args:
            path: Relative path to directory
            recursive: Include subdirectories recursively
            include_hidden: Include hidden files (starting with .)
            include_ignored: Include ignored files

        Returns:
            List of entry dicts with name, path, type, size
        """
        root = self.project_root
        target = self._validate_path(path)

        if not target.exists() or not target.is_dir():
            raise ValueError(f"'{path}' is not a directory")

        from ..core.ignore import IgnoreMatcher

        ignore = IgnoreMatcher.load(self.project_root)

        def iter_dir(base: Path):
            for p in sorted(base.iterdir(), key=lambda x: (x.is_file(), x.name.lower())):
                if not include_hidden and p.name.startswith("."):
                    continue

                # Check ignore
                if not include_ignored and ignore.is_ignored(p):
                    continue

                rel = str(p.relative_to(root))
                size = None
                if p.is_file():
                    try:
                        size = p.stat().st_size
                    except OSError:
                        size = None
                yield {
                    "name": p.name,
                    "path": rel,
                    "type": "dir" if p.is_dir() else "file",
                    "size": size,
                }
                if recursive and p.is_dir():
                    yield from iter_dir(p)

        return list(iter_dir(target))
