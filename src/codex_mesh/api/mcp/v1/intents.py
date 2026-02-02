"""
Intents MCP Tools.
"""

from pathlib import Path

from mcp.server.fastmcp import FastMCP

from ....services.analysis_service import AnalysisService
from ....services.logging import safe_tool
from ....services.project_service import ProjectService


def register_intent_tools(
    server: FastMCP, analysis_service: AnalysisService, project_service: ProjectService
):
    from ....workflows.engine.registry import IntentRegistry
    from ....workflows.runtime import RuntimeFactory

    # Load Intents
    base = Path(__file__).resolve().parents[3]
    registry = IntentRegistry(str(base / "workflows" / "definitions"))
    registry.load()

    def ensure_ready():
        project_service.ensure_ready()

    @server.tool()
    @safe_tool
    async def list_tools_detailed() -> dict:
        """List detailed tool schemas."""
        tools = RuntimeFactory._build_tools(analysis_service, registry)
        return {
            "tools": [
                {"name": name, "description": "Workflow tool"} for name in sorted(tools.keys())
            ]
        }

    @server.tool()
    @safe_tool
    async def search_tools(query: str) -> list[dict]:
        """Search available tools by name/description."""
        q = query.lower()
        all_tools = await list_tools_detailed()
        results = []
        for t in all_tools["tools"]:
            if q in t["name"].lower() or q in t["description"].lower():
                results.append(t)
        return results

    @server.tool()
    @safe_tool
    async def list_intents() -> dict:
        """List available intents."""
        items = []
        for it in registry.list():
            items.append(
                {
                    "id": it.id,
                    "title": it.title,
                    "description": it.description,
                    "slots": it.slots,
                    "examples": it.examples,
                    "tags": getattr(it, "tags", []) or [],
                }
            )
        return {"intents": items}

    @server.tool()
    @safe_tool
    async def execute_intent(
        intent_id: str, args: dict | None = None, include_trace: bool = True, max_steps: int = 200
    ) -> dict:
        """Execute a named intent."""
        ensure_ready()
        it = registry.get(intent_id)
        if not it:
            return {"error": f"Unknown intent: {intent_id}"}

        import time

        from ....services.tracing_service import TracingService
        from ....workflows.engine.input_prep import prepare_intent_input
        from ....workflows.engine.runner import JsonWorkflowRunner, ToolExecutor

        tracing = TracingService()
        tid = tracing.start_trace()
        tools = RuntimeFactory._build_tools(analysis_service, registry)

        wrapped = {}
        for name, fn in tools.items():

            def make(name=name, fn=fn):
                def call(params: dict):
                    t0 = time.time()
                    error = None
                    out = None
                    try:
                        out = fn(params)
                    except Exception as e:
                        error = e
                        raise e
                    finally:
                        dt = time.time() - t0
                        if include_trace:
                            preview = out if isinstance(out, str) else str(out)[:1000]
                            if error:
                                preview = f"Error: {str(error)}"
                            tracing.log_step(
                                step_type="tool",
                                name=name,
                                input_data=params,
                                output_data=preview,
                                duration=dt,
                            )
                    return out

                return call

            wrapped[name] = make()

        runner = JsonWorkflowRunner(ToolExecutor(wrapped), max_steps=max_steps)
        args = args or {}
        query = args.get("query", "")
        prepared = prepare_intent_input(it, query=query, slots=args)
        res = runner.run(
            it.workflow, context={"input": prepared, "query": query, "intent": intent_id}
        )

        tracing.stop_trace(tid)
        response = {
            "output": str(res.changes.get("result", "")),
            "logs": res.logs,
            "artifacts": res.changes.get("artifacts", {}) or {},
        }
        if include_trace:
            session = tracing._traces[tid]
            trace_list = []
            for s in session.steps:
                trace_list.append(
                    {
                        "step_id": s.id,
                        "tool": s.name,
                        "input": s.input,
                        "output_preview": str(s.output)[:800],
                        "duration_ms": int(s.duration * 1000),
                    }
                )
            response["trace"] = trace_list
            response["trace_subgraph"] = tracing.get_trace_subgraph(tid)

        if not res.success:
            response["error"] = "Workflow failed"
        return response
