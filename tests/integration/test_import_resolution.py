import pytest

from codex_mesh.extractors.treesitter_query import QueryBundle, TreeSitterQueryExtractor


@pytest.fixture
def extractor_java():
    return TreeSitterQueryExtractor(
        language_id="java",
        extensions=(".java",),
        ts_lang_key="java",
        queries=QueryBundle(classes=None, functions=None, methods=None, imports=None),
    )


@pytest.fixture
def extractor_cpp():
    return TreeSitterQueryExtractor(
        language_id="cpp",
        extensions=(".cpp", ".h"),
        ts_lang_key="cpp",
        queries=QueryBundle(classes=None, functions=None, methods=None, imports=None),
    )


def test_import_resolution_java(extractor_java, tmp_path):
    project_root = tmp_path

    # Create struct:
    # src/com/example/Main.java
    # src/com/utils/Helper.java

    (project_root / "src/com/example").mkdir(parents=True)
    (project_root / "src/com/utils").mkdir(parents=True)

    (project_root / "src/com/example/Main.java").touch()
    (project_root / "src/com/utils/Helper.java").touch()

    # Test import com.utils.Helper
    cands, external = extractor_java._import_candidates(
        project_root / "src/com/example/Main.java", project_root, "com.utils.Helper"
    )

    assert not external
    assert len(cands) == 1
    assert cands[0] == "src/com/utils/Helper.java"


def test_import_resolution_cpp_local(extractor_cpp, tmp_path):
    project_root = tmp_path
    (project_root / "src").mkdir()
    (project_root / "src/main.cpp").touch()
    (project_root / "src/utils.h").touch()

    # #include "utils.h"
    cands, external = extractor_cpp._import_candidates(
        project_root / "src/main.cpp", project_root, "utils.h"
    )

    assert not external
    assert "src/utils.h" in cands


def test_import_resolution_cpp_system(extractor_cpp, tmp_path):
    # #include <iostream>
    cands, external = extractor_cpp._import_candidates(
        tmp_path / "main.cpp", tmp_path, "<iostream>"
    )
    assert external
    assert len(cands) == 0


@pytest.fixture
def extractor_rust():
    return TreeSitterQueryExtractor(
        language_id="rust",
        extensions=(".rs",),
        ts_lang_key="rust",
        queries=QueryBundle(classes=None, functions=None, methods=None, imports=None),
    )


def test_import_resolution_rust(extractor_rust, tmp_path):
    project_root = tmp_path
    (project_root / "src").mkdir()
    (project_root / "src/main.rs").touch()
    (project_root / "src/utils.rs").touch()

    # use crate::utils;
    cands, external = extractor_rust._import_candidates(
        project_root / "src/main.rs", project_root, "crate::utils"
    )

    assert not external
    assert "src/utils.rs" in cands


@pytest.fixture
def extractor_go():
    return TreeSitterQueryExtractor(
        language_id="go",
        extensions=(".go",),
        ts_lang_key="go",
        queries=QueryBundle(classes=None, functions=None, methods=None, imports=None),
    )


def test_import_resolution_go(extractor_go, tmp_path):
    project_root = tmp_path
    (project_root / "pkg").mkdir()
    (project_root / "pkg/util.go").touch()
    (project_root / "main.go").touch()

    # import "./pkg"
    cands, external = extractor_go._import_candidates(
        project_root / "main.go", project_root, "./pkg"
    )

    assert not external
    # We resolve to the file(s) in the package
    assert "pkg/util.go" in cands
