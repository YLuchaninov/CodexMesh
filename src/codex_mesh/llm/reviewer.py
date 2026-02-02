"""
CodexMesh Reviewer Agent.
"""

import json
import os
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from langchain_core.messages import HumanMessage, SystemMessage  # type: ignore

try:
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

    _HAS_LANGCHAIN = True
except ImportError:
    _HAS_LANGCHAIN = False
    HumanMessage = Any  # type: ignore
    SystemMessage = Any  # type: ignore
    AIMessage = Any  # type: ignore

from ..services.analysis_service import AnalysisService
from ..services.fs_service import FileSystemService
from .command_handler import CommandRegistry
from .gemini_settings import GeminiSettings


@dataclass
class EvidenceItem:
    kind: str
    title: str
    content: str
    data: Any = field(default_factory=dict)


Mode = Literal["quick", "standard", "deep"]


class ReviewerAgent:
    """
    Local Reviewer that can answer about:
      - code quality / hotspots
      - what CodexMesh MCP server provides
      - where to look in codebase (based on search evidence)
    """

    def __init__(
        self,
        analysis_service: AnalysisService,
        fs_service: FileSystemService,
        *,
        settings: GeminiSettings,
    ):
        self.analysis = analysis_service
        self.fs = fs_service
        self.settings = settings
        self.commands = CommandRegistry()

        # Initialize Workflow Engine
        from ..workflows import IntentRegistry, IntentRouter
        from ..workflows.runtime import RuntimeFactory

        self.registry = IntentRegistry("src/codex_mesh/workflows/definitions")
        # Ensure we load correct path
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        intents_path = os.path.join(base_dir, "src", "codex_mesh", "workflows", "definitions")
        # Fallback if generic path fails
        if not os.path.exists(intents_path):
            intents_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "workflows", "definitions"
            )

        self.registry = IntentRegistry(intents_path)
        self.registry.load()

        # Router
        # Try to get config from analysis service context
        try:
            self.config = self.analysis.config
            model = self.config.embedding.model
        except Exception:
            model = "BAAI/bge-small-en-v1.5"

        self.router = IntentRouter(model_name=model)
        self.router.build_index(
            [
                {"id": it.id, "description": it.description, "examples": it.examples}
                for it in self.registry.list()
            ]
        )

        # Runner & Executor
        self.runner = RuntimeFactory.create(self.analysis, self.registry)

    async def _get_llm(self):
        from .routing import LLMFactory, LLMProfile, get_profile

        # Determine profile name
        # Priority: 1. "ui_active" in config  2. analysis context config default 3. "gemini_pro"

        try:
            if hasattr(self.analysis.manager, "server") and self.analysis.manager.server:
                cfg = self.analysis.manager.server.context.config
                # If we have "ui_active" profile, use it
                if "ui_active" in cfg.profiles:
                    return LLMFactory.create(cfg.profiles["ui_active"])

                # Otherwise try to find a default or use first available
                if cfg.profiles:
                    # Prefer gemini_pro or first one
                    p_name = (
                        "gemini_pro" if "gemini_pro" in cfg.profiles else next(iter(cfg.profiles))
                    )
                    return LLMFactory.create(cfg.profiles[p_name])
        except Exception:
            pass

        # Use Routing Layer
        profile = get_profile("gemini_pro")
        # Ensure we inject legacy settings if they exist and are non-default
        if self.settings.has_key() and self.settings.model:
            # Create custom profile from settings
            profile = LLMProfile(
                name="legacy_settings",
                model=self.settings.model,
                provider="google",
                temperature=self.settings.temperature,
                api_key_env="GOOGLE_API_KEY",  # We assume it is there or we override in env
            )
            # Update env for LLMFactory if needed (since settings.api_key might not be in env)
            if self.settings.api_key:
                os.environ["GOOGLE_API_KEY"] = self.settings.api_key

        return LLMFactory.create(profile)

    async def ask(
        self,
        query: str,
        *,
        mode: Mode = "standard",
        history: list[dict[str, Any]] | None = None,
        pinned_context: str | None = None,
        summary: str | None = None,
    ) -> dict:
        import logging

        from .routing import safe_llm_call

        logger = logging.getLogger(__name__)
        logger.info(
            f"ReviewerAgent.ask: query='{query}', mode='{mode}', history_len={len(history) if history else 0}"
        )

        # Check for commands first
        if self.commands.is_command(query):
            result = self.commands.execute(query)
            if result:
                return {
                    "answer": result.content,
                    "evidence": [],
                    "checked_items": [f"Executed command: {query}"],
                }

        # 1. Route Intent
        intent_id, slots = self.router.route(query)
        logger.info(f"ReviewerAgent.ask: routed to intent='{intent_id}'")

        # Fallback to "general" if not found or generic
        if not intent_id:
            intent_id = "general"

        evidence: list[EvidenceItem] = []
        checked: list[str] = []

        # Only add capabilities if explicitly requested
        if intent_id == "intent.mcp_capabilities":
            evidence.append(
                EvidenceItem(
                    kind="capabilities",
                    title="CodexMesh capabilities",
                    content=(
                        "Available capabilities: graph-based navigation, name search, semantic search, "
                        "RepoMap generation, Hotspot report.\n"
                        "Intents supported: search, dependency analysis, hotspots, path finding."
                    ),
                )
            )

        # 2. Execute Workflow
        intent_def = self.registry.get(intent_id)
        workflow_executed = False

        if intent_def and intent_def.workflow:
            from ..workflows.engine.input_prep import prepare_intent_input

            prepared_input = prepare_intent_input(intent_def, query=query, slots=slots)
            run_res = self.runner.run(
                intent_def.workflow,
                context={"input": prepared_input, "query": query, "intent": intent_id},
            )
            workflow_executed = True

            if run_res.success:
                # The result is typically a markdown string in changes["result"]
                content = str(run_res.changes.get("result", "No output generated."))

                evidence.append(
                    EvidenceItem(
                        kind="workflow_result",
                        title=f"Result: {intent_id}",
                        content=content,
                        data=run_res.changes,
                    )
                )
                checked.append(f"Executed workflow {intent_id}")
            else:
                evidence.append(
                    EvidenceItem(
                        kind="error",
                        title="Workflow Error",
                        content="Workflow failed to execute.\n\nLogs:\n" + "\n".join(run_res.logs),
                        data={"logs": run_res.logs},
                    )
                )
                checked.append(f"Failed workflow {intent_id}")

        # Fallback for "general" or failed workflows
        if (not workflow_executed) or (intent_id == "general"):
            # Run RepoMap and Semantic Search as fallback context
            rm = self.analysis.get_repo_map(token_budget=self.config.review.repo_map_budget)
            evidence.append(
                EvidenceItem(kind="repomap", title="RepoMap", content=rm, data={"map": rm})
            )

            if mode in ["standard", "deep"]:
                sem = self.analysis.semantic_search(query, k=self.config.review.search_k)
                summary = f"Found {len(sem)} semantic matches."
                if sem:
                    summary += "\n" + "\n".join(
                        [
                            f"- {item['name']} (score: {int(item['score'] * 100)}%)"
                            for item in sem[:3]
                        ]
                    )
                evidence.append(
                    EvidenceItem(
                        kind="semantic", title="Semantic Search", content=summary, data=sem
                    )
                )
                checked.append("Ran semantic search")

        llm = await self._get_llm()
        if llm is None:
            # Deterministic synthesis
            answer = self._synthesize_fallback_answer(intent_id, evidence)
            reason = (
                "LLM disabled (no API key)"
                if _HAS_LANGCHAIN
                else "LLM disabled (dependencies missing)"
            )
            return {
                "answer": answer,
                "evidence": [asdict(e) for e in evidence],
                "checked_items": checked + [reason],
                "intent": intent_id,
            }

        # Prepare context for LLM
        ctx_parts = []
        for e in evidence:
            ctx_parts.append(f"=== {e.kind}:{e.title} ===\n{e.content}")
            if e.data:
                # Dump data if it helps
                # Truncate large lists
                d = e.data
                if isinstance(d, list) and len(d) > 10:
                    d = d[:10]
                ctx_parts.append(f"Structured Data:\n{json.dumps(d, indent=2, default=str)}")

        # Safety check for message types (though Any would swallow it, explicit check is better)
        if not _HAS_LANGCHAIN:
            # Should be caught by llm is None above if _get_llm returns None, but double check
            return {
                "answer": "Error: LLM dependencies missing.",
                "evidence": [],
                "checked_items": checked + ["Failed: langchain missing"],
                "intent": intent_id,
            }

        system = SystemMessage(
            content=(
                "You are the **CodexMesh Reviewer Agent**.\n"
                "You have access to a semantic understanding of this codebase through the CodexMesh Graph.\n"
                "Your goal is to answer questions by leveraging the provided **Evidence** (Search results, Hotspots, RepoMaps, Workflow traces).\n"
                "\n"
                "### Guidelines:\n"
                "1. **Be Specific**: Always cite specific filenames, function names, and graph relationships found in evidence.\n"
                "2. **Explain Why**: When suggesting a refactor or identifying a hotspot, explain the metrics (complexity, churn, coupling).\n"
                "3. **Use Graph Thinking**: Don't just treat code as text; discuss dependencies (`A imports B`), flows (`A calls B`), and architecture.\n"
                "4. **MCP Awareness**: If asked how to do something you cannot do directly, suggest the appropriate MCP tool (e.g., 'Use `get_subgraph` to see connections').\n"
                "\n"
                "Respond in clear, structured Markdown."
            )
        )

        # Build message history with budget management
        messages: list[Any] = [system]

        if pinned_context:
            messages.append(
                SystemMessage(content=f"Pinned context (user instructions):\n{pinned_context}")
            )

        if summary:
            messages.append(SystemMessage(content=f"Conversation summary so far:\n{summary}"))

        # Budget history based on mode
        history_limit = {
            "quick": self.config.review.history_limit_quick,
            "standard": self.config.review.history_limit_standard,
            "deep": self.config.review.history_limit_deep,
        }.get(mode, self.config.review.history_limit_standard)
        char_limit = self.config.review.char_limit

        if history:
            # Take last N messages
            recent_history = history[-history_limit:]

            # Check char limit and truncate from front if needed
            total_chars = 0
            truncated_history: list[dict[str, Any]] = []
            for h in reversed(recent_history):
                content = h.get("content", "")
                if total_chars + len(content) > char_limit:
                    break
                truncated_history.insert(0, h)
                total_chars += len(content)

            if len(truncated_history) < len(history):
                messages.append(
                    SystemMessage(content="Older messages omitted to stay within context limit.")
                )

            for h in truncated_history:
                role = h.get("role")
                h_content = h.get("content", "")
                if role == "user":
                    messages.append(HumanMessage(content=h_content))
                elif role == "agent":
                    messages.append(AIMessage(content=h_content))
                elif role == "system":
                    messages.append(SystemMessage(content=h_content))

        ctx = "\n\n".join(ctx_parts)
        user_msg = HumanMessage(content=f"Evidence:\n{ctx}\n\nUser question: {query}")
        messages.append(user_msg)

        fallback_answer = self._synthesize_fallback_answer(intent_id, evidence)
        answer = await safe_llm_call(llm, messages, fallback=fallback_answer)

        return {
            "answer": answer,
            "evidence": [asdict(e) for e in evidence],
            "checked_items": checked,
            "intent": intent_id,
        }

    def _synthesize_fallback_answer(self, intent: str, evidence: list[EvidenceItem]) -> str:
        """Synthesize a deterministic answer when LLM is unavailable."""
        lines = []

        if intent == "review":
            lines.append("### Code Quality Review (Deterministic)")
            hotspot_item = next((e for e in evidence if e.kind == "hotspot"), None)
            if hotspot_item and hotspot_item.data:
                report = hotspot_item.data.get("report", [])
                if report:
                    lines.append("Top Hotspots:")
                    for item in report[:5]:
                        lines.append(f"- **{item['node_id']}** (Total Score: {item['total']:.1f})")
                        if item["issues"]:
                            lines.append(f"  - {len(item['issues'])} issues detected")
                else:
                    lines.append("No hotspots found.")
            else:
                lines.append("Hotspot analysis not available.")

        elif intent == "search":
            lines.append("### Search Results (Deterministic)")
            search_item = next((e for e in evidence if e.kind == "search"), None)
            if search_item and search_item.data:
                lines.append(f"Found {len(search_item.data)} matches:")
                for match in search_item.data[:5]:
                    lines.append(
                        f"- `{match['name']}` in `{match['file_path']}:{match['line_start']}`"
                    )
            else:
                lines.append("No matches found.")

        else:
            lines.append(f"### Analysis Result ({intent})")
            lines.append("Check the evidence tabs for details.")

        lines.append("\n_Note: Configure Gemini API Key for AI-driven insights._")
        return "\n".join(lines)
