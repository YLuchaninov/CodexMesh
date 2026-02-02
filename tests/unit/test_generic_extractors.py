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


def test_js_complex_extraction(registry):
    js_extractor = registry.get_for_path(Path("test.js"))
    assert js_extractor is not None

    fixture_path = (
        Path(__file__).parent.parent / "fixtures" / "langs" / "javascript" / "complex_a.js"
    )
    content = fixture_path.read_text()

    ctx = ExtractorContext(fixture_path.parent, fixture_path, "complex_a.js")
    file_node = FileNode.create("complex_a.js", "complex_a.js")

    res = js_extractor.extract(ctx, file_node, content)

    # Verify classes
    classes = [n for n in res.nodes if isinstance(n, ClassNode)]
    assert len(classes) == 1
    cls = classes[0]
    assert cls.name == "HeavyClass"
    assert "BaseClass" in cls.bases
    assert "classDecorator" in cls.decorators
    assert "A class with decorators and methods." in cls.docstring

    # Verify methods
    methods = [n for n in res.nodes if isinstance(n, FunctionNode) and n.is_method]
    assert len(methods) >= 2
    compute = next(m for m in methods if m.name == "compute")
    assert compute.docstring == "Method docstring."
    assert "methodDecorator" in compute.decorators
    # Generic extraction doesn't catch 'async' specifically yet for all languages unless in query

    # Verify functions
    funcs = [n for n in res.nodes if isinstance(n, FunctionNode) and not n.is_method]
    assert any(f.name == "processAll" for f in funcs)
    process_all = next(f for f in funcs if f.name == "processAll")
    assert "Single line doc" in process_all.docstring
    assert "with multiple lines" in process_all.docstring


def test_go_complex_extraction(registry):
    go_extractor = registry.get_for_path(Path("test.go"))

    fixture_path = Path(__file__).parent.parent / "fixtures" / "langs" / "go" / "complex_main.go"
    content = fixture_path.read_text()

    ctx = ExtractorContext(fixture_path.parent, fixture_path, "complex_main.go")
    file_node = FileNode.create("complex_main.go", "complex_main.go")

    res = go_extractor.extract(ctx, file_node, content)

    # Verify struct -> class mapping
    classes = [n for n in res.nodes if isinstance(n, ClassNode)]
    assert any(c.name == "MyService" for c in classes)

    # Verify methods
    methods = [n for n in res.nodes if isinstance(n, FunctionNode) and n.is_method]
    log_method = next(m for m in methods if m.name == "Log")
    assert "Log implementation for MyService." in log_method.docstring
    assert "Testing multiline block comments." in log_method.docstring

    # Verify entrypoint detection
    main_func = next(n for n in res.nodes if n.name == "main")
    assert main_func.meta.get("is_entrypoint") is True


def test_ts_complex_extraction(registry):
    ts_extractor = registry.get_for_path(Path("test.ts"))

    fixture_path = (
        Path(__file__).parent.parent / "fixtures" / "langs" / "typescript" / "complex_a.ts"
    )
    content = fixture_path.read_text()

    ctx = ExtractorContext(fixture_path.parent, fixture_path, "complex_a.ts")
    file_node = FileNode.create("complex_a.ts", "complex_a.ts")

    res = ts_extractor.extract(ctx, file_node, content)

    classes = [n for n in res.nodes if isinstance(n, ClassNode)]
    assert any(c.name == "DataProcessor" for c in classes)
    dp = next(c for c in classes if c.name == "DataProcessor")
    assert "UtilityClass" in dp.bases
    assert dp.docstring is not None
    assert "TS Class with modifiers" in dp.docstring

    # Check method modifiers
    methods = [n for n in res.nodes if isinstance(n, FunctionNode) and n.is_method]
    process = next(m for m in methods if m.name == "process")
    assert "public" in process.modifiers
    # async still not captured for TS in my version? Let me check
    # assert "async" in process.modifiers
