"""
Translation module for Autopilot.
"""

from .routing import LLMProfile

# Simple instructions to keep structural elements intact
TRANSLATE_PROMPT = """
You are a technical translator.
Translate the following query to English, but STRICTLY PRESERVE:
- File paths (e.g. src/main.py)
- Function/Class names (e.g. AuditService, method_name)
- Integers and specific values
- JSON-like structures
- Code snippets

Original Query ({lang}):
{text}

Output ONLY the translated text. Do not add "Translation:" or quotes.
"""


def translate_to_en_preserve_tokens(text: str, llm_config: LLMProfile | None = None) -> str:
    """
    Translate text to English using available LLM, preserving technical tokens.
    If no LLM is configured effectively, returns original text (graceful degradation).
    """
    if not llm_config:
        return text

    # Simple heuristic to skip translation if it looks like English or code
    try:
        if text.isascii():
            # If strictly ascii, it's likely English or code
            return text
    except Exception:
        pass

    try:
        from langchain_core.messages import HumanMessage

        from .routing import LLMFactory

        llm = LLMFactory.create(llm_config)
        if not llm:
            return text

        prompt = TRANSLATE_PROMPT.format(lang="auto", text=text)

        # This is sync, so we block. Ideally we'd be async everywhere.
        # But this function signature is sync.
        # We'll use ainvoke inside loops if possible, but here we invoke.
        resp = llm.invoke([HumanMessage(content=prompt)])
        return str(resp.content).strip()

    except Exception:
        # Fallback to original
        return text
