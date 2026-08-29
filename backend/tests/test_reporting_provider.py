from pathlib import Path

from langchain_groq import ChatGroq

from seo_audit.config import Settings
from seo_audit.reporting import ReportWriter


def test_report_writer_builds_selected_groq_model(tmp_path: Path):
    settings = Settings(
        database_path=tmp_path / "test.sqlite3",
        llm_provider="groq",
        llm_model="openai/gpt-oss-20b",
        llm_api_key="test-key",
    )

    model = ReportWriter(settings)._create_chat_model()

    assert isinstance(model, ChatGroq)
    assert model.model_name == "openai/gpt-oss-20b"
