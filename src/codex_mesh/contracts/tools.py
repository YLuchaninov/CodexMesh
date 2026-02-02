"""
Tool registry contracts.

Models for tool registry used by UI command palette.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field

HttpMethod = Literal["GET", "POST"]


class ToolFormField(BaseModel):
    """A form field for tool UI."""

    name: str
    type: str = Field(..., description="string|number|boolean|select")
    default: Any = None
    options: list[Any] | None = None
    placeholder: str | None = None


class ToolUIHints(BaseModel):
    """UI hints for tool rendering."""

    form: list[ToolFormField] = Field(default_factory=list)


class ToolMeta(BaseModel):
    """Tool metadata for registry."""

    id: str
    title: str
    category: str
    method: HttpMethod
    endpoint: str
    ui: ToolUIHints = Field(default_factory=ToolUIHints)


class ToolsRegistryResponse(BaseModel):
    """Response with available tools."""

    tools: list[ToolMeta] = Field(default_factory=list)
