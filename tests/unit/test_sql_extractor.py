from pathlib import Path

import pytest

from codex_mesh.core.edges import EdgeType
from codex_mesh.core.nodes import FileNode, NodeType
from codex_mesh.extractors.protocols import ExtractorContext
from codex_mesh.extractors.sqlglot_extractor import SqlGlotExtractor


def test_sql_extraction_simple():
    extractor = SqlGlotExtractor()
    content = "SELECT * FROM users WHERE id = 1; INSERT INTO logs (msg) VALUES ('test');"

    ctx = ExtractorContext(Path("."), Path("test.sql"), "test.sql")
    file_node = FileNode.create("test.sql", "test.sql")

    res = extractor.extract(ctx, file_node, content)

    # 2 queries + some tables/columns
    queries = [n for n in res.nodes if n.node_type == NodeType.QUERY]
    assert len(queries) == 2
    assert "SQL#1:SELECT" in [q.name for q in queries]
    assert "SQL#2:INSERT" in [q.name for q in queries]

    # Check tables
    tables = [n for n in res.nodes if n.node_type == NodeType.TABLE]
    assert any(t.name == "users" for t in tables)
    assert any(t.name == "logs" for t in tables)

    # Check edges
    # SELECT reads users
    reads_users = [e for e in res.edges if e.edge_type == EdgeType.READS]
    assert len(reads_users) >= 1

    # INSERT writes logs
    writes_logs = [e for e in res.edges if e.edge_type == EdgeType.WRITES]
    assert len(writes_logs) >= 1


def test_sql_extraction_complex():
    fixture_path = Path(__file__).parent.parent / "fixtures" / "langs" / "sql" / "schema.sql"
    if not fixture_path.exists():
        pytest.skip("SQL fixture not found")

    content = fixture_path.read_text()
    extractor = SqlGlotExtractor()
    ctx = ExtractorContext(fixture_path.parent, fixture_path, "schema.sql")
    file_node = FileNode.create("schema.sql", "schema.sql")

    res = extractor.extract(ctx, file_node, content)
    assert len(res.nodes) > 0

    tables = [n for n in res.nodes if n.node_type == NodeType.TABLE]
    assert any("users" in t.name.lower() for t in tables)
