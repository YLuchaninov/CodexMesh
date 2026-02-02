"""
Detailed Tools API Router.
Exposes runtime tools with full schemas (simulating MCP list_tools_detailed).
"""

from fastapi import APIRouter, Depends, Request

from ....services.analysis_service import AnalysisService
from ....workflows.runtime import RuntimeFactory
from ...dependencies import get_analysis_service

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("/detailed")
async def list_tools_detailed(
    request: Request,
    an: AnalysisService = Depends(get_analysis_service),
):
    """List runtime tools with full schemas."""
    # We need to construct the runtime environment to get actual tools
    # We can reuse RuntimeFactory._build_tools logic

    # Intent registry might be needed if some tools depend on it (though usually reverse)
    # But RuntimeFactory._build_tools takes it.
    reg = getattr(request.app.state, "intent_registry", None)
    if not reg:
        # Fallback if not loaded
        # intents_dir = (
        #     request.app.state.config.workflows_path
        #     if hasattr(request.app.state, "config")
        #     else None
        # )
        # or defaults...
        # For now, pass None or try to load if strictly required.
        # RuntimeFactory usually handles None registry gracefully if tools don't need it.
        pass

    # Actually we just want the tools list matching what Executor uses.
    tools_map = RuntimeFactory._build_tools(an, reg)

    results = []
    for name, tool_func in tools_map.items():
        # Inspect the function to get docstring and args
        # This is a simplified "schema extraction" for the agent
        # Ideally we'd use pydantic schemas if available, or docstring parsing.

        doc = (tool_func.__doc__ or "").strip()

        # We can try to get signature
        import inspect

        try:
            sig = inspect.signature(tool_func)
            params = []
            for param_name, param in sig.parameters.items():
                p_info = {
                    "name": param_name,
                    "kind": str(param.kind),
                    "default": str(param.default)
                    if param.default is not inspect.Parameter.empty
                    else None,
                    "annotation": str(param.annotation)
                    if param.annotation is not inspect.Parameter.empty
                    else None,
                }
                params.append(p_info)
        except Exception:
            params = []

        results.append({"name": name, "description": doc, "parameters": params})

    return {"tools": results}


@router.get("/search")
async def search_tools(
    q: str,
    request: Request,
    an: AnalysisService = Depends(get_analysis_service),
):
    """Search tools by name or description."""
    # Re-use logic from detailed
    detailed = await list_tools_detailed(request, an)
    all_tools = detailed["tools"]

    q_lower = q.lower()
    matches = []
    for t in all_tools:
        if q_lower in t["name"].lower() or q_lower in t["description"].lower():
            matches.append(t)

    return {"tools": matches}
