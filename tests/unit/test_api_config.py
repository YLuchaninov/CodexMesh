from unittest.mock import MagicMock

import pytest

from codex_mesh.config import CodexMeshConfig
from codex_mesh.web.routes import get_system_config, update_system_config


@pytest.fixture
def mock_pm():
    pm = MagicMock()
    pm.server = MagicMock()
    # Create a real config to test merging logic
    pm.server.context.config = CodexMeshConfig()
    return pm


@pytest.mark.asyncio
async def test_get_system_config(mock_pm):
    # Setup
    config = mock_pm.server.context.config
    config.embedding.model = "test-model"

    # Act
    res = await get_system_config(pm=mock_pm)

    # Assert
    assert res["embedding"]["model"] == "test-model"


@pytest.mark.asyncio
async def test_get_system_config_no_project():
    pm = MagicMock()
    pm.server = None
    # Mock load_user_config
    mock_config = CodexMeshConfig()
    mock_config.embedding.model = "fallback-model"
    pm.load_user_config.return_value = mock_config

    res = await get_system_config(pm=pm)
    assert res["embedding"]["model"] == "fallback-model"


@pytest.mark.asyncio
async def test_update_system_config(mock_pm):
    # Act
    updates = {"embedding": {"model": "new-model"}, "hotspot": {"error_weight": 99.9}}
    res = await update_system_config(updates, pm=mock_pm)

    # Assert
    # Check return value
    assert res["embedding"]["model"] == "new-model"
    assert res["hotspot"]["error_weight"] == 99.9
    # Check internal state updated
    config = mock_pm.server.context.config
    assert config.embedding.model == "new-model"
    assert config.hotspot.error_weight == 99.9
    # Check preserved values
    assert config.storage.backend == "rustworkx"  # default


@pytest.mark.asyncio
async def test_update_system_config_redacts_profile_api_key(mock_pm):
    updates = {
        "profiles": {
            "ui_active": {
                "name": "ui_active",
                "provider": "google",
                "model": "gemini-2.5-flash",
                "temperature": 0.2,
                "api_key": "SECRET_TEST_KEY",
            }
        }
    }

    res = await update_system_config(updates, pm=mock_pm)

    # Response must not expose api_key
    assert "profiles" in res
    assert "ui_active" in res["profiles"]
    assert "api_key" not in res["profiles"]["ui_active"]
    # Also ensure raw secret string isn't present accidentally
    assert "SECRET_TEST_KEY" not in str(res)

    # Internal runtime config may keep api_key in-memory
    cfg = mock_pm.server.context.config
    assert cfg.profiles["ui_active"].api_key == "SECRET_TEST_KEY"


@pytest.mark.asyncio
async def test_update_system_config_invalid(mock_pm):
    # Invalid updates shouldn't crash but might raise BadRequest if validation fails
    # CodexMeshConfig doesn't strictly validate types on from_dict but let's try
    # Currently it just re-instantiates.

    # If we pass something that causes from_dict (or constructor) to fail
    pass
