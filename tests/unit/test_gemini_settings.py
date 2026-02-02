"""
Unit tests for GeminiSettings.

Tests LLM settings management including key storage, updates, and public view.
"""

from codex_mesh.llm.gemini_settings import GeminiSettings


class TestGeminiSettingsInit:
    """Tests for GeminiSettings initialization."""

    def test_default_values(self):
        """Test that defaults are set correctly."""
        settings = GeminiSettings()

        assert settings.api_key is None
        assert settings.model == "gemini-2.5-flash"  # Actual default from code
        assert settings.temperature == 0.2  # Actual default from code

    def test_custom_init(self):
        """Test initialization with custom values."""
        settings = GeminiSettings(api_key="test-key", model="gemini-1.5-pro", temperature=0.7)

        assert settings.api_key == "test-key"
        assert settings.model == "gemini-1.5-pro"
        assert settings.temperature == 0.7


class TestHasKey:
    """Tests for has_key method."""

    def test_has_key_false_when_none(self):
        """Test has_key returns False when no key set."""
        settings = GeminiSettings()

        assert settings.has_key() is False

    def test_has_key_false_when_empty(self):
        """Test has_key returns False for empty string."""
        settings = GeminiSettings(api_key="")

        assert settings.has_key() is False

    def test_has_key_false_when_whitespace(self):
        """Test has_key returns False for whitespace-only key."""
        settings = GeminiSettings(api_key="   ")

        assert settings.has_key() is False

    def test_has_key_true_when_set(self):
        """Test has_key returns True when key is set."""
        settings = GeminiSettings(api_key="valid-key-123")

        assert settings.has_key() is True


class TestKeyLast4:
    """Tests for key_last4 method."""

    def test_key_last4_returns_last_4_chars(self):
        """Test key_last4 returns last 4 characters."""
        settings = GeminiSettings(api_key="my-super-secret-key")

        result = settings.key_last4()

        assert result == "-key"

    def test_key_last4_short_key(self):
        """Test key_last4 with key shorter than 4 chars."""
        settings = GeminiSettings(api_key="abc")

        result = settings.key_last4()

        assert result == "***"

    def test_key_last4_no_key(self):
        """Test key_last4 returns None when no key."""
        settings = GeminiSettings()

        result = settings.key_last4()

        assert result is None


class TestUpdate:
    """Tests for update method."""

    def test_update_api_key(self):
        """Test updating API key."""
        settings = GeminiSettings()

        settings.update(api_key="new-key")

        assert settings.api_key == "new-key"

    def test_update_model(self):
        """Test updating model name."""
        settings = GeminiSettings()

        settings.update(model="gemini-1.5-pro")

        assert settings.model == "gemini-1.5-pro"

    def test_update_temperature(self):
        """Test updating temperature."""
        settings = GeminiSettings()

        settings.update(temperature=0.8)

        assert settings.temperature == 0.8

    def test_update_multiple_fields(self):
        """Test updating multiple fields at once."""
        settings = GeminiSettings()

        settings.update(api_key="key", model="pro", temperature=0.5)

        assert settings.api_key == "key"
        assert settings.model == "pro"
        assert settings.temperature == 0.5

    def test_update_none_doesnt_overwrite(self):
        """Test that None values don't overwrite existing values."""
        settings = GeminiSettings(api_key="original-key", model="original-model")

        settings.update(api_key=None, model=None)

        assert settings.api_key == "original-key"
        assert settings.model == "original-model"

    def test_update_empty_key_clears(self):
        """Test that empty string clears the key."""
        settings = GeminiSettings(api_key="original-key")

        settings.update(api_key="")

        assert settings.api_key is None


class TestPublicView:
    """Tests for public_view method."""

    def test_public_view_structure(self):
        """Test public_view returns expected structure."""
        settings = GeminiSettings(api_key="test-key-12345")

        view = settings.public_view()

        assert "model" in view
        assert "temperature" in view
        assert "has_key" in view
        assert "provider" in view

    def test_public_view_does_not_expose_full_key(self):
        """Test that full API key is not exposed in public view."""
        settings = GeminiSettings(api_key="super-secret-key")

        view = settings.public_view()

        # Should not contain the full key anywhere
        assert "api_key" not in view  # api_key field should not exist

    def test_public_view_shows_key_last4(self):
        """Test that last 4 chars of key are shown."""
        settings = GeminiSettings(api_key="my-super-secret-key")

        view = settings.public_view()

        assert view["key_last4"] == "-key"

    def test_public_view_has_key_reflects_state(self):
        """Test has_key in public view reflects actual state."""
        settings_with_key = GeminiSettings(api_key="key123")
        settings_without_key = GeminiSettings()

        view_with = settings_with_key.public_view()
        view_without = settings_without_key.public_view()

        assert view_with["has_key"] is True
        assert view_without["has_key"] is False

    def test_public_view_no_key_no_last4(self):
        """Test that key_last4 is None when no key."""
        settings = GeminiSettings()

        view = settings.public_view()

        assert view.get("key_last4") is None


class TestTemperatureValidation:
    """Tests for temperature value handling."""

    def test_temperature_in_valid_range(self):
        """Test temperature accepts valid range values."""
        settings = GeminiSettings(temperature=0.0)
        assert settings.temperature == 0.0

        settings.update(temperature=1.0)
        assert settings.temperature == 1.0

        settings.update(temperature=0.5)
        assert settings.temperature == 0.5


class TestModelNames:
    """Tests for model name handling."""

    def test_accepts_various_model_names(self):
        """Test that various model names are accepted."""
        models = [
            "gemini-pro",
            "gemini-1.5-flash",
            "gemini-1.5-pro",
            "gemini-1.0-pro",
        ]

        for model in models:
            settings = GeminiSettings(model=model)
            assert settings.model == model
