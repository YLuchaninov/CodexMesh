import sys

from codex_mesh.core.shell import safe_shell


def test_safe_shell_binary_mode_returns_text_stdout():
    # text=False makes subprocess return bytes; safe_shell must still return str
    res = safe_shell(
        [sys.executable, "-c", "import sys; sys.stdout.buffer.write(b'abc')"],
        text=False,
    )
    assert isinstance(res.stdout, str)
    assert res.stdout == "abc"
