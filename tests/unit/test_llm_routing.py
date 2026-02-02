"""
Unit tests for logic in src/codex_mesh/llm/routing.py
"""

import os
import sys
from unittest.mock import MagicMock, patch

# Mock langchain modules BEFORE importing routing
mock_lc = MagicMock()
mock_lc_genai = MagicMock()
sys.modules["langchain_core"] = mock_lc
sys.modules["langchain_core.language_models"] = mock_lc
sys.modules["langchain_google_genai"] = mock_lc_genai

# Now it is safe to import
from codex_mesh.llm.routing import (  # noqa: E402
    DEFAULT_PROFILES,
    LLMFactory,
    LLMProfile,
    get_profile,
)


def test_llm_profile_defaults():
    profile = LLMProfile(name="test", model="gpt-4", provider="openai")
    assert profile.max_tokens == 4096
    assert profile.temperature == 0.0


def test_get_profile_defaults():
    # Should fallback to gemini_pro if unknown
    p = get_profile("unknown_profile")
    assert p.name == "gemini_pro"
    assert p.provider == "google"


def test_get_profile_custom():
    custom = {"my_custom": LLMProfile(name="my_custom", model="foo", provider="bar")}
    p = get_profile("my_custom", custom_profiles=custom)
    assert p.name == "my_custom"
    assert p.model == "foo"


@patch.dict(os.environ, {"GOOGLE_API_KEY": "fake_key"})
def test_create_gemini_client():
    # Force per-provider flags to be True for this test
    with (
        patch("codex_mesh.llm.routing._HAS_CORE", True),
        patch("codex_mesh.llm.routing._HAS_GOOGLE", True),
        patch("codex_mesh.llm.routing.ChatGoogleGenerativeAI", create=True) as MockClient,
    ):
        profile = DEFAULT_PROFILES["gemini_pro"]
        client = LLMFactory.create(profile)
        assert client is not None
        MockClient.assert_called_once()
        _, kwargs = MockClient.call_args
        assert kwargs["google_api_key"] == "fake_key"
        assert kwargs["model"] == profile.model


@patch.dict(os.environ, {}, clear=True)
def test_create_gemini_client_no_key():
    with (
        patch("codex_mesh.llm.routing._HAS_CORE", True),
        patch("codex_mesh.llm.routing._HAS_GOOGLE", True),
    ):
        profile = DEFAULT_PROFILES["gemini_pro"]
        client = LLMFactory.create(profile)
        assert client is None
