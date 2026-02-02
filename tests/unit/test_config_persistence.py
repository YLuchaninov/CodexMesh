import json
import os
from unittest.mock import patch

import pytest

from codex_mesh.api.manager import ProjectManager
from codex_mesh.config import CodexMeshConfig


@pytest.fixture
def clean_env():
    """Ensure specific env vars are unset before test."""
    old_model = os.environ.get("CODEX_MESH_EMBEDDING_MODEL")
    if old_model:
        del os.environ["CODEX_MESH_EMBEDDING_MODEL"]
    yield
    if old_model:
        os.environ["CODEX_MESH_EMBEDDING_MODEL"] = old_model


def test_update_from_env(clean_env):
    """Test that update_from_env applies environment variables."""
    config = CodexMeshConfig()
    initial_model = config.embedding.model

    os.environ["CODEX_MESH_EMBEDDING_MODEL"] = "env_model_test"
    config.update_from_env()

    assert config.embedding.model == "env_model_test"
    assert config.embedding.model != initial_model


def test_config_precedence(clean_env, tmp_path):
    """
    Test Precedence: Env > File > Default
    """
    manager = ProjectManager()

    # create a dummy config file
    config_file = tmp_path / "test_config.json"
    file_data = {"embedding": {"model": "file_model_test"}}
    config_file.write_text(json.dumps(file_data))

    # 1. Test File > Default (No Env)
    with patch.object(manager, "_get_config_path", return_value=config_file):
        config = manager.load_user_config()
        assert config.embedding.model == "file_model_test"

    # 2. Test Env > File
    os.environ["CODEX_MESH_EMBEDDING_MODEL"] = "env_model_test"
    with patch.object(manager, "_get_config_path", return_value=config_file):
        config = manager.load_user_config()
        assert config.embedding.model == "env_model_test"

    # 3. Test Default (No Env, No File)
    if "CODEX_MESH_EMBEDDING_MODEL" in os.environ:
        del os.environ["CODEX_MESH_EMBEDDING_MODEL"]

    non_existent = tmp_path / "no_exist.json"
    with patch.object(manager, "_get_config_path", return_value=non_existent):
        config = manager.load_user_config()
        # Should be default
        assert config.embedding.model == "BAAI/bge-small-en-v1.5"
