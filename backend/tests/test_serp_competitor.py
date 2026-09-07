from datetime import UTC, datetime

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from serp_competitor.api import create_serp_router
from serp_competitor.client import SerperClient, SerperError
from serp_competitor.models import QuestionEvidence, SerpItem, SerpRequest
from serp_competitor.storage import MemorySerpRepository
from seo_audit.config import Settings
from seo_audit.crawler import CrawlResult
from seo_audit.models import HeadingRecord, PageRecord


def organic():
    return [
        SerpItem(position=1, title="Best CRM Software and Pricing", url="https://one.example/crm", snippet="Compare CRM tools.", domain="one.example"),
        SerpItem(position=2, title="CRM Software Guide", url="https://two.example/guide", snippet="A buyer guide.", domain="two.example"),
        SerpItem(position=3, title="CRM Reviews", url="https://three.example/reviews", snippet="Reviews and comparisons.", domain="three.example"),
    ]


@pytest.mark.asyncio
async def test_serper_client_preserves_empty_optional_sections_and_never_exposes_key():
    key = "private-serper-key"

    def handle(request):
        assert request.headers["x-api-key"] == key
        return httpx.Response(200, json={"organic": [
            {"position": 1, "title": "CRM guide", "link": "https://example.com/crm", "snippet": "Guide"}
        ]})

    items, questions, related, answer_box, _ = await SerperClient(
        key, transport=httpx.MockTransport(handle)
    ).search(SerpRequest(target_keyword="crm software", result_limit=3))
    assert len(items) == 1
    assert questions == [] and related == []
    assert answer_box is None
    assert key not in repr(items)


@pytest.mark.asyncio
async def test_serper_client_fails_clearly_when_unconfigured():
    with pytest.raises(SerperError, match="not configured"):
        await SerperClient(None).search(SerpRequest(target_keyword="crm software"))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("response", "message"),
    [
        (httpx.Response(429, json={"message": "quota"}), "HTTP 429"),
        (httpx.Response(200, content=b"not-json"), "malformed JSON"),
        (httpx.Response(200, json={"organic": []}), "no usable organic"),
    ],
)
async def test_serper_client_classifies_provider_failures(response, message):
    def handle(request):
        return response
    with pytest.raises(SerperError, match=message):
        await SerperClient("secret", transport=httpx.MockTransport(handle)).search(
            SerpRequest(target_keyword="crm software", result_limit=3)
        )


class FakeSerper:
    def __init__(self):
        self.calls = 0

    async def search(self, request):
        self.calls += 1
        return organic(), [QuestionEvidence(question="What is a CRM?")], [], None, datetime.now(UTC)


class FakeCrawler:
    async def crawl(self, audit_id, url, limit):
        if "three.example" in url:
            raise RuntimeError("blocked")
        heading = "Compare CRM pricing" if "one.example" in url else "Choose CRM features"
        return CrawlResult(
            origin=url.rsplit("/", 1)[0],
            pages=[PageRecord(
                audit_id=audit_id, requested_url=url, final_url=url, status_code=200,
                title=heading, word_count=1200 if "one.example" in url else 800,
                headings=[HeadingRecord(level="h2", text=heading)],
                schema_types=["Article"], main_text="Observed competitor content.",
            )],
        )


def test_api_persists_grounded_serp_and_competitor_evidence():
    repository = MemorySerpRepository()
    serper = FakeSerper()
    app = FastAPI()
    app.include_router(create_serp_router(
        Settings(serper_api_key="configured"), repository,
        client=serper, crawler=FakeCrawler(),
    ))
    base = "/api/agents/serp-competitor/runs"
    with TestClient(app) as client:
        created = client.post(base, json={
            "target_keyword": "best crm software", "country": "in",
            "language": "en", "inspect_limit": 3,
        })
        assert created.status_code == 202
        run_id = created.json()["id"]
        processed = client.post(f"{base}/{run_id}/process")
        result = client.get(f"{base}/{run_id}/result")
        reopened = client.get(f"{base}/{run_id}")
        history = client.get(base, params={"query": "crm"})
        status = client.get("/api/agents/serp-competitor/status")
    assert processed.json()["status"] == "complete"
    payload = result.json()
    assert payload["search_intent"] in {"commercial", "mixed"}
    assert len(payload["organic_results"]) == 3
    assert [item["fetched"] for item in payload["competitors"]] == [True, True, False]
    assert payload["median_word_count"] == 1000
    assert payload["questions"][0]["question"] == "What is a CRM?"
    assert payload["related_searches"] == []
    assert any("No related-search" in warning for warning in payload["warnings"])
    assert reopened.json()["result"] == payload
    assert history.json()["total"] == 1
    assert status.json() == {"configured": True, "provider": "Serper"}
    assert payload["topic_patterns"]
    assert all(item["source_urls"] for item in payload["topic_patterns"])

    with TestClient(app) as client:
        second = client.post(base, json={
            "target_keyword": "  BEST crm software ", "country": "IN",
            "language": "EN", "inspect_limit": 3,
        }).json()
        reused = client.post(f"{base}/{second['id']}/process").json()
    assert serper.calls == 1
    assert reused["result"]["snapshot_source_run_id"] == run_id
    assert reused["result"]["observed_at"] == payload["observed_at"]
