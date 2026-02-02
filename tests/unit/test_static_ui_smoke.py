from pathlib import Path


def test_static_ui_uses_v1_endpoints():
    root = Path(__file__).resolve().parents[2]
    html = (root / "src" / "codex_mesh" / "web" / "static" / "index.html").read_text(
        encoding="utf-8"
    )

    assert "/v1/events" in html
    assert "/v1/project/connect" in html
    assert "/v1/fs/list" in html
