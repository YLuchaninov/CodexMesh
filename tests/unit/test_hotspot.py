"""
Unit tests for HotspotCalculator.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from codex_mesh.core.nodes import FunctionNode
from codex_mesh.metrics.hotspot import HotspotCalculator, HotspotScore


@pytest.fixture
def hotspot_calculator(mock_config):
    """Create a HotspotCalculator instance with mocked config."""
    return HotspotCalculator(project_root="/tmp/test_project", config=mock_config)


def test_calculate_structural_hotspot(hotspot_calculator):
    """Test calculation of structural hotspot from Ruff output."""
    mock_issues = [
        {
            "code": "E101",
            "message": "Indentation error",
            "severity": "error",
            "location": {"row": 10},
        },
        {
            "code": "W291",
            "message": "Trailing whitespace",
            "severity": "warning",
            "location": {"row": 20},
        },
    ]

    with (
        patch("codex_mesh.metrics.hotspot.HotspotCalculator._run_ruff", return_value=mock_issues),
        patch("codex_mesh.metrics.hotspot.HotspotCalculator._find_todos", return_value=[]),
        patch("pathlib.Path.exists", return_value=True),
    ):
        score = hotspot_calculator.calculate_file_hotspot("test_file.py")

        # Error (10.0) + Warning (5.0) = 15.0
        assert score.structural == 15.0
        assert len(score.issues) == 2
        assert score.issues[0]["type"] == "lint"


def test_calculate_structural_hotspot_failure(hotspot_calculator):
    """Test handling of unexpected linter failure."""
    # Mock safe_shell to raise exception, so _run_ruff catches it
    with (
        patch("codex_mesh.metrics.hotspot.safe_shell", side_effect=Exception("Ruff died")),
        patch("pathlib.Path.exists", return_value=True),
    ):
        score = hotspot_calculator.calculate_file_hotspot("test_fail.py")

        # Should contain one warning issue
        assert len(score.issues) == 1
        assert score.issues[0]["message"] == "Analysis failed: Ruff died"


def test_aggregate_for_function(hotspot_calculator):
    """Test aggregating scores for a specific function."""
    file_score = HotspotScore(
        node_id="file::test.py",
        issues=[
            {"type": "lint", "code": "E101", "line": 5},  # Inside
            {"type": "lint", "code": "W291", "line": 20},  # Inside
            {"type": "lint", "code": "E999", "line": 50},  # Outside
        ],
    )

    function_node = FunctionNode(
        id="func::test",
        name="test_func",
        file_path="test.py",
        line_start=1,
        line_end=30,
        body="...",
        decorators=[],
        args=[],
        return_type="None",
        docstring="None",
    )

    # We need to manually set up weights since aggregate uses them
    # But HotspotCalculator instance already has them from init

    func_score = hotspot_calculator.aggregate_for_function(function_node, file_score)

    # E101 (10.0) + W291 (5.0) = 15.0
    # E999 is excluded
    assert func_score.structural == 15.0
    assert len(func_score.issues) == 2


def test_calculate_semantic_hotspot_todos(hotspot_calculator):
    """Test semantic hotspot from TODOs."""
    mock_todos = [
        {"type": "todo", "message": "Refactor this", "line": 15, "weight": 2.0},
        {"type": "fixme", "message": "Broken logic", "line": 25, "weight": 5.0},
    ]

    with (
        patch("codex_mesh.metrics.hotspot.HotspotCalculator._run_ruff", return_value=[]),
        patch("codex_mesh.metrics.hotspot.HotspotCalculator._find_todos", return_value=mock_todos),
        patch("pathlib.Path.exists", return_value=True),
    ):
        score = hotspot_calculator.calculate_file_hotspot("test_file.py")

        assert score.semantic == 7.0
        assert len(score.issues) == 2


def test_calculate_behavioral_churn(hotspot_calculator):
    """Test behavioral hotspot from Git churn."""
    # Mock safe_shell in hotspot module
    with patch("codex_mesh.metrics.hotspot.safe_shell") as mock_shell:
        from codex_mesh.core.shell import ShellResult

        # Mock successful git log output
        mock_shell.return_value = ShellResult(
            stdout="hash1\nhash2\nhash3", stderr="", returncode=0, success=True
        )

        # We need to ensure _churn_map is empty or handled
        hotspot_calculator._churn_map = {}

        # Also patch Path.exists to true so it proceeds
        with patch("pathlib.Path.exists", return_value=True):
            score = hotspot_calculator.calculate_file_hotspot("churny_file.py")

        # 3 commits * default weight (0.5) = 1.5
        assert score.behavioral == 1.5
        assert any(i["type"] == "churn" for i in score.issues)
        assert score.issues[-1]["count"] == 3


# ... (rest of code)


def test_calculate_graph_coupling(hotspot_calculator):
    """Test graph coupling hotspot."""
    # Mock graph builder interaction
    mock_gb = Mock()
    mock_graph = MagicMock()  # Use MagicMock for __getitem__ support
    mock_gb.graph = mock_graph

    # Setup mock graph data
    # node indices: 0 (file1), 1 (file2), 2 (file3)
    mock_graph.node_indices.return_value = [0, 1, 2]

    # Enable __getitem__ on the mock to return node data
    # We use a side_effect dict or function
    # nodes: 0 (file1), 1 (file2), 2 (file3)
    # We use valid FileNode objects so isinstance(node, FileNode) passes
    from codex_mesh.core.nodes import FileNode

    nodes = []
    for i in range(3):
        nodes.append(
            FileNode(
                id=f"file::file_{i}.py",
                name=f"file_{i}.py",
                path=f"/tmp/file_{i}.py",
                relative_path=f"file_{i}.py",
            )
        )

    def get_node_data(idx):
        return nodes[idx]

    mock_graph.__getitem__.side_effect = get_node_data

    # edges: 0->1, 2->1 (1 has in=2, out=0; 0 has out=1; 2 has out=1)
    # edges: 0->1, 2->1
    from codex_mesh.core.edges import EdgeType

    edge_data = Mock()
    edge_data.edge_type = EdgeType.IMPORTS

    # edge_list returns (u, v, data)
    # mock_graph.edge_list.return_value = ...

    # We now use out_edges(u) -> [(u, v, data), ...]
    def get_out_edges(u):
        # 0 -> 1
        if u == 0:
            return [(0, 1, edge_data)]
        # 2 -> 1
        if u == 2:
            return [(2, 1, edge_data)]
        return []

    mock_graph.out_edges.side_effect = get_out_edges

    # Create mock node data objects that are NOT mocks themselves to avoid magic method issues if possible,
    # or just simple objects

    hotspot_calculator.bind_graph(mock_gb)

    with (
        patch.object(hotspot_calculator, "_run_ruff", return_value=[]),
        patch.object(hotspot_calculator, "_find_todos", return_value=[]),
        patch("pathlib.Path.exists", return_value=True),
    ):
        # Trigger pre-calculation
        hotspot_calculator.calculate_all(["file_1.py"])

    # Check file_1 (index 1) which has 2 in-edges
    score = hotspot_calculator._scores.get("file::file_1.py")

    # 2 in * 0.3 (default) = 0.6
    assert score is not None
    assert score.graph == 0.6
    assert any(i["type"] == "coupling" for i in score.issues)


# =========== P0 Tests ===========


def test_find_todos_case_insensitive(hotspot_calculator, tmp_path):
    """Test that TODO detection is case-insensitive."""
    # Create a file with lowercase and mixed case TODO markers
    test_file = tmp_path / "test_todos.py"
    test_file.write_text("""# todo: lowercase todo
# Todo: TitleCase todo
# FIXME: uppercase fixme
# fixme: lowercase fixme
# hack: lowercase hack
""")

    issues = hotspot_calculator._find_todos(test_file)

    # Should find all 5 markers regardless of case
    assert len(issues) == 5
    types = [i["type"] for i in issues]
    assert types.count("todo") == 2
    assert types.count("fixme") == 2
    assert types.count("hack") == 1


def test_find_todos_not_in_strings(hotspot_calculator, tmp_path):
    """Test that TODOs inside string literals are NOT detected."""
    test_file = tmp_path / "test_string_todos.py"
    test_file.write_text("""
# TODO: This is a real comment todo
x = "TODO: This should NOT match"
y = 'FIXME: This should also NOT match'
message = '''
TODO: This is inside a docstring-like triple quote
'''
# HACK: another real one
""")

    issues = hotspot_calculator._find_todos(test_file)

    # Should only find the 2 comment TODOs (line 2 and line 8)
    assert len(issues) == 2
    lines = sorted([i["line"] for i in issues])
    # Line 2 is "# TODO: This is a real comment todo"
    # Line 8 is "# HACK: another real one"
    assert 2 in lines  # The real TODO comment
    assert any(i["type"] == "hack" for i in issues)


def test_aggregate_for_function_treats_F_codes_as_error(hotspot_calculator):
    """Test that F* Ruff codes are treated as errors, not warnings."""
    file_score = HotspotScore(
        node_id="file::test.py",
        issues=[
            {"type": "lint", "code": "F401", "line": 5},  # Unused import - should be ERROR
            {"type": "lint", "code": "F841", "line": 10},  # Unused variable - should be ERROR
            {"type": "lint", "code": "W291", "line": 15},  # Whitespace - should be WARNING
            {"type": "lint", "code": "E101", "line": 20},  # Indentation - should be ERROR
        ],
    )

    function_node = FunctionNode(
        id="func::test",
        name="test_func",
        file_path="test.py",
        line_start=1,
        line_end=25,
        body="...",
        decorators=[],
        args=[],
        return_type="None",
        docstring="None",
    )

    func_score = hotspot_calculator.aggregate_for_function(function_node, file_score)

    # 3 errors (F401, F841, E101) * 10.0 + 1 warning (W291) * 5.0 = 35.0
    assert func_score.structural == 35.0


def test_hotspot_score_has_file_path(hotspot_calculator, tmp_path):
    """Test that HotspotScore includes file_path field."""
    test_file = tmp_path / "test_file_path.py"
    test_file.write_text("x = 1\n")

    # Temporarily set project root to tmp_path for this test
    original_root = hotspot_calculator.project_root
    hotspot_calculator.project_root = tmp_path

    try:
        score = hotspot_calculator.calculate_file_hotspot("test_file_path.py")

        # Check file_path is set
        assert score.file_path == "test_file_path.py"

        # Check file_path is in to_dict() output
        d = score.to_dict()
        assert "file_path" in d
        assert d["file_path"] == "test_file_path.py"
    finally:
        hotspot_calculator.project_root = original_root


def test_calculate_all_determinism(hotspot_calculator, tmp_path):
    """Test that calculate_all produces deterministic results."""
    # Create test files
    for i in range(3):
        f = tmp_path / f"file_{i}.py"
        f.write_text(f"# TODO: file {i}\n")

    original_root = hotspot_calculator.project_root
    hotspot_calculator.project_root = tmp_path

    try:
        paths = ["file_2.py", "file_0.py", "file_1.py"]  # Unsorted

        result1 = hotspot_calculator.calculate_all(paths.copy())
        result2 = hotspot_calculator.calculate_all(paths.copy())

        # Results should be identical
        keys1 = sorted(result1.keys())
        keys2 = sorted(result2.keys())
        assert keys1 == keys2

        for key in keys1:
            assert result1[key].to_dict() == result2[key].to_dict()
    finally:
        hotspot_calculator.project_root = original_root


def test_calculate_multi_axis_metrics(hotspot_calculator, tmp_path):
    """Test integration of P2 Multi-Axis scorers in calculate_file_hotspot."""
    test_file = tmp_path / "test_p2.py"
    # Content with Logic (deep nesting), Concurrency (async), Risk (os.environ)
    test_file.write_text("""
import os
import asyncio

async def complex_risk():
    key = os.environ['SECRET']
    if True:
        if True:
            if True:
                if True:
                    if True:
                         print("deep")
    await asyncio.sleep(1)
""")

    original_root = hotspot_calculator.project_root
    hotspot_calculator.project_root = tmp_path

    try:
        score = hotspot_calculator.calculate_file_hotspot("test_p2.py")

        # Check Complexity (Logic + Concurrency)
        # Concurrency: >1.0
        # Logic: nesting >5 levels -> some score
        assert score.complexity > 1.0

        # Check Risk
        # os.environ -> >0.5
        assert score.risk > 0.5

        # Check Issues
        types = [i["type"] for i in score.issues]
        assert "logic" in types
        assert "concurrency" in types
        assert "risk" in types
    finally:
        hotspot_calculator.project_root = original_root


def test_find_todos_not_in_js_regex_literals(hotspot_calculator, tmp_path):
    """JS/TS: TODO markers inside regex literals must NOT be treated as comments."""
    test_file = tmp_path / "test_regex_todos.js"
    test_file.write_text("""
const re1 = /[/*] TODO: should NOT match/;
const re2 = /foo\\/[/*] FIXME: also should NOT match/gi;
// TODO: real
/* HACK: real */
""")

    issues = hotspot_calculator._find_todos(test_file)

    # Should only find the two real comments (line 4 and line 5)
    assert len(issues) == 2
    lines = sorted([i["line"] for i in issues])
    assert lines == [4, 5]
    types = sorted([i["type"] for i in issues])
    assert "todo" in types
    assert "hack" in types
