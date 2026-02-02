"""Integration tests for multi-language graph construction."""

import pytest

from codex_mesh.core.edges import EdgeType
from codex_mesh.core.graph import CodeGraphBuilder

pytest.importorskip("tree_sitter_language_pack")


@pytest.fixture
def multilang_project(tmp_path):
    p = tmp_path / "polyglot"
    p.mkdir()

    # Python calling TS? ( Conceptual)
    # Let's just have Python and TS in same repo

    (p / "main.py").write_text("""
class PyService:
    def handle(self):
        pass
""")

    (p / "app.ts").write_text("""
import { util } from "./lib";
export class TsApp {
    run() { util(); }
}
""")

    (p / "lib.ts").write_text("""
export function util() { return 1; }
""")

    return p


def test_multilang_build(multilang_project):
    builder = CodeGraphBuilder(str(multilang_project))
    builder.build()

    files = builder.get_files()
    paths = {f.relative_path for f in files}
    assert "main.py" in paths
    assert "app.ts" in paths

    # Check TS relative import resolution
    # import { util } from "./lib" creates a file→symbol edge (app.ts → util function)
    # This is the correct behavior when imported_names is specified

    app_node = next(f for f in files if f.relative_path == "app.ts")

    # Find the imported function 'util' from lib.ts
    functions = builder.get_functions()
    util_fn = next((f for f in functions if f.name == "util" and f.file_path == "lib.ts"), None)
    assert util_fn is not None, "Expected 'util' function in lib.ts"

    app_idx = builder._node_id_to_index[app_node.id]
    util_idx = builder._node_id_to_index[util_fn.id]

    edge = builder.graph.get_edge_data(app_idx, util_idx)
    assert edge is not None, "Expected IMPORTS edge from app.ts to util function"
    assert edge.edge_type == EdgeType.IMPORTS
