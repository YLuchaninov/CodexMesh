from unittest.mock import MagicMock

from codex_mesh.core.edges import Edge, EdgeType
from codex_mesh.core.nodes import DocSectionNode, FileNode, FunctionNode, NodeType
from codex_mesh.docs.audit import DocsAudit


def test_audit_stale_links():
    # Setup graph mock
    mock_graph = MagicMock()

    # Nodes
    doc_node = DocSectionNode(
        id="doc:1",
        name="My Doc",
        title="My Doc",
        level=1,
        content="...",
        file_path="docs/guide.md",
        line_start=1,
        line_end=10,
        node_type=NodeType.DOC_SECTION,
    )
    file_node = FileNode(
        id="file::src/code.py",
        name="code.py",
        path="/abs/src/code.py",
        relative_path="src/code.py",
        content_hash="abc",
        mtime=2000,
    )
    func_node = FunctionNode(
        id="func:1",
        name="my_func",
        file_path="src/code.py",
        line_start=10,
        line_end=20,
        node_type=NodeType.FUNCTION,
    )

    # Graph structure
    # doc_node -> documents -> func_node

    mock_graph.graph.nodes.return_value = [doc_node, file_node, func_node]
    mock_graph.get_all_nodes.return_value = [doc_node, file_node, func_node]

    # Mocks for get_node_by_id logic simulation in DocsAudit
    # But DocsAudit uses graph.get_node_by_id internally.
    def get_node_side_effect(nid):
        mapping = {doc_node.id: doc_node, file_node.id: file_node, func_node.id: func_node}
        return mapping.get(nid)

    mock_graph.get_node_by_id.side_effect = get_node_side_effect

    # Mock edges: out_edges(doc_node_idx)
    # let's say doc_node is index 0
    # func_node is index 2

    edge = Edge(source_id=doc_node.id, target_id=func_node.id, edge_type=EdgeType.DOCUMENTS)

    # Mock graph.graph object (rustworkx wrapper usually)
    # We need to mock .nodes() (iterable) and .out_edges(idx)
    # DocsAudit iterates enumerate(nodes)

    mock_graph.graph.out_edges.side_effect = lambda idx: [(0, 2, edge)] if idx == 0 else []
    mock_graph.graph.__getitem__.side_effect = lambda idx: [doc_node, file_node, func_node][idx]

    # Scenario 1: Doc is fresh (mtime 1000), Code is old (mtime 2000 - wait, code is newer means doc is stale)
    # Let's say doc mtime is derived from its file. ID format for doc file lookup?
    # DocsAudit uses file::doc_file_path to find mtime.

    # Case: Stale
    # Doc file mtime = 1000
    # Code file mtime = 2000 + stale_seconds + 1

    stale_days = 1
    auditor = DocsAudit(mock_graph, stale_days=stale_days)

    # We need to inject FileNodes for the doc file and code file so mtime lookup works
    doc_file_node = FileNode(
        id="file::docs/guide.md",
        name="guide.md",
        path="/abs/docs/guide.md",
        relative_path="docs/guide.md",
        content_hash="xyz",
        mtime=1000.0,
    )
    # Reuse code file node with mtime
    code_file_node = FileNode(
        id="file::src/code.py",
        name="code.py",
        path="/abs/src/code.py",
        relative_path="src/code.py",
        content_hash="abc",
        mtime=1000.0 + (86400 * 1.5),
    )  # 1.5 days newer

    mock_graph.get_all_nodes.return_value = [doc_node, func_node, doc_file_node, code_file_node]
    mock_graph.graph.nodes.return_value = [doc_node, func_node, doc_file_node, code_file_node]

    # Update manual mocking for getitem since list changed
    nodes_list = [doc_node, func_node, doc_file_node, code_file_node]
    mock_graph.graph.__getitem__.side_effect = lambda idx: nodes_list[idx]

    # Edge from doc (0) to func (1)
    mock_graph.graph.out_edges.side_effect = lambda idx: [(0, 1, edge)] if idx == 0 else []

    # Run audit
    issues = auditor.audit()

    assert len(issues) == 1
    assert issues[0]["doc_id"] == doc_node.id
    assert issues[0]["target_id"] == func_node.id


def test_audit_fresh_links():
    mock_graph = MagicMock()
    stale_days = 1
    auditor = DocsAudit(mock_graph, stale_days=stale_days)

    doc_node = DocSectionNode(
        id="doc:1",
        name="My Doc",
        title="My Doc",
        level=1,
        content="...",
        file_path="docs/guide.md",
        line_start=1,
        line_end=10,
        node_type=NodeType.DOC_SECTION,
    )
    func_node = FunctionNode(
        id="func:1",
        name="my_func",
        file_path="src/code.py",
        line_start=10,
        line_end=20,
        node_type=NodeType.FUNCTION,
    )

    # Doc is newer than code
    doc_file_node = FileNode(
        id="file::docs/guide.md",
        name="guide.md",
        path="/abs/docs/guide.md",
        relative_path="docs/guide.md",
        content_hash="xyz",
        mtime=2000.0,
    )
    code_file_node = FileNode(
        id="file::src/code.py",
        name="code.py",
        path="/abs/src/code.py",
        relative_path="src/code.py",
        content_hash="abc",
        mtime=1000.0,
    )

    mock_graph.get_all_nodes.return_value = [doc_node, func_node, doc_file_node, code_file_node]
    nodes_list = [doc_node, func_node, doc_file_node, code_file_node]
    mock_graph.graph.nodes.return_value = nodes_list
    mock_graph.graph.__getitem__.side_effect = lambda idx: nodes_list[idx]

    edge = Edge(source_id=doc_node.id, target_id=func_node.id, edge_type=EdgeType.DOCUMENTS)
    mock_graph.graph.out_edges.side_effect = lambda idx: [(0, 1, edge)] if idx == 0 else []

    def get_node_side_effect(nid):
        for n in nodes_list:
            if n.id == nid:
                return n
        return None

    mock_graph.get_node_by_id.side_effect = get_node_side_effect

    issues = auditor.audit()
    assert len(issues) == 0
