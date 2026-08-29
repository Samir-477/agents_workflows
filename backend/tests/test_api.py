from pathlib import Path

from fastapi.testclient import TestClient

from seo_audit.api import create_app
from seo_audit.config import Settings
from seo_audit.models import AuditCreate, AuditReport
from seo_audit.models import AuditStage, AuditStatus
from seo_audit.storage import AuditRepository


def test_create_and_read_queued_audit(tmp_path: Path):
    settings = Settings(database_path=tmp_path / "api.sqlite3")
    repository = AuditRepository(settings.database_path)
    app = create_app(settings, repository)

    with TestClient(app) as client:
        response = client.post(
            "/audits",
            json={
                "url": "example.com",
                "business_description": "A small consultancy",
                "crawl_limit": 5,
            },
        )
        assert response.status_code == 202
        payload = response.json()
        audit_id = payload["audit"]["id"]
        assert payload["audit"]["requested_url"] == "https://example.com/"

        status_response = client.get(f"/audits/{audit_id}")
        assert status_response.status_code == 200
        assert status_response.json()["audit"]["status"] == "queued"

        history_response = client.get("/audits")
        assert history_response.status_code == 200
        assert history_response.json()["total"] == 1
        assert history_response.json()["items"][0]["audit"]["id"] == audit_id

        report_response = client.get(f"/audits/{audit_id}/report")
        assert report_response.status_code == 409

        preflight = client.options(
            "/audits",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        assert preflight.status_code == 200
        assert preflight.headers["access-control-allow-origin"] == "http://localhost:3000"

        delete_response = client.delete(f"/audits/{audit_id}")
        assert delete_response.status_code == 204
        assert client.get(f"/audits/{audit_id}").status_code == 404


def test_completed_report_can_be_downloaded_as_pdf(tmp_path: Path):
    settings = Settings(database_path=tmp_path / "api.sqlite3")
    repository = AuditRepository(settings.database_path)
    repository.initialize()
    audit = repository.create_audit(
        request=AuditCreate(url="https://example.com/"),
        crawl_limit=5,
    )
    repository.save_report(
        AuditReport(
            audit_id=audit.id,
            requested_url=audit.requested_url,
            executive_summary="The sample audit found a small number of clear improvements.",
            site_score=82,
            pages_crawled=1,
            severity_counts={"critical": 0, "important": 1, "minor": 0},
            quick_wins=["Add a concise meta description."],
            findings=[],
            limitations=["Only one page was inspected."],
        )
    )
    app = create_app(settings, repository)

    with TestClient(app) as client:
        response = client.get(f"/audits/{audit.id}/report.pdf")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF")


def test_serverless_process_endpoint_claims_and_runs_audit(tmp_path: Path, monkeypatch):
    settings = Settings(database_path=tmp_path / "api.sqlite3")
    repository = AuditRepository(settings.database_path)

    class FakeGraph:
        async def ainvoke(self, state):
            repository.update_audit(
                state["audit_id"],
                status=AuditStatus.COMPLETE,
                stage=AuditStage.COMPLETE,
                progress=100,
            )

    monkeypatch.setattr("seo_audit.api.build_audit_graph", lambda *_: FakeGraph())
    app = create_app(settings, repository)

    with TestClient(app) as client:
        created = client.post("/audits", json={"url": "https://example.com/"})
        audit_id = created.json()["audit"]["id"]
        processed = client.post(f"/audits/{audit_id}/process")

    assert processed.status_code == 200
    assert processed.json()["audit"]["status"] == "complete"
