from pathlib import Path

import pytest

from codex_mesh.core.nodes import FileNode
from codex_mesh.extractors.protocols import ExtractorContext
from codex_mesh.extractors.treesitter_query import QueryBundle, TreeSitterQueryExtractor


def test_treesitter_missing_language_is_nonfatal(tmp_path: Path):
    pytest.importorskip("tree_sitter_language_pack")

    ex = TreeSitterQueryExtractor(
        language_id="badlang",
        extensions=(".bad",),
        ts_lang_key="definitely_not_a_real_language_key",
        queries=QueryBundle(classes=None, functions=None, methods=None, imports=None, calls=None),
    )

    file_path = tmp_path / "x.bad"
    file_path.write_text("hello")
    ctx = ExtractorContext(tmp_path, file_path, "x.bad")
    file_node = FileNode.create("x.bad", "x.bad")

    res = ex.extract(ctx, file_node, file_path.read_text())
    assert res.nodes == []
    assert res.edges == []
