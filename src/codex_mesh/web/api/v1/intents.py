"""
Intents API Router.
"""

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Request

from ....contracts.errors import ApiError
from ....contracts.intents import (
    IntentExecuteRequest,
    IntentExecuteResponse,
    IntentItem,
    IntentsListResponse,
    ToolTraceStep,
)
from ....services.analysis_service import AnalysisService
from ....services.project_service import ProjectService
from ...dependencies import get_analysis_service, get_project_service

router = APIRouter(prefix="/intents", tags=["intents"])


def ensure_ready(ps: ProjectService) -> None:
    ps.ensure_ready()


def _preview(obj: Any, limit: int = 800) -> str:
    try:
        s = obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False, default=str)
    except Exception:
        s = str(obj)
    return s if len(s) <= limit else s[:limit] + "…"


def _get_intent_registry(request: Request):
    reg = getattr(request.app.state, "intent_registry", None)
    if reg is None:
        from ....workflows.engine.registry import IntentRegistry

        intents_dir = str(Path(__file__).resolve().parents[3] / "workflows" / "definitions")

        reg = IntentRegistry(intents_dir)
        reg.load()
        request.app.state.intent_registry = reg
    return reg


@router.get("", response_model=IntentsListResponse)
async def intents_list(request: Request):
    """List available intents."""
    reg = _get_intent_registry(request)
    items = []
    for it in reg.list():
        items.append(
            {
                "id": it.id,
                "title": it.title,
                "description": it.description,
                "slots": it.slots,
                "input_schema": getattr(it, "input_schema", None),
                "examples": it.examples,
                "tags": getattr(it, "tags", []) or [],
            }
        )
    return IntentsListResponse(intents=[IntentItem(**i) for i in items])


@router.post("/execute", response_model=IntentExecuteResponse)
async def intents_execute(
    request: Request,
    req: IntentExecuteRequest,
    ps: ProjectService = Depends(get_project_service),
    an: AnalysisService = Depends(get_analysis_service),
):
    """Execute an intent."""
    ensure_ready(ps)

    reg = _get_intent_registry(request)
    it = reg.get(req.intent_id)
    if not it:
        raise ApiError(404, "NotFound", f"Unknown intent: {req.intent_id}")

    from ....services.tracing_service import TracingService
    from ....workflows.engine.input_prep import prepare_intent_input
    from ....workflows.engine.runner import JsonWorkflowRunner, ToolExecutor
    from ....workflows.runtime import RuntimeFactory

    tools = RuntimeFactory._build_tools(an, reg)

    tracing_svc = TracingService()
    trace_id = tracing_svc.start_trace()

    runner = JsonWorkflowRunner(
        ToolExecutor(tools), max_steps=req.options.max_steps, tracing=tracing_svc
    )

    query = (req.input or {}).get("query", "")
    prepared = prepare_intent_input(it, query=query, slots=req.input or {})
    res = runner.run(
        it.workflow, context={"input": prepared, "query": query, "intent": req.intent_id}
    )

    if not res.success:
        tracing_svc.stop_trace(trace_id)
        raise ApiError(400, "BadRequest", "Workflow failed", details={"logs": res.logs})

    tracing_svc.stop_trace(trace_id)
    output = res.changes.get("result", "")

    final_trace: list[ToolTraceStep] = []
    if req.options.include_trace:
        graph = tracing_svc.get_trace_subgraph(trace_id)
        for node in graph["nodes"]:
            if node["type"] == "tool":
                final_trace.append(
                    ToolTraceStep(
                        tool=node["name"],
                        input=node["data"].get("input", {}),
                        output_preview=_preview(node["data"].get("output", "")),
                        duration_ms=int(node["data"].get("duration", 0) * 1000),
                    )
                )

    return IntentExecuteResponse(
        output=output,
        trace=final_trace,
        logs=res.logs,
        artifacts=res.changes.get("artifacts", {}) or {},
        stats={"steps": len(final_trace)},
    )
