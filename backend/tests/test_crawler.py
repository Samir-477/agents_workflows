from pathlib import Path

from seo_audit.config import Settings
from seo_audit.crawler import CrawlError, SiteCrawler
from seo_audit.page_types import infer_page_type, representative_url_order


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
    import httpx
    import pytest

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
