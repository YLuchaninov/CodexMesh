"""
Unit tests for storage and vector search.
"""

from unittest.mock import MagicMock, patch

import pytest

from codex_mesh.core.nodes import FunctionNode
from codex_mesh.embeddings.engine import VectorSearch


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.embedding.model = "BAAI/bge-small-en-v1.5"
    config.embedding.chunk_size = 1000
    return config


@pytest.fixture
def vector_search(tmp_path, mock_config):
    """Create VectorSearch with a temporary DB path."""
    with patch("lancedb.connect") as mock_connect:
        mock_db = MagicMock()
        mock_connect.return_value = mock_db
        return VectorSearch(str(tmp_path / "vectordb"), mock_config)


def test_vector_search_init(vector_search, tmp_path):
    """Test initialization of VectorSearch."""
    assert vector_search.db_path == tmp_path / "vectordb"
    assert vector_search._model_name == "BAAI/bge-small-en-v1.5"


@patch("codex_mesh.embeddings.engine.VectorSearch._get_embedder")
def test_vector_search_index_codebase(mock_get_embedder, vector_search):
    """Test indexing code chunks from graph."""
    # Mock embedder
    mock_embedder = MagicMock()
    # Return a generator of embeddings (lists of floats)
    mock_embedder.embed.return_value = iter([[0.1] * 384])
    mock_get_embedder.return_value = mock_embedder

    # Mock graph builder
    mock_gb = MagicMock()
    node = FunctionNode(
        id="func::1",
        name="test_func",
        file_path="test.py",
        line_start=1,
        line_end=5,
        body="def test_func():\n    pass",
        decorators=[],
        args=[],
        return_type="None",
        docstring="Test docstring",
    )
    mock_gb.graph.nodes.return_value = [node]

    # Mock file reading
    with (
        patch("pathlib.Path.read_text", return_value="def test_func():\n    pass"),
        patch.object(vector_search._db, "create_table") as mock_create_table,
    ):
        vector_search.index_codebase(mock_gb, "/tmp/project")

        assert mock_create_table.called
        # Check that it was called with some data
        args, kwargs = mock_create_table.call_args
        assert args[0] == "code_chunks"
        assert len(args[1]) == 1
        assert args[1][0]["name"] == "test_func"
        assert "vector" in args[1][0]


@patch("codex_mesh.embeddings.engine.VectorSearch._get_embedder")
def test_vector_search_query(mock_get_embedder, vector_search):
    """Test semantic search query."""
    # Mock embedder
    mock_embedder = MagicMock()
    mock_embedder.embed.return_value = iter([[0.1] * 384])
    mock_get_embedder.return_value = mock_embedder

    # Mock table
    mock_table = MagicMock()
    vector_search._table = mock_table

    mock_query_res = MagicMock()
    mock_query_res.limit.return_value.to_list.return_value = [
        {
            "node_id": "func::1",
            "name": "test_func",
            "file_path": "test.py",
            "content": "some content",
            "line_start": 1,
            "line_end": 5,
            "_distance": 0.1,
        }
    ]
    mock_table.search.return_value = mock_query_res

    results = vector_search.search("find test")

    assert len(results) == 1
    assert results[0].node_id == "func::1"
    assert results[0].score == pytest.approx(1.0 / (1.0 + 0.1))  # 1.0 / (1.0 + distance)


def test_vector_search_has_index_true(tmp_path, mock_config):
    """Test has_index returns True when table exists."""
    with patch("lancedb.connect") as mock_connect:
        mock_db = MagicMock()
        mock_db.table_names.return_value = ["code_chunks"]
        mock_connect.return_value = mock_db

        vs = VectorSearch(str(tmp_path / "vectordb"), mock_config)

        assert vs.has_index() is True


def test_vector_search_has_index_false(tmp_path, mock_config):
    """Test has_index returns False when table doesn't exist."""
    with patch("lancedb.connect") as mock_connect:
        mock_db = MagicMock()
        mock_db.table_names.return_value = []
        mock_connect.return_value = mock_db

        vs = VectorSearch(str(tmp_path / "vectordb"), mock_config)

        assert vs.has_index() is False


def test_vector_search_has_index_different_tables(tmp_path, mock_config):
    """Test has_index returns False when other tables exist but not code_chunks."""
    with patch("lancedb.connect") as mock_connect:
        mock_db = MagicMock()
        mock_db.table_names.return_value = ["other_table", "another_table"]
        mock_connect.return_value = mock_db

        vs = VectorSearch(str(tmp_path / "vectordb"), mock_config)

        assert vs.has_index() is False
