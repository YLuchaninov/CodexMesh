"""
SQL extractor with "maximum useful MVP" semantics using sqlglot.

Outputs:
- Table/Column nodes
- Query nodes (one per statement)
- Edges: FILE->QUERY (CONTAINS), QUERY->TABLE (READS/WRITES), QUERY->COLUMN (REFERENCES)
"""

from __future__ import annotations

from hashlib import md5

import sqlglot
from sqlglot import exp

from codex_mesh.core.edges import Edge, EdgeType
from codex_mesh.core.nodes import (  # unused but keeps import style consistent
    BaseNode,
    FileNode,
    NodeType,
)

from .protocols import ExtractionResult, ExtractorContext


class SqlQueryNode(BaseNode):
    """Represents a single SQL statement/query in a file."""

    node_type: NodeType = NodeType.QUERY
    file_path: str = ""
    statement_type: str = ""
    ordinal: int = 0


class SqlTableNode(BaseNode):
    """Represents a SQL table."""

    node_type: NodeType = NodeType.TABLE
    full_name: str = ""


class SqlColumnNode(BaseNode):
    """Represents a SQL column."""

    node_type: NodeType = NodeType.COLUMN
    full_name: str = ""


class SqlGlotExtractor:
    language_id: str = "sql"
    extensions: tuple[str, ...] = (".sql",)

    def extract(self, ctx: ExtractorContext, file_node: FileNode, content: str) -> ExtractionResult:
        try:
            statements = sqlglot.parse(content)  # list[Expression]
        except Exception:
            return ExtractionResult(nodes=[], edges=[], pending_imports=[], pending_calls=[])

        nodes: list[BaseNode] = []
        edges: list[Edge] = []

        # Interning maps to avoid duplicates
        table_by_name: dict[str, SqlTableNode] = {}
        col_by_name: dict[str, SqlColumnNode] = {}

        for i, st in enumerate(statements, start=1):
            if st is None:
                continue
            st_type = st.key.upper()
            qid = self._query_id(ctx.relative_path, i, st.sql())
            qnode = SqlQueryNode(
                id=qid,
                name=f"SQL#{i}:{st_type}",
                node_type=NodeType.QUERY,
                file_path=ctx.relative_path,
                statement_type=st_type,
                ordinal=i,
            )
            nodes.append(qnode)
            edges.append(Edge.create(file_node.id, qnode.id, EdgeType.CONTAINS))

            # Detect write targets (INSERT/CREATE/UPDATE/DELETE/MERGE etc.)
            write_tables = self._extract_write_tables(st)
            for t in write_tables:
                tnode = table_by_name.get(t) or self._mk_table(t, table_by_name, nodes)
                edges.append(Edge.create(qnode.id, tnode.id, EdgeType.WRITES))

            # Detect read sources (Tables used in FROM/JOIN etc.)
            read_tables = self._extract_read_tables(st)
            for t in read_tables:
                tnode = table_by_name.get(t) or self._mk_table(t, table_by_name, nodes)
                edges.append(Edge.create(qnode.id, tnode.id, EdgeType.READS))

            # Columns (best-effort, qualified where possible)
            for col in st.find_all(exp.Column):
                col_name = col.sql(dialect=None)
                cnode = col_by_name.get(col_name) or self._mk_col(col_name, col_by_name, nodes)
                edges.append(Edge.create(qnode.id, cnode.id, EdgeType.REFERENCES))

        return ExtractionResult(nodes=nodes, edges=edges, pending_imports=[], pending_calls=[])

    def _query_id(self, rel_path: str, ordinal: int, sql_text: str) -> str:
        h = md5(sql_text.encode("utf-8")).hexdigest()[:10]
        return f"query::{rel_path}::{ordinal}::{h}"

    def _mk_table(
        self, full_name: str, cache: dict[str, SqlTableNode], nodes: list[BaseNode]
    ) -> SqlTableNode:
        nid = f"table::{full_name}"
        node = SqlTableNode(id=nid, name=full_name, node_type=NodeType.TABLE, full_name=full_name)
        cache[full_name] = node
        nodes.append(node)
        return node

    def _mk_col(
        self, full_name: str, cache: dict[str, SqlColumnNode], nodes: list[BaseNode]
    ) -> SqlColumnNode:
        nid = f"column::{full_name}"
        node = SqlColumnNode(id=nid, name=full_name, node_type=NodeType.COLUMN, full_name=full_name)
        cache[full_name] = node
        nodes.append(node)
        return node

    def _extract_read_tables(self, st: exp.Expression) -> set[str]:
        out: set[str] = set()
        for t in st.find_all(exp.Table):
            name = self._table_name(t)
            if name:
                out.add(name)
        return out

    def _extract_write_tables(self, st: exp.Expression) -> set[str]:
        out: set[str] = set()

        # INSERT INTO x ...
        for ins in st.find_all(exp.Insert):
            tbl = ins.this
            if isinstance(tbl, (exp.Table, exp.Schema)):
                name = self._table_name(tbl)
                if name:
                    out.add(name)

        # CREATE TABLE x AS ...
        for cr in st.find_all(exp.Create):
            tbl = cr.this
            if isinstance(tbl, (exp.Table, exp.Schema)):
                name = self._table_name(tbl)
                if name:
                    out.add(name)

        # UPDATE x SET ...
        for upd in st.find_all(exp.Update):
            tbl = upd.this
            if isinstance(tbl, (exp.Table, exp.Schema)):
                name = self._table_name(tbl)
                if name:
                    out.add(name)

        # DELETE FROM x ...
        for dele in st.find_all(exp.Delete):
            tbl = dele.this
            if isinstance(tbl, (exp.Table, exp.Schema)):
                name = self._table_name(tbl)
                if name:
                    out.add(name)

        return out

    def _table_name(self, t: exp.Table | exp.Schema) -> str | None:
        if isinstance(t, exp.Schema):
            t = t.this
        if not isinstance(t, exp.Table):
            return None
        # Prefer fully qualified if present
        catalog = (t.catalog or "").strip()
        db = (t.db or "").strip()
        name = (t.name or "").strip()
        if not name:
            return None
        parts = [p for p in (catalog, db, name) if p]
        return ".".join(parts)
