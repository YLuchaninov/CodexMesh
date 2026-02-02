from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GeminiSettings:
    """
    In-memory Gemini configuration for the Control Plane.

    Security:
      - Do NOT persist api_key to disk by default.
      - UI may keep it in browser localStorage.
    """

    api_key: str | None = None
    model: str = "gemini-2.5-flash"
    temperature: float = 0.2

    def __post_init__(self):
        import os

        if not self.api_key:
            self.api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

    def has_key(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def key_last4(self) -> str | None:
        if not self.has_key():
            return None
        k = (self.api_key or "").strip()
        return k[-4:] if len(k) >= 4 else "***"

    def public_view(self) -> dict[str, object]:
        return {
            "provider": "gemini",
            "has_key": self.has_key(),
            "key_last4": self.key_last4(),
            "model": self.model,
            "temperature": self.temperature,
        }

    def update(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
    ) -> None:
        if api_key is not None:
            cleaned = api_key.strip()
            self.api_key = cleaned if cleaned else None
        if model is not None and model.strip():
            self.model = model.strip()
        if temperature is not None:
            self.temperature = float(temperature)
