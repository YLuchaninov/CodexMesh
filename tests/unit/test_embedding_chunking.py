from unittest.mock import MagicMock, patch

import pytest

from codex_mesh.core.nodes import FileNode, FunctionNode, NodeType
from codex_mesh.embeddings.engine import VectorSearch


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.embedding.model = "BAAI/bge-small-en-v1.5"
    config.embedding.chunk_size = 1000
    return config


@pytest.fixture
def vector_search(tmp_path, mock_config):
    with patch("lancedb.connect") as mock_connect:
        mock_db = MagicMock()
        mock_connect.return_value = mock_db
        return VectorSearch(str(tmp_path / "vectordb"), mock_config)


@patch("codex_mesh.embeddings.engine.VectorSearch._get_embedder")
def test_index_file_overview(mock_get_embedder, vector_search):
    # Mock embedder
    mock_embedder = MagicMock()
    mock_embedder.embed.return_value = iter([[0.1] * 384] * 2)  # Two chunks: file + func
    mock_get_embedder.return_value = mock_embedder

    # Setup Graph
    mock_gb = MagicMock()

    file_node = FileNode(
        id="file::src/main.py",
        name="src/main.py",
        path="/abs/src/main.py",
        relative_path="src/main.py",
        node_type=NodeType.FILE,
    )

    func_node = FunctionNode(
        id="func::src/main.py::main",
        name="main",
        file_path="src/main.py",
        line_start=1,
        line_end=5,
        node_type=NodeType.FUNCTION,
        signature="def main():",
    )

    # Graph.nodes() iterator
    mock_gb.graph.nodes.return_value = [file_node, func_node]

    # Mock file reading
    file_content = '"""Module docstring."""\nimport os\n\n# ... lines ...\n\ndef main():\n    pass'

    # We need to mock Path.read_text. Since _get_file_overview uses project_root / relative_path
    # We'll use pyfakefs or just patch pathlib.Path.read_text directly for simplicity.
    with (
        patch("pathlib.Path.read_text", return_value=file_content),
        patch.object(vector_search._db, "create_table") as mock_create_table,
    ):
        count = vector_search.index_codebase(mock_gb, "/abs")

        assert count == 2  # 1 file + 1 function
        assert mock_create_table.called

        # Check args passed to create_table
        # Check args passed to create_table
        args, _ = mock_create_table.call_args
        # table_name = args[0]  # Unused
        chunks = args[1]

        assert len(chunks) == 2

        # Find file chunk
        file_chunk = next((c for c in chunks if c["node_type"] == "file"), None)
        assert file_chunk is not None
        assert file_chunk["node_id"] == "file::src/main.py"
        # Check content includes docstring
        assert "Module docstring" in file_chunk["content"]
        # Check content includes definition summary
        assert "# Definitions in this file:" in file_chunk["content"]
        assert "# - def main():" in file_chunk["content"]
