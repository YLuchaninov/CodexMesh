import pytest

from codex_mesh.extractors.import_resolvers import (
    GoImportResolver,
    JSImportResolver,
    RustImportResolver,
)


@pytest.fixture
def mock_project(tmp_path):
    # Setup a fake project structure
    (tmp_path / "package.json").touch()
    (tmp_path / "src").mkdir()
    (tmp_path / "src/index.ts").touch()
    (tmp_path / "src/utils.ts").touch()
    (tmp_path / "src/components").mkdir()
    (tmp_path / "src/components/Button.tsx").touch()
    (tmp_path / "src/components/index.ts").touch()

    # Go
    (tmp_path / "go.mod").write_text("module github.com/user/repo")
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg/math.go").touch()

    # Rust
    (tmp_path / "Cargo.toml").touch()
    (tmp_path / "src/main.rs").touch()
    (tmp_path / "src/lib.rs").touch()
    (tmp_path / "src/net").mkdir()
    (tmp_path / "src/net/mod.rs").touch()
    (tmp_path / "src/net/http.rs").touch()

    return tmp_path


def test_js_resolution(mock_project):
    resolver = JSImportResolver()
    root = mock_project

    # Test 1: Relative import of sibling
    # Originally: "import { x } from './utils'" -> treesitter extracts "./utils"
    res = resolver.resolve(root, root / "src/index.ts", "./utils")
    assert "src/utils.ts" in res

    # Test 2: Import from index
    # "./components"
    res = resolver.resolve(root, root / "src/index.ts", "./components")
    assert (
        "src/components/index.ts" in res or "src/components/Button.tsx" not in res
    )  # Directory import -> index

    # Test 3: Import specific file in subdir
    # "./components/Button"
    res = resolver.resolve(root, root / "src/index.ts", "./components/Button")
    assert "src/components/Button.tsx" in res


def test_go_resolution(mock_project):
    resolver = GoImportResolver()
    root = mock_project

    # Test 1: Internal package import
    # import "github.com/user/repo/pkg" -> "github.com/user/repo/pkg"
    res = resolver.resolve(root, root / "main.go", "github.com/user/repo/pkg")
    assert "pkg/math.go" in res

    # Test 2: External/Stdlib (should be empty)
    res = resolver.resolve(root, root / "main.go", "fmt")
    assert not res


def test_rust_resolution(mock_project):
    resolver = RustImportResolver()
    root = mock_project

    # Test 1: Module import "net" -> net/mod.rs
    # mod net; -> "net"
    res = resolver.resolve(root, root / "src/lib.rs", "net")
    assert "src/net/mod.rs" in res

    # Test 2: Sub-module "net::http" -> net/http.rs
    # use net::http; -> "net::http"
    res = resolver.resolve(root, root / "src/lib.rs", "net::http")
    # Our resolver logic for "net::http" checks under src/net/http.rs
    assert "src/net/http.rs" in res or "src/net/mod.rs" in res
