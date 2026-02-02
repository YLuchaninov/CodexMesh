"""
Tests for API contract compliance.
"""

from codex_mesh.contracts.analysis import SearchMatch, SemanticResult, SymbolInfo


def test_semantic_result_padding():
    """Verify SemanticResult handles optional fields and padding."""
    # Case 1: Minimal init
    res = SemanticResult(id="node1", name="foo", score=0.9)
    assert res.id == "node1"
    assert res.span is None

    # Case 2: Validation of padding would happen in service, but contract allows optional
    assert res.line_end is None


def test_search_match_structure():
    """Verify SearchMatch fields."""
    m = SearchMatch(id="foo", file_path="foo.py", snippet="code")
    assert m.id == "foo"
    assert m.span is None


def test_symbol_info_structure():
    """Verify SymbolInfo structure."""
    s = SymbolInfo(id="node1", name="foo", type="function", file_path="a.py")
    assert s.id == "node1"
    assert s.found is True
