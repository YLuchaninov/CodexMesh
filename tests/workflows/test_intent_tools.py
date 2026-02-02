import json
from pathlib import Path

from codex_mesh.workflows.runtime import RuntimeFactory

# Assuming we can instantiate RuntimeFactory or get its internal registry
# If RuntimeFactory requires complex deps, we might mock


def test_intents_refer_to_existing_tools():
    """
    Validate that all tool_names in intent JSON definitions exist in the runtime registry.
    """
    # 1. Get all available tools from RuntimeFactory
    # We can probably use a static method or instantiate with dummy config if needed
    # Or just inspect the registered tools if they are static
    # Let's try to inspect _build_tools if accessible or similar

    from unittest.mock import MagicMock

    mock_analysis = MagicMock()
    mock_registry = MagicMock()

    # We only need the keys, so the mock implementation doesn't matter much
    # provided it has the attributes accessed during build (like methods)
    tools_map = RuntimeFactory._build_tools(mock_analysis, mock_registry)
    allowed_tools = set(tools_map.keys())

    # 2. Iterate over all intent .json files
    intents_dir = Path(__file__).parents[2] / "src" / "codex_mesh" / "workflows" / "definitions"
    assert intents_dir.exists(), f"Intents dir not found at {intents_dir}"

    for intent_file in intents_dir.glob("*.json"):
        with open(intent_file) as f:
            data = json.load(f)

        # Check standard intent structure
        def check_steps(steps_list, current_intent_name):
            for i, step in enumerate(steps_list):
                # 'tool' action should have 'tool_name'
                if step.get("action") == "tool":
                    tool_name = step.get("tool_name")
                    if not tool_name:
                        tool_name = step.get("tool")

                    if tool_name:
                        assert tool_name in allowed_tools, (
                            f"Intent '{current_intent_name}' step {i} references "
                            f"unknown tool '{tool_name}'. Available: {sorted(allowed_tools)}"
                        )

                # Recursion
                if step.get("action") == "loop":
                    check_steps(step.get("steps", []), current_intent_name)

                if step.get("action") == "branch":
                    check_steps(step.get("then", []), current_intent_name)
                    check_steps(step.get("else", []), current_intent_name)

        steps = data.get("steps", [])
        if not steps and "workflow" in data:
            steps = data["workflow"].get("steps", [])

        check_steps(steps, intent_file.name)
