from unittest.mock import MagicMock, patch

from codex_mesh.config import CodexMeshConfig
from codex_mesh.plugins.loader import load_skills


def test_load_skills_success():
    config = MagicMock(spec=CodexMeshConfig)
    config.skills = ["my_plugin"]
    registry = MagicMock()

    with patch("importlib.import_module") as mock_import:
        mock_module = MagicMock()
        mock_import.return_value = mock_module

        # Test loading
        load_skills(config, registry)

        mock_import.assert_called_with("my_plugin")
        mock_module.register.assert_called_once_with(registry)


def test_load_skills_import_error(caplog):
    config = MagicMock(spec=CodexMeshConfig)
    config.skills = ["bad_plugin"]
    registry = MagicMock()

    with patch("importlib.import_module", side_effect=ImportError("No module")):
        load_skills(config, registry)

        # Should log warning but not crash
        assert "Failed to load skill" in caplog.text


def test_load_skills_no_register_function():
    config = MagicMock(spec=CodexMeshConfig)
    config.skills = ["plugin_no_reg"]
    registry = MagicMock()

    with patch("importlib.import_module") as mock_import:
        mock_module = MagicMock()
        del mock_module.register  # Ensure no register attr
        # Or mock_module.register = "not callable"

        mock_import.return_value = mock_module

        load_skills(config, registry)
        # Should just pass silently or log? The code doesn't log if register is missing, acts safely.
        # But we should ensure no exception.
