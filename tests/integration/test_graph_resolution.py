from unittest.mock import MagicMock

import pytest

from codex_mesh.core.edges import EdgeType
from codex_mesh.core.graph import CodeGraphBuilder
from codex_mesh.core.nodes import FileNode, FunctionNode
from codex_mesh.extractors.protocols import PendingCall

# We mock the extractor to return specific nodes and pending calls
# so we can test the RESOLUTION logic in isolation from parsing.


@pytest.fixture
def mock_registry():
    reg = MagicMock()
    return reg


def test_resolution_priority_same_file(mock_registry, tmp_path):
    # Setup:
    # File A: contains func foo() and calls foo()
    # File B: contains func foo()
    # Expectation: Call in A links to A.foo

    project_root = tmp_path

    # We manually hydrate the builder
    builder = CodeGraphBuilder(str(project_root), registry=mock_registry)

    # Node definition
    file_a = FileNode.create("A.py", "A.py")
    file_b = FileNode.create("B.py", "B.py")

    foo_a = FunctionNode.create("foo", "A.py", 1, 2)
    foo_b = FunctionNode.create("foo", "B.py", 1, 2)

    # Add nodes to graph
    builder._add_node(file_a)
    builder._add_node(file_b)
    builder._add_node(foo_a)
    builder._add_node(foo_b)

    # Register pending call from A
    call = PendingCall(
        source_id=foo_a.id,  # recursive call or just call from A
        callee_name="foo",
        file_path="A.py",
        line=5,
    )
    builder._pending_calls.append(call)

    # Resolve
    builder._resolve_pending_calls()

    # Verify edge
    edges = list(builder.graph.out_edges(builder._node_id_to_index[foo_a.id]))
    calls_edges = [e for u, v, e in edges if e.edge_type == EdgeType.CALLS]

    assert len(calls_edges) == 1
    target_idx = builder.graph.out_edges(builder._node_id_to_index[foo_a.id])[0][1]
    target_node = builder.graph[target_idx]

    assert target_node.id == foo_a.id  # Should point to self (A.foo)


def test_resolution_priority_same_class(mock_registry, tmp_path):
    # Setup:
    # File A:
    #   class C:
    #      method bar()
    #      method test() -> calls bar()
    #
    # File B:
    #   func bar()
    #
    # Expectation: C.test() calls C.bar(), not global bar()

    project_root = tmp_path
    builder = CodeGraphBuilder(str(project_root), registry=mock_registry)

    file_a = FileNode.create("A.py", "A.py")

    # Class C methods
    bar_method = FunctionNode.create("bar", "A.py", 10, 11, is_method=True, class_name="C")
    test_method = FunctionNode.create("test", "A.py", 20, 21, is_method=True, class_name="C")

    # Global bar in B
    bar_global = FunctionNode.create("bar", "B.py", 1, 2)

    builder._add_node(file_a)
    builder._add_node(bar_method)
    builder._add_node(test_method)
    builder._add_node(bar_global)

    # Call from C.test to "bar"
    call = PendingCall(source_id=test_method.id, callee_name="bar", file_path="A.py", line=21)
    builder._pending_calls.append(call)

    builder._resolve_pending_calls()

    # Verify edge from test_method
    s_idx = builder._node_id_to_index[test_method.id]
    edges = []
    for _u, v, e in builder.graph.out_edges(s_idx):
        if e.edge_type == EdgeType.CALLS:
            edges.append(builder.graph[v])

    assert len(edges) == 1
    assert edges[0].id == bar_method.id
