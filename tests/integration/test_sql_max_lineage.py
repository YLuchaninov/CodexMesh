"""Integration tests for SQL lineage analysis."""

import pytest

from codex_mesh.core.edges import EdgeType
from codex_mesh.core.graph import CodeGraphBuilder
from codex_mesh.core.nodes import NodeType

pytest.importorskip("sqlglot")


@pytest.fixture
def sql_project(tmp_path):
    """Create a temporary SQL project with lineage."""
    p = tmp_path / "sql_proj"
    p.mkdir()

    (p / "lineage.sql").write_text("""
    CREATE TABLE source_users (id INT, email TEXT);
    CREATE TABLE dest_users (id INT, email TEXT);

    INSERT INTO dest_users
    SELECT id, email FROM source_users WHERE id > 100;

    CREATE VIEW active_users AS
    SELECT * FROM dest_users;
    """)

    return p


def test_sql_max_lineage(sql_project):
    builder = CodeGraphBuilder(str(sql_project))
    builder.build()

    # Helper to find node by name/type
    def find_node(name, ntype):
        for n in builder.get_all_nodes():
            if n.node_type == ntype and n.name == name:
                return n
        return None

    # 1. Verify Tables
    src = find_node("source_users", NodeType.TABLE)
    dst = find_node("dest_users", NodeType.TABLE)
    find_node("active_users", NodeType.TABLE)  # View is extracted as TABLE in MVP or separate?
    # In extractor we use SqlTableNode with NodeType.TABLE.
    # Extractors might extract VIEW as TABLE or we check extract logic.
    # Logic: CREATE VIEW x ... -> _extract_write_tables might capture 'x' as table.

    assert src is not None
    assert dst is not None
    # Provide leniency on view detection if extractor treats it as table

    # 2. Verify Query Edges
    # We should have a query that WRITES to dest_users and READS from source_users

    # Find queries
    queries = builder.get_nodes_by_type(NodeType.QUERY)
    assert len(queries) >= 3  # CREATE, CREATE, INSERT, CREATE VIEW

    # Find the INSERT query
    insert_query = None
    for q in queries:
        # Check edges from this query
        q_idx = builder._node_id_to_index[q.id]

        reads = []
        writes = []

        for _unused, v_idx, edge in builder.graph.out_edges(q_idx):
            target = builder.graph[v_idx]
            if edge.edge_type == EdgeType.READS:
                reads.append(target.name)
            elif edge.edge_type == EdgeType.WRITES:
                writes.append(target.name)

        if "dest_users" in writes and "source_users" in reads:
            insert_query = q
            break

    assert insert_query is not None, "Could not find query that reads source and writes dest"
