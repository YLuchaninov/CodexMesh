from unittest.mock import MagicMock

import pytest
import rustworkx as rx

from codex_mesh.core.edges import Edge, EdgeType
from codex_mesh.core.graph import CodeGraphBuilder
from codex_mesh.core.nodes import FunctionNode
from codex_mesh.storage.search import GraphSearch


@pytest.fixture
def graph_search_with_chain():
    """Create a GraphSearch with a chain of nodes A->B->C->D."""
    builder = MagicMock(spec=CodeGraphBuilder)
    graph = rx.PyDiGraph()

    nodes = []
    for _i, name in enumerate(["A", "B", "C", "D"]):
        node = FunctionNode(
            id=name, name=name, file_path=f"{name}.py", line_start=1, line_end=10, docstring=""
        )
        idx = graph.add_node(node)
        nodes.append((name, idx, node))

    # A->B->C->D
    # hops: A->B (1), A->C (2), A->D (3)
    graph.add_edge(
        nodes[0][1], nodes[1][1], Edge(source_id="A", target_id="B", edge_type=EdgeType.CALLS)
    )
    graph.add_edge(
        nodes[1][1], nodes[2][1], Edge(source_id="B", target_id="C", edge_type=EdgeType.CALLS)
    )
    graph.add_edge(
        nodes[2][1], nodes[3][1], Edge(source_id="C", target_id="D", edge_type=EdgeType.CALLS)
    )

    builder.graph = graph
    builder._node_id_to_index = {n[0]: n[1] for n in nodes}

    return GraphSearch(builder)


def test_find_path_max_hops_success(graph_search_with_chain):
    """Test finding path within max_hops limit."""
    # A -> C is 2 hops. max_hops=2 should find it.
    path = graph_search_with_chain.find_path("A", "C", max_hops=2)
    assert path is not None
    assert len(path) == 3  # [A, B, C]
    assert path[0].id == "A"
    assert path[2].id == "C"


def test_find_path_max_hops_failure(graph_search_with_chain):
    """Test failing to find path when limit is too low."""
    # A -> C is 2 hops. max_hops=1 should fail.
    path = graph_search_with_chain.find_path("A", "C", max_hops=1)
    assert path is None


def test_find_path_default_hops(graph_search_with_chain):
    """Test default max_hops (should find path)."""
    path = graph_search_with_chain.find_path("A", "D")
    assert path is not None
    assert len(path) == 4  # [A, B, C, D]
