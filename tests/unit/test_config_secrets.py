import json

from codex_mesh.config import CodexMeshConfig
from codex_mesh.llm.routing import LLMProfile


def test_save_to_file_does_not_persist_profile_api_key(tmp_path):
    cfg = CodexMeshConfig()
    cfg.profiles["ui_active"] = LLMProfile(
        name="ui_active",
        provider="google",
        model="gemini-2.5-flash",
        temperature=0.2,
        api_key="SECRET_TEST_KEY",
        api_key_env="GOOGLE_API_KEY",
    )

    p = tmp_path / "cfg.json"
    cfg.save_to_file(p)

    raw = p.read_text(encoding="utf-8")
    assert "SECRET_TEST_KEY" not in raw
    assert '"api_key"' not in raw

    data = json.loads(raw)
    assert "profiles" in data
    assert "ui_active" in data["profiles"]
    assert "api_key" not in data["profiles"]["ui_active"]
