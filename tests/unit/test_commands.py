from codex_mesh.llm.command_handler import CommandRegistry


def test_registry_basics():
    registry = CommandRegistry()
    assert registry.is_command("/help") is True
    assert registry.is_command("hello") is False
    assert registry.get_command("/help") is not None
    assert registry.get_command("/invalid") is None


def test_help_command():
    registry = CommandRegistry()
    result = registry.execute("/help")
    assert result is not None
    assert "CodexMesh Help" in result.content
    assert "/help" in result.content
    assert "/about" in result.content


def test_about_command():
    registry = CommandRegistry()
    result = registry.execute("/about")
    assert result is not None
    assert "About CodexMesh" in result.content
    assert "semantic" in result.content.lower()


def test_mcp_command():
    registry = CommandRegistry()
    result = registry.execute("/mcp")
    assert result is not None
    assert "Connecting via MCP" in result.content
    assert "Claude Desktop" in result.content


def test_execution_miss():
    registry = CommandRegistry()
    result = registry.execute("/doesntexist")
    assert result is None


def test_execution_no_command():
    registry = CommandRegistry()
    result = registry.execute(" hello ")
    assert result is None
