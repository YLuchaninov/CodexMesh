"""
Workflow Runtime Factory.

Centralizes the creation of WorkflowRunner and ToolExecutor to ensure consistency
between MCP tools and ReviewerAgent.
"""

from typing import Any

from ..services.analysis_service import AnalysisService
from ..services.fs_service import FileSystemService
from ..services.tracing_service import TracingService
from ..services.workflow_tool_service import WorkflowToolService
from .engine.registry import IntentRegistry
from .engine.runner import JsonWorkflowRunner, ToolExecutor


class RuntimeFactory:
    """Factory for creating configured WorkflowRunners."""

    @staticmethod
    def create(analysis_service: AnalysisService, registry: IntentRegistry) -> JsonWorkflowRunner:
        """Create a fully configured runner with all standard tools."""

        executor = ToolExecutor(tools=RuntimeFactory._build_tools(analysis_service, registry))
        return JsonWorkflowRunner(executor)

    @staticmethod
    def _build_tools(
        analysis: AnalysisService,
        registry: IntentRegistry | None,
        fs: FileSystemService | None = None,
    ) -> dict[str, Any]:
        """
        Builds a dictionary of callable tools for the agent/workflow.
        """

        tracing = TracingService()
        tool_service = WorkflowToolService(analysis, tracing)

        def _wrap_sync(f):
            return lambda p: f(**p)

        # --- 1. Core Analysis Wrappers ---
        tools: dict[str, Any] = {
            # --- Analysis / Search ---
            "search_code_raw": _wrap_sync(analysis.search_code_raw),
            "search_text_raw": _wrap_sync(analysis.search_text_raw),
            "semantic_search_raw": _wrap_sync(analysis.semantic_search_raw),
            "resolve_symbol": _wrap_sync(analysis.resolve_symbol),
            "get_subgraph": _wrap_sync(analysis.get_subgraph),
            "build_call_graph": _wrap_sync(analysis.build_call_graph),
            "callers_of": _wrap_sync(analysis.callers_of),
            "callees_of": _wrap_sync(analysis.callees_of),
            "find_entrypoint_paths": _wrap_sync(analysis.find_entrypoint_paths),
            "detect_entrypoints": _wrap_sync(analysis.detect_entrypoints),
            "entrypoints_list": _wrap_sync(analysis.entrypoints_list),
            "compute_reachable_set": _wrap_sync(analysis.compute_reachable_set),
            "find_path": _wrap_sync(analysis.find_path),
            "get_hotspot": _wrap_sync(analysis.get_hotspot),
            "get_hotspot_raw": _wrap_sync(analysis.get_hotspot_raw),
            "get_repo_map_raw": _wrap_sync(analysis.get_repo_map_raw),
            "get_symbol_info": _wrap_sync(analysis.get_symbol_info),
            "get_dependency_tree": _wrap_sync(analysis.get_dependency_tree),
            "list_tools": lambda p: {"markdown": "- " + "\n- ".join(sorted(tools.keys()))},
            "list_intents": lambda p: {
                "markdown": "\n".join([f"- {it.id}" for it in registry.list()])
                if registry
                else "No intents available."
            },
        }

        # --- 2. Workflow Helpers (via WorkflowToolService) ---
        tools.update(
            {
                "resolve_seeds": _wrap_sync(tool_service.resolve_seeds),
                "rank_subgraph_nodes": _wrap_sync(tool_service.rank_subgraph_nodes),
                "pick_best_entrypoint": _wrap_sync(tool_service.pick_best_entrypoint),
                "hotspot_in_scope": _wrap_sync(tool_service.hotspot_in_scope),
                "join_hotspot_scores": _wrap_sync(tool_service.join_hotspot_scores),
                "detect_cycles": _wrap_sync(tool_service.detect_cycles),
                "summarize_hotspots": _wrap_sync(tool_service.summarize_hotspots),
                "path_to_subgraph": _wrap_sync(tool_service.path_to_subgraph),
                "render_graph": _wrap_sync(tool_service.render_graph),
                "dead_code_candidates": _wrap_sync(tool_service.dead_code_candidates),
                "build_module_graph": _wrap_sync(tool_service.build_module_graph),
                "check_layering_rules": _wrap_sync(tool_service.check_layering_rules),
                "rank_impact": _wrap_sync(tool_service.rank_impact),
                "summarize_security_hits": _wrap_sync(tool_service.summarize_security_hits),
                # Tracing
                "trace_start": _wrap_sync(tool_service.trace_start),
                "trace_wait": _wrap_sync(tool_service.trace_wait),
                "trace_stop": _wrap_sync(tool_service.trace_stop),
                "trace_to_subgraph": _wrap_sync(tool_service.trace_to_subgraph),
            }
        )

        return tools
