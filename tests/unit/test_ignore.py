from pathlib import Path

import pytest

from codex_mesh.core.ignore import IgnoreMatcher


@pytest.fixture
def temp_project(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / "src").mkdir()
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "dist").mkdir()

    (tmp_path / ".codexignore").write_text("ignored.py\n#comment\n\nsecret_dir/")
    (tmp_path / "src" / "main.py").touch()
    (tmp_path / "src" / "ignored.py").touch()
    (tmp_path / "node_modules" / "lib.js").touch()
    return tmp_path


def test_default_ignores(temp_project):
    matcher = IgnoreMatcher.load(temp_project)

    # Should be ignored by defaults
    assert matcher.is_ignored(temp_project / ".git", is_dir=True)
    assert matcher.is_ignored(temp_project / "node_modules", is_dir=True)
    assert matcher.is_ignored(temp_project / "node_modules" / "lib.js", is_dir=False)
    assert matcher.is_ignored(temp_project / "__pycache__", is_dir=True)
    assert matcher.is_ignored(temp_project / "dist", is_dir=True)

    # Should not be ignored
    assert not matcher.is_ignored(temp_project / "src" / "main.py", is_dir=False)


def test_custom_codexignore_rules(temp_project):
    matcher = IgnoreMatcher.load(temp_project)

    # "ignored.py" is in .codexignore
    assert matcher.is_ignored(temp_project / "ignored.py", is_dir=False)
    assert matcher.is_ignored(
        temp_project / "src" / "ignored.py", is_dir=False
    )  # gitignore is usually recursive unless anchored

    # secret_dir/
    assert matcher.is_ignored(temp_project / "secret_dir", is_dir=True)

    # comments and empty lines skipped
    assert not matcher.is_ignored(temp_project / "#comment", is_dir=False)


def test_nested_paths_resolution(temp_project):
    matcher = IgnoreMatcher.load(temp_project)

    # passing child path to is_ignored
    child_file = temp_project / "node_modules" / "pkg" / "index.js"
    assert matcher.is_ignored(child_file)


def test_extra_patterns(temp_project):
    matcher = IgnoreMatcher.load(temp_project, extra_patterns=["*.tmp"])

    (temp_project / "test.tmp").touch()
    assert matcher.is_ignored(temp_project / "test.tmp")


def test_absolute_vs_relative_paths(temp_project):
    matcher = IgnoreMatcher.load(temp_project)

    abs_path = temp_project / "node_modules"
    assert matcher.is_ignored(abs_path, is_dir=True)

    # If we pass a relative path (relative to cwd, which might match root), it should work if we construct it carefully
    # But IgnoreMatcher expects full path or path relative to root.
    # If we pass a path object that is already relative 'node_modules',
    # the code `path.relative_to(root)` will fail if root is absolute.
    # Let's see how `is_ignored` handles strictly relative paths that don't share root.

    rel_path = Path("node_modules")
    # This might tricky depending on implementation.
    # Our impl: if path.is_absolute() -> relative_to(root). else -> as_posix()
    assert matcher.is_ignored(rel_path, is_dir=True)
