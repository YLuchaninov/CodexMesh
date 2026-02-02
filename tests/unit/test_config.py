"""
Unit tests for the configuration system.
"""

import json

from codex_mesh.config import (
    CodexMeshConfig,
)


def test_config_default_values():
    """Test that default values are correctly initialized."""
    config = CodexMeshConfig()
    assert config.embedding.engine == "fastembed"
    assert config.storage.backend == "rustworkx"
    assert config.hotspot.error_weight == 5.0
    assert config.mcp.tools is True
    assert config.workflows_path == "./workflows"


def test_config_from_dict():
    """Test creating configuration from a dictionary."""
    data = {
        "embedding": {"engine": "custom", "model": "my-model"},
        "storage": {"path": "/tmp/data"},
        "skills": ["skill1", "skill2"],
        "workflows_path": "/tmp/workflows",
    }
    config = CodexMeshConfig.from_dict(data)
    assert config.embedding.engine == "custom"
    assert config.embedding.model == "my-model"
    assert config.storage.path == "/tmp/data"
    assert config.storage.backend == "rustworkx"  # Default
    assert config.skills == ["skill1", "skill2"]
    assert config.workflows_path == "/tmp/workflows"


def test_config_from_file(tmp_path):
    """Test loading configuration from a JSON file."""
    config_data = {
        "embedding": {"model": "file-model"},
        "storage": {"path": str(tmp_path / "data")},
    }
    config_file = tmp_path / "config.json"
    with open(config_file, "w") as f:
        json.dump(config_data, f)

    config = CodexMeshConfig.from_file(config_file)
    assert config.embedding.model == "file-model"
    assert config.storage.path == str(tmp_path / "data")


def test_config_from_env(monkeypatch):
    """Test overriding configuration from environment variables."""
    monkeypatch.setenv("CODEX_MESH_EMBEDDING_MODEL", "env-model")
    monkeypatch.setenv("CODEX_MESH_STORAGE_PATH", "/env/path")

    config = CodexMeshConfig.from_env()
    assert config.embedding.model == "env-model"
    assert config.storage.path == "/env/path"


def test_config_to_dict():
    """Test converting configuration back to a dictionary."""
    config = CodexMeshConfig()
    config.embedding.model = "to-dict-model"
    config.skills = ["test-skill"]

    data = config.to_dict()
    assert data["embedding"]["model"] == "to-dict-model"
    assert data["skills"] == ["test-skill"]
    assert data["storage"]["backend"] == "rustworkx"
