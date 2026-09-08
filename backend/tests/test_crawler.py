from pathlib import Path
import gzip

import httpx
import pytest

from seo_audit.config import Settings
from seo_audit.crawler import CrawlError, SiteCrawler
from seo_audit.page_types import infer_page_type, representative_url_order
from seo_audit.url_safety import ValidatedTarget


def test_crawler_requests_stable_compression_encodings(tmp_path: Path):
    settings = Settings()
    crawler = SiteCrawler(settings)

    assert crawler.request_headers()["Accept-Encoding"] == "gzip, deflate"


def test_discovered_urls_are_ordered_as_a_representative_sample():
    urls = [
        "https://shop.test/category/books",
        "https://shop.test/category/games",
        "https://shop.test/catalogue/example-book/index.html",
        "https://shop.test/catalogue/another-book/index.html",
        "https://shop.test/about",
    ]

    ordered = representative_url_order(urls)

    assert [infer_page_type(url) for url in ordered[:3]] == [
        "category",
        "product",
        "other",
    ]


def test_blocked_start_page_reports_the_real_cause(tmp_path: Path, monkeypatch):
    settings = Settings()
    crawler = SiteCrawler(settings)

    async def fake_validate(url: str, allow_private_networks: bool = False):
        class Target:
            def __init__(self, target_url: str):
                self.url = target_url

        return Target(url)

    async def fake_fetch(client, url: str, max_redirects: int = 5):
        return httpx.Response(403, request=httpx.Request("GET", url)), url

    monkeypatch.setattr("seo_audit.crawler.validate_public_target", fake_validate)
    monkeypatch.setattr(crawler, "_fetch", fake_fetch)

    with pytest.raises(CrawlError, match=r"blocked the audit crawler \(HTTP 403\)"):
        import asyncio

        asyncio.run(crawler.crawl("audit-id", "https://example.com/", 5))


@pytest.mark.asyncio
async def test_fetch_rejects_declared_and_streamed_oversize_responses(monkeypatch):
    async def fake_validate(url: str, allow_private_networks: bool = False):
        return ValidatedTarget(url=url, origin="https://example.com")

    monkeypatch.setattr("seo_audit.crawler.validate_public_target", fake_validate)
    crawler = SiteCrawler(Settings(maximum_response_bytes=12))

    async def declared(_request):
        return httpx.Response(200, headers={"content-length": "13"}, content=b"small")

    async with httpx.AsyncClient(transport=httpx.MockTransport(declared)) as client:
        with pytest.raises(CrawlError, match="byte limit"):
            await crawler._fetch(client, "https://example.com/", allowed_origin="https://example.com")

    async def streamed(_request):
        return httpx.Response(200, content=b"thirteen-byte")

    async with httpx.AsyncClient(transport=httpx.MockTransport(streamed)) as client:
        with pytest.raises(CrawlError, match="byte limit"):
            await crawler._fetch(client, "https://example.com/", allowed_origin="https://example.com")


@pytest.mark.asyncio
async def test_fetch_rejects_redirect_that_leaves_settled_origin(monkeypatch):
    async def fake_validate(url: str, allow_private_networks: bool = False):
        origin = "https://other.example" if "other.example" in url else "https://example.com"
        return ValidatedTarget(url=url, origin=origin)

    monkeypatch.setattr("seo_audit.crawler.validate_public_target", fake_validate)

    def redirect(request):
        return httpx.Response(302, headers={"location": "https://other.example/page"})

    crawler = SiteCrawler(Settings())
    async with httpx.AsyncClient(transport=httpx.MockTransport(redirect)) as client:
        with pytest.raises(CrawlError, match="left the settled audit origin"):
            await crawler._fetch(client, "https://example.com/page", allowed_origin="https://example.com")


@pytest.mark.asyncio
async def test_fetch_retries_once_without_compression_for_mislabeled_body(monkeypatch):
    async def fake_validate(url: str, allow_private_networks: bool = False):
        return ValidatedTarget(url=url, origin="https://example.com")

    monkeypatch.setattr("seo_audit.crawler.validate_public_target", fake_validate)
    encodings = []

    def respond(request):
        encodings.append(request.headers.get("accept-encoding"))
        if request.headers.get("accept-encoding") != "identity":
            return httpx.Response(
                200,
                headers={"content-type": "text/html", "content-encoding": "gzip"},
                stream=httpx.ByteStream(b"<html>not really gzipped</html>"),
            )
        return httpx.Response(200, headers={"content-type": "text/html"}, content=b"<html>ok</html>")

    crawler = SiteCrawler(Settings())
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        response, _ = await crawler._fetch(client, "https://example.com/", allowed_origin="https://example.com")

    assert response.text == "<html>ok</html>"
    assert encodings[-1] == "identity"


@pytest.mark.asyncio
async def test_fetch_does_not_decode_a_valid_compressed_response_twice(monkeypatch):
    async def fake_validate(url: str, allow_private_networks: bool = False):
        return ValidatedTarget(url=url, origin="https://example.com")

    monkeypatch.setattr("seo_audit.crawler.validate_public_target", fake_validate)
    body = b"<html><title>Compressed page</title></html>"

    def respond(request):
        return httpx.Response(
            200,
            headers={"content-type": "text/html", "content-encoding": "gzip"},
            stream=httpx.ByteStream(gzip.compress(body)),
        )

    crawler = SiteCrawler(Settings())
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        response, _ = await crawler._fetch(client, "https://example.com/", allowed_origin="https://example.com")

    assert response.text == body.decode()
    assert "content-encoding" not in response.headers


@pytest.mark.asyncio
async def test_crawl_has_a_total_time_budget(monkeypatch):
    import asyncio

    crawler = SiteCrawler(Settings(crawl_timeout_seconds=0.001))

    async def slow(*_args):
        await asyncio.sleep(0.02)

    monkeypatch.setattr(crawler, "_crawl_bounded", slow)
    with pytest.raises(CrawlError, match="time budget"):
        await crawler.crawl("audit-id", "https://example.com", 5)
