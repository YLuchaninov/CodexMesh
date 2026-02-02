from __future__ import annotations

import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Protocol


class ImportResolver(Protocol):
    def resolve(self, project_root: Path, file_path: Path, import_path: str) -> list[str]:
        """Return candidate file paths (relative to project_root). Empty => unknown/external."""
        ...


# ---------------------------
# Utilities / path index
# ---------------------------

_DEFAULT_SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    ".pytest_cache",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    "out",
    ".venv",
    "venv",
    ".mypy_cache",
    ".ruff_cache",
    ".next",
}


@dataclass(frozen=True)
class PathIndex:
    root: Path
    by_rel: dict[str, str]  # rel -> rel (normalized)
    by_basename: dict[str, list[str]]  # "Foo.java" -> ["a/b/Foo.java", ...]

    def exists(self, rel: str) -> bool:
        return rel in self.by_rel

    def find_by_basename(self, basename: str) -> list[str]:
        return self.by_basename.get(basename, [])


@lru_cache(maxsize=16)
def build_path_index(root: str) -> PathIndex:
    r = Path(root).resolve()
    by_rel: dict[str, str] = {}
    by_basename: dict[str, list[str]] = {}

    for dirpath, dirnames, filenames in os.walk(r):
        dp = Path(dirpath)
        dirnames[:] = [d for d in dirnames if d not in _DEFAULT_SKIP_DIRS]

        for fn in filenames:
            rel = str((dp / fn).relative_to(r)).replace("\\", "/")
            by_rel[rel] = rel
            by_basename.setdefault(fn, []).append(rel)

    return PathIndex(root=r, by_rel=by_rel, by_basename=by_basename)


def _rel_if_exists(project_root: Path, p: Path) -> str | None:
    try:
        rel = str(p.resolve().relative_to(project_root.resolve())).replace("\\", "/")
        if rel:
            return rel
    except Exception:
        return None
    return None


# ---------------------------
# JS / TS
# ---------------------------


class JSImportResolver:
    def resolve(self, project_root: Path, file_path: Path, import_path: str) -> list[str]:
        spec = import_path.strip()

        # External packages: "react", "@scope/pkg" => ignore
        if not spec.startswith((".", "/")):
            return []

        # Resolve relative to file directory
        base = file_path.parent
        idx = build_path_index(str(project_root))

        # Candidate targets:
        #   ./x  -> ./x.ts, ./x.tsx, ./x.js, ./x.jsx, ./x.mjs, ./x.cjs, ./x.d.ts
        #   ./x/ -> ./x/index.*
        exts = [".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".d.ts", ".mts", ".cts"]
        candidates: list[str] = []

        try:
            raw = (base / spec).resolve()
        except OSError:
            return []

        # If spec already ends with extension
        if raw.suffix:
            rel = _rel_if_exists(project_root, raw)
            if rel and idx.exists(rel):
                return [rel]
            return []

        # Try file.* and index.*
        for ext in exts:
            p = Path(str(raw) + ext)
            rel = _rel_if_exists(project_root, p)
            if rel and idx.exists(rel):
                candidates.append(rel)

        # Directory index
        for ext in exts:
            p = raw / ("index" + ext)
            rel = _rel_if_exists(project_root, p)
            if rel and idx.exists(rel):
                candidates.append(rel)

        # Dedup preserve order
        seen = set()
        out = []
        for c in candidates:
            if c not in seen:
                seen.add(c)
                out.append(c)
        return out


# ---------------------------
# Java / Kotlin
# ---------------------------


class JavaKotlinImportResolver:
    _SRC_ROOTS = [
        "src/main/java",
        "src/test/java",
        "src/main/kotlin",
        "src/test/kotlin",
        "app/src/main/java",
        "app/src/test/java",
        "app/src/main/kotlin",
        "app/src/test/kotlin",
    ]

    def resolve(self, project_root: Path, file_path: Path, import_path: str) -> list[str]:
        name = import_path.strip()

        # simple static cleanup
        if name.startswith("static "):
            name = name[len("static ") :].strip()

        # Wildcards: a.b.*
        wildcard = name.endswith(".*")
        pkg = name[:-2] if wildcard else name

        idx = build_path_index(str(project_root))

        src_roots = [project_root / p for p in self._SRC_ROOTS if (project_root / p).exists()]
        if not src_roots:
            # Fallback to project root (monorepos / custom layouts)
            src_roots = [project_root]

        # For non-wildcard imports, map a.b.C -> a/b/C.java|kt
        candidates: list[str] = []
        if not wildcard:
            path_part = pkg.replace(".", "/")
            for sr in src_roots:
                for ext in (".java", ".kt", ".kts"):
                    p = sr / (path_part + ext)
                    rel = _rel_if_exists(project_root, p)
                    if rel and idx.exists(rel):
                        candidates.append(rel)

                # Kotlin often places top-level declarations in file named not exactly class;
                # try basename fallback (C.kt) under the package dir
                leaf = path_part.split("/")[-1]
                # Also try finding ANY file with that basename
                for ext in (".kt", ".kts", ".java"):
                    for rel in idx.find_by_basename(leaf + ext):
                        # Verify package structure (heuristic)
                        if rel.endswith(path_part + ext):
                            candidates.append(rel)
        else:
            # a.b.* -> link to any file in that package dir (best effort)
            dir_part = pkg.replace(".", "/")
            for sr in src_roots:
                d = sr / dir_part
                if not d.exists():
                    continue
                # attach all java/kt files under this dir (non-recursive)
                for ext in (".java", ".kt", ".kts"):
                    prefix = str(d.relative_to(project_root)).replace("\\", "/") + "/"
                    for rel in idx.by_rel:
                        if rel.startswith(prefix) and rel.endswith(ext):
                            candidates.append(rel)

        # Dedup
        seen = set()
        out = []
        for c in candidates:
            if c not in seen:
                seen.add(c)
                out.append(c)
        return out


# ---------------------------
# Go
# ---------------------------


class GoImportResolver:
    def resolve(self, project_root: Path, file_path: Path, import_path: str) -> list[str]:
        idx = build_path_index(str(project_root))
        module = _read_go_module(project_root)

        imp_path = import_path.strip().strip('"')

        if not imp_path:
            return []

        # Stdlib or external => ignore
        if imp_path.startswith("./") or imp_path.startswith("../"):
            # Relative import (discouraged but exists in some tests/codebase)
            rel_dir = (file_path.parent / imp_path).relative_to(project_root).as_posix()
        elif module and imp_path.startswith(module + "/"):
            rel_dir = imp_path[len(module) + 1 :]
        elif module and imp_path == module:
            rel_dir = ""
        else:
            return []

        # Map to directory under project root
        target_dir = (project_root / rel_dir).resolve()
        rel_target_dir = _rel_if_exists(project_root, target_dir)
        if not rel_target_dir:
            return []

        # Connect to all .go files in that directory (excluding _test.go by default)
        pref = rel_target_dir.rstrip("/") + "/"
        candidates = [
            rel
            for rel in idx.by_rel
            if rel.startswith(pref) and rel.endswith(".go") and not rel.endswith("_test.go")
        ]
        return candidates


def _read_go_module(project_root: Path) -> str | None:
    p = project_root / "go.mod"
    try:
        if p.exists():
            for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if line.startswith("module "):
                    return line.split(" ", 1)[1].strip()
    except Exception:
        return None
    return None


# ---------------------------
# Rust
# ---------------------------


class RustImportResolver:
    def resolve(self, project_root: Path, file_path: Path, import_path: str) -> list[str]:
        path = import_path.strip()

        # Strip braces: use a::b::{c,d}; -> a::b
        path = re.sub(r"\{.*\}", "", path).strip()
        path = path.rstrip(":")

        # Normalize leading crate/self/super
        # NOTE: treesitter might pass just "net" from "mod net;"
        # If it's single identifier, we treat as submodule or sibling.

        if path.startswith("crate::"):
            mod_path = path[len("crate::") :]
            base = project_root / "src"  # Simplified assumption
        elif path.startswith("self::"):
            mod_path = path[len("self::") :]
            base = file_path.parent
        elif path.startswith("super::"):
            mod_path = path[len("super::") :]
            base = file_path.parent.parent
        else:
            # "net" or "std::io"
            # If no ::, assumes sibling module
            if "::" not in path:
                mod_path = path
                base = file_path.parent
            else:
                # "foo::bar" -> could be crate root or external
                # We assume crate root for now if we can match it
                # But actually, "use foo::bar" often means "use crate::foo::bar" if foo is a module at root
                # OR external crate.
                # Default to external/unknown for now unless we find it in src?
                # Actually, let's try assuming it is under src
                mod_path = path
                base = project_root / "src"

        mod_path = mod_path.strip(":")
        segs = [s for s in mod_path.split("::") if s]
        if not segs:
            return []

        idx = build_path_index(str(project_root))
        rels: list[str] = []

        # Logic:
        # mod foo -> foo.rs OR foo/mod.rs

        # Candidate 1: Full path as file
        p1 = base / "/".join(segs)
        p1_rs = p1.with_suffix(".rs")
        rel1 = _rel_if_exists(project_root, p1_rs)
        if rel1 and idx.exists(rel1):
            rels.append(rel1)

        # Candidate 2: Full path as dir -> mod.rs
        p2 = p1 / "mod.rs"
        rel2 = _rel_if_exists(project_root, p2)
        if rel2 and idx.exists(rel2):
            rels.append(rel2)

        # Also try dropping last segment if it's an item import?
        # e.g. use net::http::Request -> net/http.rs
        if len(segs) > 1:
            p3 = base / "/".join(segs[:-1])
            p3_rs = p3.with_suffix(".rs")
            rel3 = _rel_if_exists(project_root, p3_rs)
            if rel3 and idx.exists(rel3):
                rels.append(rel3)

            p4 = p3 / "mod.rs"
            rel4 = _rel_if_exists(project_root, p4)
            if rel4 and idx.exists(rel4):
                rels.append(rel4)

        # Dedup
        seen = set()
        out = []
        for c in rels:
            if c not in seen:
                seen.add(c)
                out.append(c)
        return out


# ---------------------------
# C / C++ includes
# ---------------------------


class CIncludeResolver:
    def resolve(self, project_root: Path, file_path: Path, import_path: str) -> list[str]:
        # treesitter query gets regex captures from:
        # (preproc_include path: (string_literal) @source) -> "stdio.h" (with quotes)
        # (preproc_include (string_literal) @source) -> <stdio.h> (maybe with angles if we captured textual content?)

        # treesitter_query.py strips quotes.
        # But if it was <stdio.h>, treesitter might capture node text including <>.

        q = import_path.strip()
        is_angle = q.startswith("<")
        name = q[1:-1] if is_angle and q.endswith(">") else q

        idx = build_path_index(str(project_root))

        candidates: list[str] = []
        # Priority
        if is_angle:
            search_dirs = [
                project_root / "include",
                project_root / "src",
                project_root,
                file_path.parent,
            ]
        else:
            search_dirs = [
                file_path.parent,
                project_root / "src",
                project_root / "include",
                project_root,
            ]

        for d in search_dirs:
            p = d / name
            rel = _rel_if_exists(project_root, p)
            if rel and idx.exists(rel):
                candidates.append(rel)

        # If include without extension, try .h/.hpp/.hh
        if "." not in name:
            for ext in (".h", ".hpp", ".hh", ".hxx"):
                for d in search_dirs:
                    p = d / (name + ext)
                    rel = _rel_if_exists(project_root, p)
                    if rel and idx.exists(rel):
                        candidates.append(rel)

        seen = set()
        out = []
        for c in candidates:
            if c not in seen:
                seen.add(c)
                out.append(c)
        return out


# ---------------------------
# C#
# ---------------------------


class CSharpUsingResolver:
    def resolve(self, project_root: Path, file_path: Path, import_path: str) -> list[str]:
        # using System.Collections; -> "System.Collections"
        ns = import_path.strip()

        # Best effort: namespace -> folder path
        idx = build_path_index(str(project_root))
        parts = ns.split(".")

        # Try map to folder, then attach all .cs in that folder
        candidates: list[str] = []
        for base in (project_root, project_root / "src", project_root / "Source"):
            d = base / "/".join(parts)
            rel_dir = _rel_if_exists(project_root, d)
            if not rel_dir:
                continue

            # Find all .cs files in that directory
            pref = rel_dir.rstrip("/") + "/"
            for rel in idx.by_rel:
                if rel.startswith(pref) and rel.endswith(".cs"):
                    candidates.append(rel)

        # Also try by basename of last segment (Foo.cs)
        leaf = parts[-1]
        candidates.extend(idx.find_by_basename(leaf + ".cs"))

        seen = set()
        out = []
        for c in candidates:
            if c not in seen:
                seen.add(c)
                out.append(c)
        return out


# ---------------------------
# Resolver selection
# ---------------------------


class NoopResolver:
    def resolve(self, project_root: Path, file_path: Path, import_path: str) -> list[str]:
        return []


def resolve_import_resolver(language_id: str) -> ImportResolver:
    lid = (language_id or "").lower()
    if lid in ("javascript", "typescript"):
        return JSImportResolver()
    if lid in ("java", "kotlin"):
        return JavaKotlinImportResolver()
    if lid == "go":
        return GoImportResolver()
    if lid == "rust":
        return RustImportResolver()
    if lid in ("c", "cpp", "c++"):
        return CIncludeResolver()
    if lid in ("csharp", "cs"):
        return CSharpUsingResolver()
    return NoopResolver()
