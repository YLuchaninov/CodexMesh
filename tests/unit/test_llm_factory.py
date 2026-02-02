import os
from unittest.mock import MagicMock, patch

import pytest

from codex_mesh.llm import routing
from codex_mesh.llm.routing import LLMFactory, LLMProfile


@pytest.fixture(autouse=True)
def mock_routing_deps():
    """Force per-provider flags=True and inject mock classes."""
    with (
        patch.object(routing, "_HAS_CORE", True),
        patch.object(routing, "_HAS_GOOGLE", True),
        patch.object(routing, "_HAS_ANTHROPIC", True),
        patch.object(routing, "_HAS_OPENAI", True),
        patch.object(routing, "_HAS_MISTRAL", True),
        patch.object(routing, "_HAS_OLLAMA", True),
        patch.object(routing, "ChatGoogleGenerativeAI", MagicMock(), create=True) as m_google,
        patch.object(routing, "ChatAnthropic", MagicMock(), create=True) as m_anthropic,
        patch.object(routing, "ChatOllama", MagicMock(), create=True) as m_ollama,
        patch.object(routing, "ChatOpenAI", MagicMock(), create=True) as m_openai,
        patch.object(routing, "ChatMistralAI", MagicMock(), create=True) as m_mistral,
    ):
        yield {
            "google": m_google,
            "anthropic": m_anthropic,
            "ollama": m_ollama,
            "openai": m_openai,
            "mistral": m_mistral,
        }


def test_create_google_provider(mock_routing_deps):
    # Setup
    profile = LLMProfile(
        name="test_google", model="gemini-pro", provider="google", api_key_env="TEST_GOOGLE_KEY"
    )

    with patch.dict(os.environ, {"TEST_GOOGLE_KEY": "fake-key"}):
        # Act
        model = LLMFactory.create(profile)

        # Assert
        assert model is not None
        mock_routing_deps["google"].assert_called_once_with(
            model="gemini-pro", temperature=0.0, max_output_tokens=4096, google_api_key="fake-key"
        )


def test_create_anthropic_provider(mock_routing_deps):
    # Setup
    profile = LLMProfile(
        name="test_anthropic",
        model="claude-3",
        provider="anthropic",
        api_key_env="TEST_ANTHROPIC_KEY",
    )

    with patch.dict(os.environ, {"TEST_ANTHROPIC_KEY": "fake-key"}):
        # Act
        model = LLMFactory.create(profile)

        # Assert
        assert model is not None
        mock_routing_deps["anthropic"].assert_called_once_with(
            model_name="claude-3", temperature=0.0, max_tokens=4096, anthropic_api_key="fake-key"
        )


def test_create_ollama_provider(mock_routing_deps):
    # Setup
    profile = LLMProfile(
        name="test_ollama", model="mistral", provider="ollama", api_base="http://test-host:11434"
    )

    # Act
    model = LLMFactory.create(profile)

    # Assert
    assert model is not None
    mock_routing_deps["ollama"].assert_called_once_with(
        model="mistral", temperature=0.0, base_url="http://test-host:11434"
    )


def test_create_openai_provider(mock_routing_deps):
    # Setup
    profile = LLMProfile(
        name="test_openai", model="gpt-4", provider="openai", api_key_env="TEST_OPENAI_KEY"
    )

    with patch.dict(os.environ, {"TEST_OPENAI_KEY": "fake-key"}):
        # Act
        model = LLMFactory.create(profile)

        # Assert
        assert model is not None
        mock_routing_deps["openai"].assert_called_once_with(
            model="gpt-4", temperature=0.0, max_tokens=4096, api_key="fake-key"
        )


def test_create_mistral_provider(mock_routing_deps):
    # Setup
    profile = LLMProfile(
        name="test_mistral",
        model="mistral-large-latest",
        provider="mistral",
        api_key_env="TEST_MISTRAL_KEY",
    )

    with patch.dict(os.environ, {"TEST_MISTRAL_KEY": "fake-key"}):
        # Act
        model = LLMFactory.create(profile)

        # Assert
        assert model is not None
        mock_routing_deps["mistral"].assert_called_once_with(
            model="mistral-large-latest", temperature=0.0, max_tokens=4096, api_key="fake-key"
        )


def test_create_unsupported_provider(mock_routing_deps):
    profile = LLMProfile(name="test_unknown", model="unknown", provider="unknown")
    assert LLMFactory.create(profile) is None


def test_create_missing_api_key(mock_routing_deps):
    profile = LLMProfile(
        name="test_google", model="gemini-pro", provider="google", api_key_env="MISSING_KEY"
    )
    with patch.dict(os.environ, {}, clear=True):
        assert LLMFactory.create(profile) is None
