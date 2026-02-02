import logging
import sys

from codex_mesh.extractors.builtin_treesitter import register_defaults
from codex_mesh.extractors.registry import ExtractorRegistry
from codex_mesh.extractors.treesitter_query import _EXTRA_CALL_QUERIES, TreeSitterQueryExtractor

# Configure logging to capture warnings
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("codex_mesh.extractors.treesitter_query")


def verify():
    registry = ExtractorRegistry()
    register_defaults(registry)

    print(f"Registered {len(set(registry._by_ext.values()))} extractors.")

    failures = 0

    for ext in set(registry._by_ext.values()):
        if isinstance(ext, TreeSitterQueryExtractor):
            print(f"Checking {ext.language_id}...")

            # Check symbol query (composite)
            queries = ext._queries
            parts = []
            if queries.classes:
                parts.append(queries.classes.replace("@name", "@class_name"))
            if queries.functions:
                parts.append(queries.functions.replace("@name", "@func_name"))
            if queries.methods:
                parts.append(queries.methods.replace("@name", "@method_name"))
            if queries.decorators:
                parts.append(queries.decorators)
            if queries.modifiers:
                parts.append(queries.modifiers)
            if queries.entrypoints:
                parts.append(queries.entrypoints)

            full_symbol = "\n".join(parts)
            if full_symbol:
                q = ext._compile_query(full_symbol)
                if q is None:
                    print(f"  [X] Symbol query failed for {ext.language_id}")
                    failures += 1

            # Check imports
            if queries.imports:
                q = ext._compile_query(queries.imports)
                if q is None:
                    print(f"  [X] Import query failed for {ext.language_id}")
                    failures += 1

            # Check bases
            if queries.bases:
                q = ext._compile_query(queries.bases)
                if q is None:
                    print(f"  [X] Bases query failed for {ext.language_id}")
                    failures += 1

            # Check calls
            calls = []
            if queries.calls:
                calls.append(queries.calls)
            if ext.language_id in _EXTRA_CALL_QUERIES:
                calls.append(_EXTRA_CALL_QUERIES[ext.language_id])

            if calls:
                full_calls = "\n".join(calls)
                q = ext._compile_query(full_calls)
                if q is None:
                    print(f"  [X] Calls query failed for {ext.language_id}")
                    failures += 1

    if failures == 0:
        print("\nAll queries compiled successfully!")
    else:
        print(f"\n{failures} query failures detected.")
        sys.exit(1)


if __name__ == "__main__":
    verify()
