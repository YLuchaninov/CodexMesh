import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from codex_mesh.llm.autopilot_agent import AutopilotAgent


async def _test_autopilot_plan_parsing_impl():
    # Mock services
    an = MagicMock()
    reg = MagicMock()

    # Mock registry list with schema
    intent_def = MagicMock()
    intent_def.id = "intent.test"
    intent_def.description = "Test Intent"
    intent_def.input_schema = {
        "properties": {"arg1": {"type": "string", "description": "Argument 1"}}
    }
    reg.list.return_value = [intent_def]
    reg.get.return_value = intent_def

    # Mock settings
    settings = MagicMock()
    settings.api_key = "dummy"
    settings.model = "gpt-4"

    # Mock LLM and LLMFactory
    mock_llm = AsyncMock()

    # Plans and Responses
    plan_json = """
    ```json
    {
      "language": "en",
      "plan": [
        {"kind": "intent", "id": "intent.test", "args": {"arg1": "value"}}
      ]
    }
    ```
    """

    msg_plan = MagicMock()
    msg_plan.content = plan_json

    msg_synth = MagicMock()
    msg_synth.content = "Final Answer"

    mock_llm.ainvoke.side_effect = [msg_plan, msg_synth]

    with (
        patch("codex_mesh.llm.routing.LLMFactory.create", return_value=mock_llm),
        patch(
            "codex_mesh.llm.autopilot_agent.translate_to_en_preserve_tokens",
            return_value="test query",
        ),
    ):
        agent = AutopilotAgent(an, reg, settings)

        with patch.object(agent, "_execute_intent_action") as mock_exec:
            mock_exec.return_value = {"output": "result", "artifacts": {}}

            res = await agent.ask("test query")

            assert res["answer"] == "Final Answer"
            assert len(res["evidence"]) == 1
            assert res["evidence"][0]["id"] == "intent.test"
            assert res["evidence"][0]["status"] == "success"


def test_autopilot_plan_parsing():
    asyncio.run(_test_autopilot_plan_parsing_impl())


async def _test_autopilot_translation_fallback_impl():
    # Test fallback if no config
    from codex_mesh.llm.translate import translate_to_en_preserve_tokens

    res = translate_to_en_preserve_tokens("тест", None)
    assert res == "тест"

    # Test valid translation
    from codex_mesh.llm.routing import LLMProfile

    profile = LLMProfile(name="test", model="m", provider="p", api_key="k")

    # Mock Factory to return LLM
    mock_llm = MagicMock()
    msg = MagicMock()
    msg.content = "test"
    # translate uses sync invoke if possible per my implementation?
    # Wait, my translate implementation uses: `resp = llm.invoke(...)`
    # Ensure mock_llm.invoke works
    mock_llm.invoke.return_value = msg

    with patch("codex_mesh.llm.routing.LLMFactory.create", return_value=mock_llm):
        res = translate_to_en_preserve_tokens("тест", profile)
        assert res == "test"


def test_autopilot_translation_fallback():
    asyncio.run(_test_autopilot_translation_fallback_impl())
