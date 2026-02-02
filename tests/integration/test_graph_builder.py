"""Tests for code graph builder."""

import tempfile
from pathlib import Path

import pytest

from codex_mesh.core.edges import EdgeType
from codex_mesh.core.graph import CodeGraphBuilder


@pytest.fixture
def sample_project():
    """Create a temporary project with sample Python files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir)

        # Create sample files
        (project / "main.py").write_text('''
"""Main module."""

from utils import helper

def main():
    """Entry point."""
    result = helper()
    print(result)

class Application:
    """Main application class."""

    def __init__(self):
        self.name = "test"

    def run(self):
        """Run the application."""
        main()
''')

        (project / "utils.py").write_text('''
"""Utility functions."""

# TODO: Add more helpers

def helper():
    """A helper function."""
    return "Hello, World!"

def unused():
    """An unused function."""
    pass
''')

        yield project


def test_graph_builder_init(sample_project):
    """Test graph builder initialization."""
    builder = CodeGraphBuilder(str(sample_project))
    # Compare resolved paths to handle macOS symlinks (/var -> /private/var)
    assert builder.project_root.resolve() == sample_project.resolve()


def test_graph_builder_build(sample_project):
    """Test building the code graph."""
    builder = CodeGraphBuilder(str(sample_project))
    graph = builder.build()

    # Should have nodes
    assert graph.num_nodes() > 0

    # Check for file nodes
    files = builder.get_files()
    assert len(files) == 2
    file_names = {f.relative_path for f in files}
    assert "main.py" in file_names
    assert "utils.py" in file_names


def test_graph_builder_extracts_classes(sample_project):
    """Test that classes are extracted."""
    builder = CodeGraphBuilder(str(sample_project))
    builder.build()

    classes = builder.get_classes()
    assert len(classes) == 1
    assert classes[0].name == "Application"


def test_graph_builder_extracts_functions(sample_project):
    """Test that functions are extracted."""
    builder = CodeGraphBuilder(str(sample_project))
    builder.build()

    functions = builder.get_functions()
    func_names = {f.name for f in functions}

    assert "main" in func_names
    assert "helper" in func_names
    assert "unused" in func_names


def test_graph_has_edges(sample_project):
    """Test that edges are created between nodes."""
    builder = CodeGraphBuilder(str(sample_project))
    graph = builder.build()

    # Should have edges (contains relationships at minimum)
    assert graph.num_edges() > 0


def test_graph_extracts_calls(sample_project):
    """Test that function calls are extracted as edges."""
    # Create file with calls
    (sample_project / "calls.py").write_text("""
def callee():
    pass

def caller():
    callee()
""")

    builder = CodeGraphBuilder(str(sample_project))
    graph = builder.build()

    # Find nodes
    functions = builder.get_functions()
    caller = next(f for f in functions if f.name == "caller")
    callee = next(f for f in functions if f.name == "callee")

    # Check for edge
    caller_idx = builder._node_id_to_index[caller.id]
    callee_idx = builder._node_id_to_index[callee.id]

    edge_data = graph.get_edge_data(caller_idx, callee_idx)
    assert edge_data is not None
    assert edge_data.edge_type == EdgeType.CALLS
