from codex_mesh.review.markdown_render import MarkdownRenderer


def test_render_search_results():
    results = [
        {
            "type": "function",
            "name": "foo",
            "is_method": False,
            "file_path": "a.py",
            "line_start": 10,
            "signature": "def foo(x)",
        },
        {"type": "class", "name": "Bar", "file_path": "b.py", "line_start": 20},
    ]
    md = MarkdownRenderer.render_search_results(results, "query")
    assert "Found 2 results for 'query':" in md
    assert "⚡ def foo(x)" in md
    assert "📍 a.py:10" in md
    assert "🔷 class Bar" in md
    assert "📍 b.py:20" in md


def test_render_semantic_search_results():
    results = [
        {
            "name": "foo",
            "score": 0.95,
            "file_path": "a.py",
            "line_start": 10,
            "line_end": 15,
            "content": "def foo():\n    pass",
        }
    ]
    md = MarkdownRenderer.render_semantic_search_results(results, "query")
    assert "Semantic search results for 'query':" in md
    assert "📌 foo (relevance: 95%)" in md
    assert "📍 a.py:10-15" in md
    assert "def foo():" in md


def test_render_hotspot_report():
    scores = [
        {
            "node_id": "a.py",
            "total": 10.5,
            "structural": 5.0,
            "semantic": 5.5,
            "issues": [{"type": "warn", "message": "Too complex"}],
        }
    ]
    md = MarkdownRenderer.render_hotspot_report(scores)
    assert "# Hotspot Report" in md
    assert "## a.py" in md
    assert "Total: 10.5" in md
    assert "[warn] Too complex" in md


def test_render_hotspot_report_empty():
    md = MarkdownRenderer.render_hotspot_report([])
    assert md == "No hotspot data available"


def test_render_hotspot_report_no_issues():
    md = MarkdownRenderer.render_hotspot_report([{"total": 0.0}])
    assert md == "✅ No hotspot issues found - code looks good!"


def test_render_function_info():
    info = {
        "found": True,
        "name": "foo",
        "file_path": "a.py",
        "line_start": 1,
        "line_end": 10,
        "signature": "def foo()",
        "docstring": "A fee",
        "callers": [{"name": "bar"}],
    }
    md = MarkdownRenderer.render_function_info(info, "foo")
    assert "# Function: foo" in md
    assert "**Called by:**" in md
    assert "- bar" in md


def test_render_dead_code_candidates():
    candidates = [{"name": "old_func", "file_path": "x.py", "line_start": 100}]
    md = MarkdownRenderer.render_dead_code_candidates(candidates)
    assert "- `old_func` in x.py:100" in md
