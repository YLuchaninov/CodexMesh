"""
LLM Routing Layer.

Per advanced.md: Agent actions should specify which LLM profile to use.
Enables optimized cost, latency, and quality tradeoffs.
"""

import logging
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel  # type: ignore

logger = logging.getLogger(__name__)


# Per-provider availability flags (P0-1 fix: import each provider independently)
_HAS_CORE = False
_HAS_GOOGLE = False
_HAS_ANTHROPIC = False
_HAS_OPENAI = False
_HAS_MISTRAL = False
_HAS_OLLAMA = False

# Provider classes (set to None if not available)
ChatGoogleGenerativeAI = None
ChatAnthropic = None
ChatOpenAI = None
ChatMistralAI = None
ChatOllama = None
BaseChatModel: Any = Any  # type: ignore

try:
    from langchain_core.language_models import BaseChatModel  # type: ignore

    _HAS_CORE = True
except ImportError:
    pass

if _HAS_CORE:
    try:
        from langchain_google_genai import (
            ChatGoogleGenerativeAI as _ChatGoogleGenerativeAI,  # type: ignore
        )

        ChatGoogleGenerativeAI = _ChatGoogleGenerativeAI
        _HAS_GOOGLE = True
    except ImportError:
        pass

    try:
        from langchain_anthropic import ChatAnthropic as _ChatAnthropic  # type: ignore

        ChatAnthropic = _ChatAnthropic
        _HAS_ANTHROPIC = True
    except ImportError:
        pass

    try:
        from langchain_openai import ChatOpenAI as _ChatOpenAI  # type: ignore

        ChatOpenAI = _ChatOpenAI
        _HAS_OPENAI = True
    except ImportError:
        pass

    try:
        from langchain_mistralai import ChatMistralAI as _ChatMistralAI  # type: ignore

        ChatMistralAI = _ChatMistralAI
        _HAS_MISTRAL = True
    except ImportError:
        pass

    try:
        from langchain_community.chat_models import ChatOllama as _ChatOllama  # type: ignore

        ChatOllama = _ChatOllama
        _HAS_OLLAMA = True
    except ImportError:
        pass


def providers_available() -> dict[str, bool]:
    """Return availability status of each LLM provider."""
    return {
        "core": _HAS_CORE,
        "google": _HAS_GOOGLE,
        "anthropic": _HAS_ANTHROPIC,
        "openai": _HAS_OPENAI,
        "mistral": _HAS_MISTRAL,
        "ollama": _HAS_OLLAMA,
    }


@dataclass
class LLMProfile:
    """Configuration for a specific LLM execution profile."""

    name: str
    model: str
    provider: str
    max_tokens: int = 4096
    temperature: float = 0.0
    api_key_env: str = ""
    api_key: str | None = None
    api_base: str | None = None


# Default recommended profiles
DEFAULT_PROFILES = {
    "fast_local": LLMProfile(
        name="fast_local",
        model="mistral",
        provider="ollama",
        max_tokens=2048,
        temperature=0.1,
        api_base="http://localhost:11434",
    ),
    "deep_cloud": LLMProfile(
        name="deep_cloud",
        model="claude-3-opus-20240229",
        provider="anthropic",
        max_tokens=4096,
        temperature=0.0,
        api_key_env="ANTHROPIC_API_KEY",
    ),
    "gemini_pro": LLMProfile(
        name="gemini_pro",
        model="gemini-1.5-pro-latest",
        provider="google",
        max_tokens=8192,
        temperature=0.0,
        api_key_env="GOOGLE_API_KEY",
    ),
}


class LLMFactory:
    """Creates LLM clients based on profiles."""

    @staticmethod
    def create(profile: LLMProfile) -> BaseChatModel | None:
        """
        Create a LangChain chat model from the profile.
        Returns None if provider not supported or API key missing.
        """
        if not _HAS_CORE:
            logger.warning("LangChain core not installed. LLM features disabled.")
            return None

        if profile.provider == "google":
            if not _HAS_GOOGLE:
                logger.warning(
                    "Google LLM provider not available (langchain-google-genai not installed)"
                )
                return None
            api_key = profile.api_key or os.environ.get(profile.api_key_env)
            if not api_key:
                logger.debug("Google API key not provided")
                return None
            return ChatGoogleGenerativeAI(  # type: ignore
                model=profile.model,
                temperature=profile.temperature,
                max_output_tokens=profile.max_tokens,
                google_api_key=api_key,
            )

        if profile.provider == "anthropic":
            if not _HAS_ANTHROPIC:
                logger.warning(
                    "Anthropic LLM provider not available (langchain-anthropic not installed)"
                )
                return None
            api_key = profile.api_key or os.environ.get(profile.api_key_env)
            if not api_key:
                logger.debug("Anthropic API key not provided")
                return None
            return ChatAnthropic(  # type: ignore
                model_name=profile.model,
                temperature=profile.temperature,
                max_tokens=profile.max_tokens,
                anthropic_api_key=api_key,
            )

        if profile.provider == "ollama":
            if not _HAS_OLLAMA:
                logger.warning(
                    "Ollama LLM provider not available (langchain-community not installed)"
                )
                return None
            return ChatOllama(  # type: ignore
                model=profile.model,
                temperature=profile.temperature,
                base_url=profile.api_base or "http://localhost:11434",
            )

        if profile.provider == "openai":
            if not _HAS_OPENAI:
                logger.warning("OpenAI LLM provider not available (langchain-openai not installed)")
                return None
            api_key = profile.api_key or os.environ.get(profile.api_key_env)
            if not api_key:
                logger.debug("OpenAI API key not provided")
                return None
            return ChatOpenAI(  # type: ignore
                model=profile.model,
                temperature=profile.temperature,
                max_tokens=profile.max_tokens,
                api_key=api_key,
            )

        if profile.provider == "mistral":
            if not _HAS_MISTRAL:
                logger.warning(
                    "Mistral LLM provider not available (langchain-mistralai not installed)"
                )
                return None
            api_key = profile.api_key or os.environ.get(profile.api_key_env)
            if not api_key:
                logger.debug("Mistral API key not provided")
                return None
            return ChatMistralAI(  # type: ignore
                model=profile.model,
                temperature=profile.temperature,
                max_tokens=profile.max_tokens,
                api_key=api_key,
            )

        logger.warning(f"Unknown LLM provider: {profile.provider}")
        return None


def get_profile(name: str, custom_profiles: dict[str, LLMProfile] | None = None) -> LLMProfile:
    """Retrieve a profile by name, checking custom config first, then defaults."""
    if custom_profiles and name in custom_profiles:
        return custom_profiles[name]
    return DEFAULT_PROFILES.get(name, DEFAULT_PROFILES["gemini_pro"])


async def safe_llm_call(
    model: BaseChatModel,
    messages: list[Any],
    fallback: str = "[fallback: unable to generate output]",
) -> str:
    """
    Safely call an LLM with fallback logic.

    Per advanced.md: Every critical AI output path must have fallback logic.
    """
    try:
        if model is None:
            return fallback
        resp = await model.ainvoke(messages)
        content = resp.content if hasattr(resp, "content") else str(resp)
        # Handle list[str] or dict cases from multimodal models
        if not isinstance(content, str):
            content = str(content)
        if not content or len(content.strip()) == 0:
            return fallback
        return content
    except Exception as e:
        logger.warning(f"LLM call failed: {e}")
        return fallback
