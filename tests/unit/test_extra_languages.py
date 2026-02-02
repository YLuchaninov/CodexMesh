from pathlib import Path

import pytest

from codex_mesh.core.nodes import ClassNode, FileNode, FunctionNode
from codex_mesh.extractors.builtin_treesitter import register_defaults
from codex_mesh.extractors.protocols import ExtractorContext
from codex_mesh.extractors.registry import ExtractorRegistry

pytest.importorskip("tree_sitter_language_pack")


@pytest.fixture
def registry():
    r = ExtractorRegistry()
    register_defaults(r)
    return r


LANGS = [
    ("rust", "lib.rs", "rs"),
    ("java", "App.java", "java"),
    ("cpp", "main.cpp", "cpp"),
    ("c", "main.c", "c"),
    ("csharp", "Program.cs", "cs"),
    ("php", "index.php", "php"),
    ("ruby", "app.rb", "rb"),
    ("swift", "main.swift", "swift"),
    ("kotlin", "main.kt", "kt"),
    ("dart", "main.dart", "dart"),
    ("scala", "Main.scala", "scala"),
]


@pytest.mark.parametrize("lang, filename, ext", LANGS)
def test_extra_lang_extraction(registry, lang, filename, ext):
    fixture_dir = Path(__file__).parent.parent / "fixtures" / "langs" / lang
    if not fixture_dir.exists():
        pytest.skip(f"Fixture dir for {lang} not found")

    fixtures = list(fixture_dir.glob(f"*.{ext}"))
    if not fixtures:
        pytest.skip(f"No {ext} fixtures found for {lang}")

    fixture_path = fixtures[0]
    content = fixture_path.read_text()

    extractor = registry.get_for_path(fixture_path)
    assert extractor is not None, f"No extractor for {lang}"

    ctx = ExtractorContext(fixture_path.parent, fixture_path, fixture_path.name)
    file_node = FileNode.create(fixture_path.name, fixture_path.name)

    res = extractor.extract(ctx, file_node, content)

    # We don't assert specific counts because fixtures vary,
    # but we want to know it didn't crash and found *something* if expected
    assert res is not None
    # All language fixtures should have at least some symbols (class or function)
    symbols = [n for n in res.nodes if isinstance(n, (ClassNode, FunctionNode))]
    assert len(symbols) > 0  # Should find at least one class/function
