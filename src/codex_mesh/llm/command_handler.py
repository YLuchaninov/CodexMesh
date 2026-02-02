"""
Chat Command Handler for CodexMesh.
"""

from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class CommandResult:
    content: str
    metadata: dict | None = None


class CommandRegistry:
    """Registry for chat slash commands."""

    def __init__(self):
        self._commands: dict[str, Callable[[], CommandResult]] = {}
        self._descriptions: dict[str, str] = {}
        self._setup_defaults()

    def register(self, name: str, handler: Callable[[], CommandResult], description: str):
        """Register a new command."""
        self._commands[name] = handler
        self._descriptions[name] = description

    def get_command(self, name: str) -> Callable[[], CommandResult] | None:
        """Get command handler by name."""
        return self._commands.get(name)

    def is_command(self, text: str) -> bool:
        """Check if text is a command."""
        return text.strip().startswith("/")

    def execute(self, text: str) -> CommandResult | None:
        """Execute a command if it exists."""
        parts = text.strip().split()
        if not parts:
            return None

        cmd_name = parts[0]
        handler = self.get_command(cmd_name)
        if handler:
            return handler()
        return None

    def _setup_defaults(self):
        """Register default commands."""
        self.register(
            "/help", self._handle_help, "Show available commands and web interface capabilities"
        )
        self.register("/about", self._handle_about, "Describe the CodexMesh system and its purpose")
        self.register("/mcp", self._handle_mcp, "Show instructions for connecting to MCP clients")

    def _handle_help(self) -> CommandResult:
        commands_help = "\n".join(
            [f"- `{cmd}`: {desc}" for cmd, desc in self._descriptions.items()]
        )

        content = f"""# CodexMesh Help

## Available Commands
{commands_help}

## What I Can Do (Intents)
I can run complex multi-step workflows for you. Just ask:
- **"Overview"**: `intent.codebase_overview` - High-level map and risk analysis.
- **"Trace path from A to B"**: `intent.find_path` - Find execution paths.
- **"Refactor X"**: `intent.refactor_guidance` - Impact analysis and plan.
- **"Hotspots"**: `intent.hotspots_report` - Find tech debt and complexity.

## Web Interface
The Web UI is your Control Plane:
- **Graph Explorer**: Visual interaction with the dependency graph.
- **Project Switcher**: Manage multiple repositories.
- **Live Status**: Monitor indexing progress.
"""
        return CommandResult(content=content)

    def _handle_about(self) -> CommandResult:
        content = """# About CodexMesh

**CodexMesh** is a semantic intelligence layer for your codebase.

It doesn't just "read" files; it builds a **Knowledge Graph** of your software, understanding:
- **Structure**: Classes, functions, and their hierarchical relationships.
- **Flow**: Who calls whom (`CALLS` edges) and data dependencies.
- **Usage**: What is dead code, and what is critical infrastructure.

It bridges the gap between static text and semantic understanding, empowering Agents to reason about code architecture.
"""
        return CommandResult(content=content)

    def _handle_mcp(self) -> CommandResult:
        content = """# Connecting via MCP

CodexMesh exposes a **Model Context Protocol (MCP)** server, allowing AI assistants to directly query your codebase.

## Quick Setup

### Claude Desktop
Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "codex-mesh": {
      "command": "uv",
      "args": ["run", "codex-mesh", "--directory", "/absolute/path/to/your/repo"]
    }
  }
}
```

### Cursor / VS Code
1. Open **Settings** -> **Features** -> **MCP**.
2. Add a new server:
   - **Type**: `stdio`
   - **Command**: `uv run codex-mesh` (ensure `uv` is in PATH, or use absolute path)
   - **Args**: `--directory /absolute/path/to/your/repo`

> **Note**: Verify paths are absolute. Check logs if connection fails.
"""
        return CommandResult(content=content)
