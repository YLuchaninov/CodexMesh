"""
Unit tests for CodexMeshServer instance.

Tests server initialization, graph loading, conditional indexing,
and component orchestration.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from codex_mesh.api.instance import CodexMeshServer
from codex_mesh.core.context import AppContext


@pytest.fixture
def mock_context():
    """Create a mock AppContext with config."""
    context = MagicMock(spec=AppContext)
    context.config = MagicMock()
    context.config.storage.path = "/tmp/codex_mesh"
    context.config.embedding.model = "BAAI/bge-small-en-v1.5"
    return context


@pytest.fixture
def temp_project():
    """Create a temporary project directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir)
        # Create a simple Python file
        (project / "main.py").write_text("def main():\n    pass\n")
        yield str(project)


class TestServerInit:
    """Tests for CodexMeshServer initialization."""

    @patch("codex_mesh.api.instance.VectorSearch")
    @patch("codex_mesh.api.instance.HotspotCalculator")
    @patch("codex_mesh.api.instance.CodeGraphBuilder")
    def test_init_creates_components(
        self, mock_builder, mock_hotspot, mock_vector, temp_project, mock_context
    ):
        """Test that initialization creates all components."""
        server = CodexMeshServer(temp_project, mock_context)

        assert server.graph_builder is not None
        assert server.hotspot_calc is not None
        assert server.vector_search is not None

    @patch("codex_mesh.api.instance.VectorSearch")
    @patch("codex_mesh.api.instance.HotspotCalculator")
    @patch("codex_mesh.api.instance.CodeGraphBuilder")
    def test_init_validates_project_root(
        self, mock_builder, mock_hotspot, mock_vector, mock_context
    ):
        """Test that non-existent project root raises error."""
        with pytest.raises(ValueError, match="does not exist"):
            CodexMeshServer("/nonexistent/path", mock_context)

    @patch("codex_mesh.api.instance.VectorSearch")
    @patch("codex_mesh.api.instance.HotspotCalculator")
    @patch("codex_mesh.api.instance.CodeGraphBuilder")
    def test_init_rejects_file_as_root(self, mock_builder, mock_hotspot, mock_vector, mock_context):
        """Test that file as project root raises error."""
        with tempfile.NamedTemporaryFile() as f, pytest.raises(ValueError, match="not a directory"):
            CodexMeshServer(f.name, mock_context)

    @patch("codex_mesh.api.instance.VectorSearch")
    @patch("codex_mesh.api.instance.HotspotCalculator")
    @patch("codex_mesh.api.instance.CodeGraphBuilder")
    def test_init_not_initialized_flag(
        self, mock_builder, mock_hotspot, mock_vector, temp_project, mock_context
    ):
        """Test that server starts as not initialized."""
        server = CodexMeshServer(temp_project, mock_context)

        assert server._initialized is False


class TestServerInitialize:
    """Tests for the initialize method."""

    @patch("codex_mesh.api.instance.VectorSearch")
    @patch("codex_mesh.api.instance.HotspotCalculator")
    @patch("codex_mesh.api.instance.CodeGraphBuilder")
    @patch("codex_mesh.api.instance.RepoMapGenerator")
    @patch("codex_mesh.api.instance.GraphSearch")
    def test_initialize_builds_graph_when_no_snapshot(
        self, mock_search, mock_repomap, mock_builder, mock_hotspot, mock_vector, mock_context
    ):
        """Test that initialize builds graph when no snapshot exists."""
        # Create a real temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            (project / "main.py").write_text("def main(): pass")

            mock_builder_instance = mock_builder.return_value
            mock_builder_instance.build.return_value = MagicMock()
            mock_builder_instance.get_files.return_value = []
            mock_builder_instance.get_classes.return_value = []
            mock_builder_instance.get_functions.return_value = []
            mock_builder_instance.graph.num_nodes.return_value = 5
            mock_builder_instance.graph.num_edges.return_value = 3
            mock_builder_instance.load_snapshot.return_value = False

            mock_vector_instance = mock_vector.return_value
            mock_vector_instance.has_index.return_value = False
            mock_vector_instance.index_codebase.return_value = 10

            server = CodexMeshServer(str(project), mock_context)
            # Override snapshot path to non-existent
            server.snapshot_path = project / "nonexistent_snapshot.json"

            server.initialize()

            mock_builder_instance.build.assert_called_once()

    @patch("codex_mesh.api.instance.VectorSearch")
    @patch("codex_mesh.api.instance.HotspotCalculator")
    @patch("codex_mesh.api.instance.CodeGraphBuilder")
    @patch("codex_mesh.api.instance.RepoMapGenerator")
    @patch("codex_mesh.api.instance.GraphSearch")
    def test_initialize_loads_snapshot_when_exists(
        self, mock_search, mock_repomap, mock_builder, mock_hotspot, mock_vector, mock_context
    ):
        """Test that initialize loads snapshot when available."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            (project / "main.py").write_text("def main(): pass")

            # Create a fake snapshot file
            snapshot_file = project / "snapshot.json"
            snapshot_file.write_text("{}")

            mock_builder_instance = mock_builder.return_value
            mock_builder_instance.load_snapshot.return_value = True  # Snapshot loads successfully
            mock_builder_instance.get_files.return_value = []
            mock_builder_instance.graph.num_nodes.return_value = 5
            mock_builder_instance.graph.num_edges.return_value = 3

            mock_vector_instance = mock_vector.return_value
            mock_vector_instance.has_index.return_value = True

            server = CodexMeshServer(str(project), mock_context)
            server.snapshot_path = snapshot_file  # Point to existing file

            server.initialize()

            # Build should NOT be called when snapshot loads
            mock_builder_instance.build.assert_not_called()

    @patch("codex_mesh.api.instance.VectorSearch")
    @patch("codex_mesh.api.instance.HotspotCalculator")
    @patch("codex_mesh.api.instance.CodeGraphBuilder")
    @patch("codex_mesh.api.instance.RepoMapGenerator")
    @patch("codex_mesh.api.instance.GraphSearch")
    def test_initialize_skips_index_when_loaded_and_exists(
        self, mock_search, mock_repomap, mock_builder, mock_hotspot, mock_vector, mock_context
    ):
        """Test that initialize skips indexing if index exists and snapshot loaded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            (project / "main.py").write_text("def main(): pass")

            snapshot_file = project / "snapshot.json"
            snapshot_file.write_text("{}")

            mock_builder_instance = mock_builder.return_value
            mock_builder_instance.load_snapshot.return_value = True
            mock_builder_instance.get_files.return_value = []
            mock_builder_instance.graph.num_nodes.return_value = 5
            mock_builder_instance.graph.num_edges.return_value = 3

            mock_vector_instance = mock_vector.return_value
            mock_vector_instance.has_index.return_value = True  # Index exists

            server = CodexMeshServer(str(project), mock_context)
            server.snapshot_path = snapshot_file

            server.initialize()

            # index_codebase should NOT be called
            mock_vector_instance.index_codebase.assert_not_called()

    @patch("codex_mesh.api.instance.VectorSearch")
    @patch("codex_mesh.api.instance.HotspotCalculator")
    @patch("codex_mesh.api.instance.CodeGraphBuilder")
    @patch("codex_mesh.api.instance.RepoMapGenerator")
    @patch("codex_mesh.api.instance.GraphSearch")
    def test_initialize_indexes_when_no_index(
        self, mock_search, mock_repomap, mock_builder, mock_hotspot, mock_vector, mock_context
    ):
        """Test that initialize indexes when no index exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            (project / "main.py").write_text("def main(): pass")

            snapshot_file = project / "snapshot.json"
            snapshot_file.write_text("{}")

            mock_builder_instance = mock_builder.return_value
            mock_builder_instance.load_snapshot.return_value = True
            mock_builder_instance.get_files.return_value = []
            mock_builder_instance.graph.num_nodes.return_value = 5
            mock_builder_instance.graph.num_edges.return_value = 3

            mock_vector_instance = mock_vector.return_value
            mock_vector_instance.has_index.return_value = False  # No index
            mock_vector_instance.index_codebase.return_value = 10

            server = CodexMeshServer(str(project), mock_context)
            server.snapshot_path = snapshot_file

            server.initialize()

            # index_codebase SHOULD be called
            mock_vector_instance.index_codebase.assert_called_once()

    @patch("codex_mesh.api.instance.VectorSearch")
    @patch("codex_mesh.api.instance.HotspotCalculator")
    @patch("codex_mesh.api.instance.CodeGraphBuilder")
    @patch("codex_mesh.api.instance.RepoMapGenerator")
    @patch("codex_mesh.api.instance.GraphSearch")
    def test_initialize_is_idempotent(
        self, mock_search, mock_repomap, mock_builder, mock_hotspot, mock_vector, mock_context
    ):
        """Test that calling initialize twice doesn't re-initialize."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            (project / "main.py").write_text("def main(): pass")

            snapshot_file = project / "snapshot.json"
            snapshot_file.write_text("{}")

            mock_builder_instance = mock_builder.return_value
            mock_builder_instance.load_snapshot.return_value = True
            mock_builder_instance.get_files.return_value = []
            mock_builder_instance.graph.num_nodes.return_value = 5
            mock_builder_instance.graph.num_edges.return_value = 3

            mock_vector.return_value.has_index.return_value = True

            server = CodexMeshServer(str(project), mock_context)
            server.snapshot_path = snapshot_file

            server.initialize()
            server.initialize()  # Second call

            # GraphSearch should only be created once
            assert mock_search.call_count == 1


class TestGetStats:
    """Tests for get_stats method."""

    @patch("codex_mesh.api.instance.VectorSearch")
    @patch("codex_mesh.api.instance.HotspotCalculator")
    @patch("codex_mesh.api.instance.CodeGraphBuilder")
    def test_get_stats_returns_counts(
        self, mock_builder, mock_hotspot, mock_vector, temp_project, mock_context
    ):
        """Test that get_stats returns correct counts."""
        mock_builder_instance = mock_builder.return_value

        mock_file = MagicMock()
        mock_class = MagicMock()
        mock_func = MagicMock()

        mock_builder_instance.get_files.return_value = [mock_file] * 5
        mock_builder_instance.get_classes.return_value = [mock_class] * 3
        mock_builder_instance.get_functions.return_value = [mock_func] * 10
        mock_builder_instance.graph.num_nodes.return_value = 18
        mock_builder_instance.graph.num_edges.return_value = 25

        server = CodexMeshServer(temp_project, mock_context)
        stats = server.get_stats()

        assert stats["files"] == 5
        assert stats["classes"] == 3
        assert stats["functions"] == 10
        assert stats["total_nodes"] == 18
        assert stats["total_edges"] == 25
