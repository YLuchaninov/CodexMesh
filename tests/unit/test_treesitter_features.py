from pathlib import Path

import pytest

from codex_mesh.core.nodes import ClassNode, FileNode, FunctionNode
from codex_mesh.extractors.protocols import ExtractorContext
from codex_mesh.extractors.treesitter_query import QueryBundle, TreeSitterQueryExtractor


# Use Python as it's easy to mock/fixture for us (we have the parser)
@pytest.fixture
def extractor_python():
    # Minimal config for Python
    return TreeSitterQueryExtractor(
        language_id="python",
        extensions=(".py",),
        ts_lang_key="python",
        queries=QueryBundle(
            classes="(class_definition name: (identifier) @name)",
            functions="(function_definition name: (identifier) @name)",
            methods=None,  # In python queries typically separate, but for unit test we can simplify
            imports=None,
            bases="(class_definition superclasses: (argument_list (identifier) @base))",
        ),
    )


def test_extract_docstrings(extractor_python):
    # Note: Our query extractor logic attempts to grab comments *above* the definition.
    # Python docstrings are usually *inside* the body.
    # But our implementation in `treesitter_query.py` `_extract_doc_comment` looks at lines *before* start.
    # So we should test that behavior: "Above-method docs".

    code_comments = """
# This is a class doc
class Foo:
    pass

# This is a func doc
def bar():
    pass
"""
    ctx = ExtractorContext(Path("."), Path("test.py"), "test.py")
    node = FileNode.create("test.py", "test.py")

    res = extractor_python.extract(ctx, node, code_comments)

    cls_node = next(n for n in res.nodes if isinstance(n, ClassNode))
    func_node = next(n for n in res.nodes if isinstance(n, FunctionNode))

    assert cls_node.docstring is not None
    assert "This is a class doc" in cls_node.docstring

    assert func_node.docstring is not None
    assert "This is a func doc" in func_node.docstring


def test_extract_bases(extractor_python):
    code = """
class Base: pass
class Derived(Base): pass
"""
    ctx = ExtractorContext(Path("."), Path("test.py"), "test.py")
    node = FileNode.create("test.py", "test.py")
    res = extractor_python.extract(ctx, node, code)

    derived = next(n for n in res.nodes if n.name == "Derived")
    assert isinstance(derived, ClassNode)
    assert "Base" in derived.bases


def test_extract_signature(extractor_python):
    # We need to enable sig extraction, which happens for functions/methods
    code = "def my_func(a, b): pass"

    ctx = ExtractorContext(Path("."), Path("test.py"), "test.py")
    node = FileNode.create("test.py", "test.py")
    res = extractor_python.extract(ctx, node, code)

    func = next(n for n in res.nodes if n.name == "my_func")
    assert isinstance(func, FunctionNode)
    # The signature extractor grabs limits to 500 chars and splits at { or ; or \n
    # Python def ends with : usually.
    # Our impl: splits at {, ;, \n. Python code "def mys_func(a,b): pass"
    # It might capture "def my_func(a, b): pass" if single line.

    assert func.signature is not None
    assert "def my_func(a, b)" in func.signature
