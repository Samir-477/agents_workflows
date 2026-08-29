from pathlib import Path

from seo_audit.config import Settings


def test_settings_load_llm_values_from_env_file(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("SEO_AUDIT_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("SEO_AUDIT_LLM_MODEL", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "SEO_AUDIT_LLM_PROVIDER=groq\nGROQ_API_KEY=test-key\nSEO_AUDIT_LLM_MODEL=test-model\n",
        encoding="utf-8",
    )

    settings = Settings.from_env(env_file)

    assert settings.llm_provider == "groq"
    assert settings.llm_api_key == "test-key"
    assert settings.llm_model == "test-model"


def test_settings_do_not_enable_an_unselected_provider(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("SEO_AUDIT_LLM_PROVIDER", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "unused-key")
    env_file = tmp_path / ".env"
    env_file.write_text("SEO_AUDIT_LLM_MODEL=test-model\n", encoding="utf-8")

    settings = Settings.from_env(env_file)

    assert settings.llm_provider is None
    assert settings.llm_api_key is None
