from fastapi.testclient import TestClient

from agent_runtime.api import create_app
from memory_metadata_repository import MemoryMetadataGenerationRepository
from memory_repository import MemoryAuditRepository
from seo_audit.config import Settings


def test_shared_app_registers_audit_and_metadata_agent_routes():
    app = create_app(
        Settings(),
        audit_repository=MemoryAuditRepository(),
        metadata_repository=MemoryMetadataGenerationRepository(),
    )

    with TestClient(app) as client:
        health = client.get("/api/health")
        metadata = client.post(
            "/api/agents/meta-title-description/generations",
            json={"prompt": "Write metadata for a project management pricing page."},
        )
        audit = client.post(
            "/api/agents/seo-audit/audits",
            json={"url": "https://example.com/"},
        )
        schema = client.get("/api/openapi.json").json()
        history = client.get("/api/agent-runs")
        protected_settings = client.get("/api/settings/providers")
        settings = client.get(
            "/api/settings/providers",
            cookies={"stellar_demo_session": "stellar-admin"},
        )

    assert health.status_code == 200
    assert metadata.status_code == 202
    assert audit.status_code == 202
    assert history.status_code == 200
    assert history.json()["total"] == 2
    assert {item["agent_slug"] for item in history.json()["items"]} == {
        "seo-audit",
        "meta-title-description",
    }
    assert protected_settings.status_code == 401
    assert settings.status_code == 200
    assert all("api_key" not in item for item in settings.json()["providers"])
    assert [item["provider"] for item in settings.json()["providers"]] == ["groq"]
    assert len(settings.json()["model_options"]) == 4
    assert app.title == "Stellar Agents API"
    assert "/api/agents/meta-title-description/generations" in schema["paths"]
    assert "/api/agents/internal-linking/audits" in schema["paths"]
    assert "/api/agent-runs" in schema["paths"]
