"""
Intent contracts.

Models for workflow intents: list, execute, trace.
"""

from typing import Any

from pydantic import BaseModel, Field


class IntentItem(BaseModel):
    """An intent definition."""

    id: str
    title: str
    description: str = ""
    slots: dict[str, Any] = Field(default_factory=dict)
    input_schema: dict[str, Any] | None = None
    examples: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class IntentsListResponse(BaseModel):
    """Response with list of available intents."""

    intents: list[IntentItem] = Field(default_factory=list)


class ToolTraceStep(BaseModel):
    """A single step in tool execution trace."""

    tool: str
    input: dict[str, Any] = Field(default_factory=dict)
    output_preview: str = ""
    duration_ms: int | None = None


class IntentExecuteOptions(BaseModel):
    """Options for intent execution."""

    include_trace: bool = Field(True, description="Include tool execution trace")
    max_steps: int = Field(200, ge=1, le=2000)


class IntentExecuteRequest(BaseModel):
    """Intent execution request."""

    intent_id: str
    input: dict[str, Any] = Field(default_factory=dict)
    options: IntentExecuteOptions = Field(default_factory=lambda: IntentExecuteOptions())


class IntentExecuteResponse(BaseModel):
    """Intent execution response."""

    output: str = ""
    trace: list[ToolTraceStep] = Field(default_factory=list)
    logs: list[str] = Field(default_factory=list)
    artifacts: dict[str, Any] = Field(default_factory=dict)
    stats: dict[str, Any] = Field(default_factory=dict)
