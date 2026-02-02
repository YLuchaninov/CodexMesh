from unittest.mock import patch

import pytest

from codex_mesh.core.edges import Edge, EdgeType
from codex_mesh.core.graph import CodeGraphBuilder
from codex_mesh.core.nodes import FileNode, FunctionNode, NodeType


@pytest.fixture
def builder(tmp_path):
    return CodeGraphBuilder(str(tmp_path))


def test_add_node_upsert(builder):
    node1 = FileNode.create(path="test.py", relative_path="test.py", content_hash="h1")
    idx1 = builder._add_node(node1)

    # Upsert with same ID but different data
    node1_v2 = FileNode.create(path="test.py", relative_path="test.py", content_hash="h2")
    idx2 = builder._add_node(node1_v2)

    assert idx1 == idx2
    assert builder.get_node_by_id(node1.id).content_hash == "h2"


def test_save_load_snapshot(builder, tmp_path):
    # Setup graph
    n1 = FileNode.create(path=str(tmp_path / "a.py"), relative_path="a.py", content_hash="1")
    n2 = FunctionNode(
        id="f1",
        name="func",
        file_path="a.py",
        node_type=NodeType.FUNCTION,
        line_start=1,
        line_end=2,
    )
    builder._add_node(n1)
    builder._add_node(n2)
    builder._add_edge(Edge.create(n1.id, n2.id, EdgeType.CONTAINS))

    snapshot_path = tmp_path / "graph.json"
    builder.save_snapshot(snapshot_path)
    assert snapshot_path.exists()

    # Load into new builder
    new_builder = CodeGraphBuilder(str(tmp_path))
    success = new_builder.load_snapshot(snapshot_path, validate_sources=False)
    assert success
    assert len(new_builder.get_all_nodes()) == 2
    assert new_builder.get_node_by_id("f1").name == "func"


def test_discover_files_with_git(builder, tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / "code.py").write_text("print(1)")
    (tmp_path / "ignored.py").write_text("print(2)")

    # Mock safe_shell for git check-ignore
    with patch("codex_mesh.core.graph.safe_shell") as mock_shell:
        from codex_mesh.core.shell import ShellResult

        mock_shell.return_value = ShellResult(
            returncode=0, stdout="ignored.py\n", stderr="", success=True
        )

        files = builder._discover_files(exclude_patterns=[])
        # ignored.py should be filtered out
        assert len(files) == 1
        assert files[0].name == "code.py"


def test_resolve_pending_calls_class_aware(builder):
    # Setup nodes: Class A has method m1, Class B has method m1
    # Function in A calls "m1"
    c1 = FunctionNode(
        id="A::m1",
        name="m1",
        file_path="a.py",
        class_name="A",
        node_type=NodeType.METHOD,
        line_start=1,
        line_end=2,
    )
    c2 = FunctionNode(
        id="B::m1",
        name="m1",
        file_path="b.py",
        class_name="B",
        node_type=NodeType.METHOD,
        line_start=1,
        line_end=2,
    )
    caller = FunctionNode(
        id="A::caller",
        name="caller",
        file_path="a.py",
        class_name="A",
        node_type=NodeType.METHOD,
        line_start=5,
        line_end=10,
    )

    builder._add_node(c1)
    builder._add_node(c2)
    builder._add_node(caller)

    # Pending call to "m1" from "A::caller"
    from codex_mesh.extractors.protocols import PendingCall

    builder._pending_calls.append(
        PendingCall(source_id="A::caller", callee_name="m1", file_path="a.py", line=1)
    )

    builder._resolve_pending_calls()

    # Should have linked to A::m1 because it's in the same class
    caller_idx = builder._node_id_to_index["A::caller"]
    c1_idx = builder._node_id_to_index["A::m1"]
    edge = builder.graph.get_edge_data(caller_idx, c1_idx)
    assert edge is not None
    assert edge.edge_type == EdgeType.CALLS


def test_resolve_pending_calls_import_aware(builder):
    # Setup:
    # File A imports B
    # File B has function "foo"
    # File C has function "foo"
    # File A calls "foo" -> Should trigger B::foo due to import

    fa = FileNode.create("a.py", "a.py")
    fb = FileNode.create("b.py", "b.py")

    foo_b = FunctionNode(
        id="B::foo",
        name="foo",
        file_path="b.py",
        node_type=NodeType.FUNCTION,
        line_start=1,
        line_end=2,
    )
    foo_c = FunctionNode(
        id="C::foo",
        name="foo",
        file_path="c.py",
        node_type=NodeType.FUNCTION,
        line_start=1,
        line_end=2,
    )

    caller = FunctionNode(
        id="A::main",
        name="main",
        file_path="a.py",
        node_type=NodeType.FUNCTION,
        line_start=1,
        line_end=5,
    )

    builder._add_node(fa)
    builder._add_node(fb)
    builder._add_node(foo_b)
    builder._add_node(foo_c)
    builder._add_node(caller)

    # Manually populate path map since we bypassed process_file
    builder._path_to_node_id["a.py"] = fa.id
    builder._path_to_node_id["b.py"] = fb.id

    # Add IMPORT edge: A imports foo_b (simulating "from b import foo")
    # In real graph, extractor adds this. We simulate it.
    builder._add_edge(Edge.create(fa.id, foo_b.id, EdgeType.IMPORTS))

    # Register pending call
    from codex_mesh.extractors.protocols import PendingCall

    builder._pending_calls.append(
        PendingCall(source_id="A::main", callee_name="foo", file_path="a.py", line=3)
    )

    builder._resolve_pending_calls()

    # Check edges from A::main
    caller_idx = builder._node_id_to_index["A::main"]
    foo_b_idx = builder._node_id_to_index["B::foo"]
    foo_c_idx = builder._node_id_to_index["C::foo"]

    # Should have edge to B::foo
    assert builder.graph.has_edge(caller_idx, foo_b_idx)
    # Should NOT have edge to C::foo (ambiguity resolved by import)
    assert not builder.graph.has_edge(caller_idx, foo_c_idx)


def test_query_helpers(builder):
    n1 = FileNode.create(path="a.py", relative_path="a.py", content_hash="1")
    n2 = FunctionNode(
        id="f1", name="f1", file_path="a.py", node_type=NodeType.FUNCTION, line_start=1, line_end=2
    )
    builder._add_node(n1)
    builder._add_node(n2)

    assert len(builder.get_files()) == 1
    assert len(builder.get_functions()) == 1
    assert builder.get_nodes_by_type(NodeType.FILE)[0].id == n1.id
