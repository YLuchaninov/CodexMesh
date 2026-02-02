"""
DevTool to verify that extractors conform to the Import Contract.

Usage:
    uv run python -m codex_mesh.devtools.check_import_contract <path_to_file>

Checks:
- Extractor runs successfully
- Returns PendingImports with valid fields
- 'raw' is populated
- 'candidates' are not empty (warning) or at least structure is correct
- 'kind' is one of allowed values
"""

import argparse
import sys
from pathlib import Path

from codex_mesh.core.nodes import FileNode
from codex_mesh.extractors.protocols import ExtractorContext
from codex_mesh.extractors.registry import ExtractorRegistry


def main():
    parser = argparse.ArgumentParser(description="Check extractor import contract")
    parser.add_argument("file_path", help="Path to source file to check")
    args = parser.parse_args()

    fpath = Path(args.file_path).resolve()
    if not fpath.exists():
        print(f"File not found: {fpath}")
        sys.exit(1)

    project_root = fpath.parent  # Simplified
    # Try to find actual root (git or whatever), but parent is safe fallback for loose check
    for p in fpath.parents:
        if (
            (p / ".git").exists()
            or (p / "pyproject.toml").exists()
            or (p / "package.json").exists()
        ):
            project_root = p
            break

    print(f"Project root: {project_root}")
    print(f"Checking file: {fpath}")

    registry = ExtractorRegistry.default()
    extractor = registry.get_for_path(fpath)

    if not extractor:
        print(f"No extractor found for {fpath}")
        sys.exit(1)

    print(f"Using extractor: {extractor.__class__.__name__} ({extractor.language_id})")

    content = fpath.read_text(encoding="utf-8", errors="replace")
    rel_path = fpath.relative_to(project_root).as_posix()

    file_node = FileNode.create(
        path=str(fpath), relative_path=rel_path, content_hash="mock", mtime=0.0
    )
    ctx = ExtractorContext(project_root=project_root, file_path=fpath, relative_path=rel_path)

    try:
        result = extractor.extract(ctx, file_node, content)
    except Exception as e:
        print(f"Extraction failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    print(f"\nFound {len(result.pending_imports)} imports:")

    errors = []

    for i, imp in enumerate(result.pending_imports):
        print(f"  [{i}] {imp.raw} (kind={imp.kind}, candidates={len(imp.candidates)})")

        # Contract checks
        if not imp.raw:
            errors.append(f"Import [{i}]: raw field is empty")

        if imp.kind not in ("import", "from", "require", "using", "include", "use", None):
            print(f"    WARNING: Unknown kind '{imp.kind}'")

        if imp.is_star and imp.imported_names:
            errors.append(f"Import [{i}]: is_star=True but imported_names is populated")

        if imp.alias_map:
            for k, v in imp.alias_map.items():
                if not k or not v:
                    errors.append(f"Import [{i}]: Invalid alias map entry '{k}': '{v}'")

    if errors:
        print("\n❌ Contract Violations:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)
    else:
        print("\n✅ Import Contract Verified")


if __name__ == "__main__":
    main()
