"""
Autopilot Agent.
Orchestrates translation, planning, and execution of intents/tools.
"""

import json
import logging
import os
import re
from typing import Any

from ..services.analysis_service import AnalysisService
from ..services.fs_service import FileSystemService
from ..services.tracing_service import TracingService
from ..workflows.engine.input_prep import prepare_intent_input
from ..workflows.engine.registry import IntentRegistry
from ..workflows.engine.runner import JsonWorkflowRunner, ToolExecutor
from ..workflows.runtime import RuntimeFactory
from .translate import translate_to_en_preserve_tokens

logger = logging.getLogger(__name__)

PLAN_PROMPT = """
You are a technical planner for a code analysis assistant.
You have access to a set of Tools and Workflows (Intents).

User Query (Original): "{user_query_orig}"
User Query (English): "{user_query_en}"

Available Capabilities:
{capabilities_json}

Goal:
1. Analyze the user query.
2. Select the most relevant Intents or Tools to gather information or perform actions.
3. If the query asks for a diagram/graph, PREFER intents like 'intent.execution_graph_static' or 'intent.feature_slice'.
4. If the query asks for risks/hotspots, properties, use 'analysis.hotspots' or 'intent.hotspots_report'.
5. Use 'analysis.search' if you need to find file paths first.

ActiYou have access to:
1. Intents (high-level workflows).
2. Runtime Tools (low-level functions like search).

Use `search_text_raw` / `search_code_raw` / `semantic_search_raw` to find files/symbols.
Use ONLY tool/intent IDs present in capabilities_json. Never invent IDs.
If user asks to show exact code / конкретный кусок / where rendering happens: MUST call `semantic_search_raw` then `read_span`.

Return JSON with a list of steps.
Example:
{{
  "language": "ru",
  "plan": [
    {{"kind":"tool","id":"semantic_search_raw","args":{{"query":"AuthService","k":5}}}},
    {{"kind":"tool","id":"read_span","args":{{"path":"src/auth.py","start_line":10,"end_line":50}}}}
  ]
}}

Output ONLY valid JSON.
"""

SYNTHESIS_PROMPT = """
You are a helpful coding assistant.
User Query: "{user_query}"
Language: {language}

Evidence collected from tools:
{evidence_json}

Task:
Answer the user's query based on the evidence.
- If the evidence contains diagrams (mermaid), include them in the response.
- If the evidence shows errors, explain them.
- Be concise and technical.
- Answer in {language}.
"""


_WANTS_CODE_RE = re.compile(
    r"\b(show|snippet|code|render|rendering|responsible|where|"
    r"покажи|показать|кусок|фрагмент|код|где|отвечает|рендер)\b",
    re.IGNORECASE,
)


def _wants_code_snippet(q: str) -> bool:
    return bool(_WANTS_CODE_RE.search(q or ""))


class AutopilotAgent:
    def __init__(
        self,
        analysis_service: AnalysisService,
        intent_registry: IntentRegistry,
        settings=None,
        fs: FileSystemService | None = None,
    ):
        self.an = analysis_service
        self.reg = intent_registry
        self.settings = settings or {}
        self.fs = fs
        self.tracer = TracingService()

        self.profile = self._resolve_profile()

        from .routing import LLMFactory

        self.llm = LLMFactory.create(self.profile) if self.profile else None

    def _resolve_profile(self):
        """
        Resolve LLM profile with same logic as ReviewerAgent.
        1. 'ui_active' profile from Server Context (if available)
        2. Config defaults
        3. Settings passed from UI
        4. Environment variables
        """
        from .routing import LLMProfile, get_profile

        # 1. Try Server Context (ui_active)
        try:
            if hasattr(self.an.manager, "server") and self.an.manager.server:
                cfg = self.an.manager.server.context.config
                if "ui_active" in cfg.profiles:
                    return cfg.profiles["ui_active"]
        except Exception:
            pass

        # 2. Try Base Profile (gemini_pro)
        base_profile = get_profile("gemini_pro") or get_profile("google")

        # 3. Use Settings (UI Overrides) or Env Fallback
        # Same logic as we tried to fix before, but now more comprehensive
        api_key = None
        if self.settings and self.settings.api_key:
            api_key = self.settings.api_key
        else:
            # Fallback to env or base profile
            api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
            if not api_key and base_profile:
                api_key = base_profile.api_key

        if api_key:
            return LLMProfile(
                name="autopilot_session",
                model=self.settings.model
                if self.settings
                else (base_profile.model if base_profile else "gemini-1.5-pro-latest"),
                provider="google",
                api_key=api_key,
                api_key_env="GOOGLE_API_KEY",
            )

        # 4. Fallback to base_profile if we couldn't resolve a key but usage might rely on internal auth (e.g. Vertex AI default)
        # However, for API-Key based usage, we need a key.
        return base_profile

    async def ask(
        self, query: str, history: list | None = None, pinned_context: Any = None
    ) -> dict[str, Any]:
        """
        Main entry point.
        """
        # 0. Setup
        history = history or []
        evidence = []
        trace_steps = []

        # 1. Translate / Normalize
        # Use LLMProfile for translation (fixing type mismatch)
        query_en = translate_to_en_preserve_tokens(query, self.profile)

        # 2. List Capabilities for Planner
        caps = self._get_capabilities_summary()

        # 2. Add Code Snippet Guard: if user wants code, pre-fetch it
        if self.fs and _wants_code_snippet(query_en):
            # Try to catch code early
            hits = self.an.semantic_search(query_en, k=5)
            if hits:
                best = hits[0]
                path = best.get("file_path")
                start = best.get("line_start")
                end = best.get("line_end") or start
                if path and start:
                    # Read span safely
                    try:
                        s_val = int(start)
                        e_val = int(end) if end else s_val
                        span = self.fs.read_file_span(
                            path,
                            s_val,
                            e_val,
                            context_lines=12,
                        )
                        # Format for trace
                        base = int(span.get("base_line", 1))
                        lines = span.get("content", "").splitlines()
                        numbered = "\n".join(f"{base + i:4d} | {ln}" for i, ln in enumerate(lines))
                        snippet_md = f"{path}#L{start}-L{end}\n```text\n{numbered}\n```"
                        trace_steps.append(
                            {
                                "id": "guard_read_span",
                                "status": "done",
                                "output": snippet_md,
                                "artifacts": [],
                            }
                        )
                    except Exception:
                        pass

        # 3. Plan
        plan_data = await self._generate_plan(query, query_en, caps)
        language = plan_data.get("language", "en")
        actions = plan_data.get("plan", [])

        # 4. Execute Plan
        # results_map = {}

        for i, action in enumerate(actions):
            kind = action.get("kind")
            aid = action.get("id")
            args = action.get("args", {})

            step_record = {"step": i + 1, "kind": kind, "id": aid, "status": "pending"}

            try:
                if kind == "intent":
                    res = self._execute_intent_action(aid, args)
                    step_record["output"] = res["output"]
                    step_record["status"] = "success"
                    evidence.append(f"Action {i} ({aid}):\n{res['output'][:2000]}")
                    if res.get("artifacts"):
                        step_record["artifacts"] = res["artifacts"]

                elif kind == "tool":
                    res = self._execute_tool_action(aid, args)
                    step_record["output"] = str(res)
                    step_record["status"] = "success"
                    evidence.append(f"Action {i} ({aid}):\n{str(res)[:2000]}")

            except Exception as e:
                logger.error(f"Action failed: {action} - {e}")
                step_record["status"] = "error"
                step_record["error"] = str(e)
                evidence.append(f"Action {i} ({aid}) FAILED: {e}")

            trace_steps.append(step_record)

        # 5. Synthesize Answer
        answer = await self._synthesize_answer(query, language, trace_steps)

        return {"answer": answer, "evidence": trace_steps, "raw_plan": plan_data}

    def _get_capabilities_summary(self) -> str:
        """
        Prepare a compressed JSON summary of available tools/intents.
        """
        # Intents
        intents_list = []
        for it in self.reg.list():
            # Include input schema properties to help LLM
            # Maximal enrichment: include types and descriptions if available
            props = getattr(it, "input_schema", {}).get("properties", {})
            args_desc = {}
            for k, v in props.items():
                args_desc[k] = {
                    "type": v.get("type", "string"),
                    "description": v.get("description", ""),
                }

            intents_list.append(
                {"kind": "intent", "id": it.id, "description": it.description, "args": args_desc}
            )

        # Tools (Runtime)
        tools = RuntimeFactory._build_tools(self.an, self.reg, fs=self.fs)
        tools_list = []
        for name, fn in tools.items():
            # Basic introspection
            import inspect

            try:
                sig = inspect.signature(fn)
                params = {
                    k: {
                        "type": str(v.annotation),
                        "default": str(v.default) if v.default != inspect._empty else "required",
                    }
                    for k, v in sig.parameters.items()
                }
            except Exception:
                params = {}

            tools_list.append(
                {
                    "kind": "tool",
                    "id": name,
                    "description": (fn.__doc__ or "").split("\n")[0],
                    "args": params,
                }
            )

        return json.dumps({"intents": intents_list, "tools": tools_list}, indent=2)

    async def _generate_plan(self, q_orig: str, q_en: str, caps: str) -> dict:
        if not self.llm:
            return {"language": "en", "plan": []}

        prompt = PLAN_PROMPT.format(
            user_query_orig=q_orig, user_query_en=q_en, capabilities_json=caps, language="auto"
        )

        try:
            from langchain_core.messages import HumanMessage

            resp = await self.llm.ainvoke([HumanMessage(content=prompt)])
            txt = str(resp.content).strip()

            if "```json" in txt:
                txt = txt.split("```json")[1].split("```")[0].strip()
            elif "```" in txt:
                txt = txt.split("```")[1].split("```")[0].strip()

            return json.loads(txt)
        except Exception as e:
            logger.error(f"Plan generation failed: {e}")
            return {"language": "en", "plan": []}

    async def _synthesize_answer(self, query: str, language: str, trace_steps: list[dict]) -> str:
        """
        Summarize the findings into a final answer using structured trace steps.
        """
        # Convert structured trace to JSON string for the LLM
        evidence_json = json.dumps(trace_steps, indent=2, ensure_ascii=False)

        prompt = SYNTHESIS_PROMPT.format(
            user_query=query, language=language, evidence_json=evidence_json
        )

        try:
            from langchain_core.messages import HumanMessage

            if not self.llm:
                return "Error: No LLM configured."

            resp = await self.llm.ainvoke([HumanMessage(content=prompt)])
            return str(resp.content).strip()
        except Exception as e:
            return f"Error generating answer: {e}"

    def _execute_intent_action(self, intent_id: str, args: dict) -> dict:
        it = self.reg.get(intent_id)
        if not it:
            raise ValueError(f"Unknown intent: {intent_id}")

        # Build Tools
        tools = RuntimeFactory._build_tools(self.an, self.reg, fs=self.fs)

        # Prepare Input
        # We can treat args as 'slots' or 'query' depending on what LLM output
        # LLM output 'args' which should match properties
        # We pass it as 'slots' to refine
        # But we also need a 'query' for heuristics?
        # Actually planner gives us structured args, so we pass it as slots.
        # pass empty string as query if args are fully structured
        prepared = prepare_intent_input(it, query="", slots=args)

        # Run
        trace_id = self.tracer.start_trace()
        runner = JsonWorkflowRunner(ToolExecutor(tools), max_steps=50, tracing=self.tracer)

        try:
            res = runner.run(
                it.workflow, context={"input": prepared, "query": "", "intent": intent_id}
            )

            self.tracer.stop_trace(trace_id)

            return {
                "success": res.success,
                "output": res.changes.get("result", "") or "\n".join(res.logs),
                "artifacts": res.changes.get("artifacts", {}),
            }
        except Exception as e:
            self.tracer.stop_trace(trace_id)
            raise e

    def _execute_tool_action(self, tool_id: str, args: dict) -> Any:
        # RuntimeFactory._build_tools returns map {name: func}
        tools = RuntimeFactory._build_tools(self.an, self.reg, fs=self.fs)
        func = tools.get(tool_id)
        if not func:
            # Maybe it is aliased or needs prefix?
            # Try searching
            for k, v in tools.items():
                if k.endswith(tool_id):  # heuristic
                    func = v
                    break

        if not func:
            raise ValueError(f"Unknown tool: {tool_id}")

        return func(**args)
