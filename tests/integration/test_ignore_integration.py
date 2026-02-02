import pytest

from codex_mesh.core.graph import CodeGraphBuilder
from codex_mesh.services.fs_service import FileSystemService


# Dummy mock for ProjectManager/Server because FS Service expects it
class MockServer:
    def __init__(self, root):
        self.project_root = root


class MockManager:
    def __init__(self, root):
        self.server = MockServer(root)


@pytest.fixture
def integration_project(tmp_path):
    # Setup similar to unit test but for full components
    project = tmp_path / "project"
    project.mkdir()
    (project / ".git").mkdir()
    (project / "src").mkdir()
    (project / "node_modules").mkdir()
    (project / "node_modules" / "pkg").mkdir()

    (project / ".codexignore").write_text("ignored_file.py\nignored_dir/\nnode_modules/")

    (project / "src" / "main.py").touch()
    (project / "src" / "ignored_file.py").touch()
    (project / "ignored_dir").mkdir()
    (project / "ignored_dir" / "secret.txt").touch()
    (project / "node_modules" / "pkg" / "lib.js").touch()
    (project / "should_see.py").touch()

    return project


def test_graph_builder_ignores(integration_project):
    # Test that graph builder doesn't index ignored files
    builder = CodeGraphBuilder(str(integration_project))

    # We can inspect _discover_files directly or build the graph
    # _discover_files is easier to check
    files = builder._discover_files(exclude_patterns=[])

    file_names = {p.name for p in files}

    assert "main.py" in file_names
    assert "should_see.py" in file_names

    assert "ignored_file.py" not in file_names
    assert "secret.txt" not in file_names
    assert "lib.js" not in file_names  # node_modules ignored


def test_fs_service_ignores(integration_project):
    # Test FS Service filtering
    pm = MockManager(integration_project)
    fs = FileSystemService(pm)

    # 1. List root
    # Should not see ignored_dir or node_modules or ignored_file.py
    listing = fs.list_directory_structured(".", recursive=True)
    paths = {item["path"] for item in listing}

    assert "src/main.py" in paths
    assert "should_see.py" in paths

    assert "src/ignored_file.py" not in paths
    assert "ignored_dir/secret.txt" not in paths
    assert "node_modules/pkg/lib.js" not in paths

    # 2. List ignored dir directly - implicit behavior check
    # If we try to list "node_modules", what happens?
    # If include_ignored=False (default), entries inside should be hidden OR
    # if the dir itself is ignored, it might be empty or error?
    # Current impl: list_directory_structured iterates contents. content "pkg" matches ignore "node_modules/"?
    # Wait, "node_modules/" matches the dir node_modules. Use inside node_modules: "node_modules/pkg".
    # Should be ignored.

    # With include_ignored=False
    try:
        sub = fs.list_directory_structured("node_modules")
        # should be empty if all children match?
        # Or maybe the loop filters children.
        # "pkg" path is "node_modules/pkg". Matches "node_modules/".
        assert len(sub) == 0
    except (ValueError, PermissionError):
        pass  # Acceptable if we block access to ignored dirs

    # 3. Read ignored file
    with pytest.raises(PermissionError):
        fs.read_file("src/ignored_file.py")

    with pytest.raises(PermissionError):
        fs.read_file_raw("node_modules/pkg/lib.js")


def test_fs_service_include_ignored(integration_project):
    pm = MockManager(integration_project)
    fs = FileSystemService(pm)

    # List with include_ignored=True
    listing = fs.list_directory_structured(".", recursive=True, include_ignored=True)
    paths = {item["path"] for item in listing}

    assert "src/ignored_file.py" in paths
    assert "node_modules/pkg/lib.js" in paths

    # Note: read_file currently has NO override parameter.
    # API design says: "Include ignore filter... read_file / read_file_raw... PermissionError".
    # It didn't specify 'read_file(force=True)'.
    # So even with include_ignored=True in list, you can't read it via standard API?
    # The requirement: "Important, so that LLM/instruments do not drag gigabyte... files."
    # If user INTENDS to read it, they might need a way.
    # But for now, we follow the spec "read_file throws PermissionError".
    pass
