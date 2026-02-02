"""
Workflow Runner.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from ...services.tracing_service import TracingService
from .templating import render_compose_template, render_template


# Use simple compat result
@dataclass
class WorkflowResult:
    success: bool
    logs: list[str]
    changes: dict[str, Any]


class WorkflowRunner(Protocol):
    def run(self, workflow_json: dict, context: dict) -> WorkflowResult: ...


ToolFn = Callable[[dict[str, Any]], Any]


@dataclass
class ToolExecutor:
    """
    Maps tool_name -> callable(params)->result
    Keep it pure + JSON-serializable outputs.
    """

    tools: dict[str, ToolFn]

    def call(self, tool_name: str, params: dict[str, Any]) -> Any:
        if tool_name not in self.tools:
            raise KeyError(f"Unknown tool: {tool_name}")
        return self.tools[tool_name](params)


class JsonWorkflowRunner:
    def __init__(
        self, executor: ToolExecutor, max_steps: int = 200, tracing: TracingService | None = None
    ):
        self._executor = executor
        self._max_steps = max_steps
        self._tracing = tracing

    def run(self, workflow_json: dict, context: dict) -> WorkflowResult:
        logs: list[str] = []
        ctx: dict[str, Any] = dict(context or {})
        steps = workflow_json.get("steps", [])
        try:
            result = self._run_steps(steps, ctx, logs, depth=0, step_budget=self._max_steps)
            changes = {"context": ctx, "result": result}
            return WorkflowResult(success=True, logs=logs, changes=changes)
        except Exception as e:
            import traceback

            logs.append(f"[error] {type(e).__name__}: {e}")
            logs.append(traceback.format_exc())
            return WorkflowResult(success=False, logs=logs, changes={"context": ctx})

    def _run_steps(
        self,
        steps: list[dict[str, Any]],
        ctx: dict[str, Any],
        logs: list[str],
        depth: int,
        step_budget: int,
    ) -> Any:
        if depth > 50:
            raise RuntimeError("Max workflow recursion depth exceeded")
        remaining = step_budget
        last_value: Any = None

        for step in steps:
            remaining -= 1
            if remaining < 0:
                raise RuntimeError("Max workflow steps exceeded")

            action = step.get("action", "tool")
            try:
                if action == "tool":
                    tool_name = step["tool_name"]
                    params = render_template(step.get("params", {}), ctx)
                    logs.append(f"[tool] {tool_name}")
                    out = self._executor.call(tool_name, params)

                    save_as = step.get("save_as")
                    if save_as:
                        ctx[save_as] = out
                    last_value = out

                    if self._tracing:
                        # Assuming we have an active trace session if tracing service is provided
                        # The start/stop should be managed by the caller of run() or inside run()
                        self._tracing.log_step(
                            "tool", tool_name, input_data=params, output_data=out, duration=0.0
                        )

                elif action == "branch":
                    cond_raw = step.get("condition", "")
                    cond = render_template(cond_raw, ctx)
                    # Simple truthiness check
                    ok = bool(cond)
                    if isinstance(cond, str):
                        ok = cond.lower() in ("true", "yes", "1")

                    logs.append(f"[branch] condition={cond_raw} -> {ok}")
                    step.get("steps", []) if ok else step.get("else", [])
                    # Note: "then" was used in example, "steps" in my recursive call?
                    # The example used nested "steps" for branch if true.
                    # Let's support "steps" (if true) and "else" (if false)
                    if ok:
                        last_value = self._run_steps(
                            step.get("steps", []), ctx, logs, depth + 1, remaining
                        )
                    elif "else" in step:
                        last_value = self._run_steps(
                            step.get("else", []), ctx, logs, depth + 1, remaining
                        )

                elif action == "compose":
                    template = step.get("template", "")
                    if isinstance(template, list):
                        # Use Jinja2-aware rendering for list templates
                        rendered = render_compose_template(template, ctx)
                    else:
                        rendered = render_template(template, ctx)

                    save_as = step.get("save_as")
                    if save_as:
                        ctx[save_as] = rendered
                    logs.append(f"[compose] -> {save_as or '(no save_as)'}")
                    last_value = rendered

                elif action == "set":
                    key = step["key"]
                    value = render_template(step.get("value"), ctx)
                    ctx[key] = value
                    logs.append(f"[set] {key}")
                    last_value = value

                elif action == "return":
                    value = render_template(step.get("value"), ctx)
                    logs.append("[return]")
                    return value

                elif action == "vis":  # visualization
                    # Alias to tool, but maybe special logging
                    tool_name = step.get("tool_name", "render_graph")
                    params = render_template(step.get("params", {}), ctx)
                    out = self._executor.call(tool_name, params)
                    save_as = step.get("save_as")
                    if save_as:
                        ctx[save_as] = out
                    logs.append(f"[vis] {tool_name}")
                    last_value = out

                else:
                    logs.append(f"[warn] Unsupported action: {action}")
            except Exception as e:
                logs.append(f"[error] Step failed: {action} - {e}")
                raise e

        return last_value
