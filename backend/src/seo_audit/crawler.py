from __future__ import annotations

import asyncio
import xml.etree.ElementTree as ET
from collections import deque
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from seo_audit.config import Settings
from seo_audit.extractor import canonicalize_discovered_url, extract_page
from seo_audit.models import PageRecord
from seo_audit.page_types import representative_url_order
from seo_audit.url_safety import UnsafeTargetError, validate_public_target


@dataclass(slots=True)
class CrawlResult:
    pages: list[PageRecord]
    origin: str
    warnings: list[str] = field(default_factory=list)


class CrawlError(RuntimeError):
    pass


class SiteCrawler:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def crawl(self, audit_id: str, start_url: str, limit: int) -> CrawlResult:
        validated = await validate_public_target(
            start_url, allow_private_networks=self.settings.allow_private_networks
        )
        warnings: list[str] = []
        async with httpx.AsyncClient(
            timeout=self.settings.request_timeout_seconds,
            headers=self.request_headers(),
        ) as client:
            first_response, first_url = await self._fetch(client, validated.url)
            if first_response.status_code in {401, 403}:
                raise CrawlError(
                    f"The website blocked the audit crawler (HTTP {first_response.status_code}). "
                    "This does not mean search engines cannot crawl the site."
                )
            if first_response.status_code == 429:
                raise CrawlError(
                    "The website rate-limited the audit crawler (HTTP 429). "
                    "Wait a few minutes before retrying."
                )
            first_origin = _origin(first_url)
            robots, sitemap_urls = await self._load_robots_and_sitemaps(
                client, first_origin, warnings
            )

            queue: deque[tuple[str, int]] = deque([(first_url, 0)])
            for sitemap_url in representative_url_order(sitemap_urls):
                if len(queue) >= limit:
                    break
                queue.append((sitemap_url, 1))

            seen: set[str] = set()
            pages: list[PageRecord] = []
            prefetched = {first_url: first_response}
            robots_blocked_count = 0
            start_url_blocked = False

            while queue and len(pages) < limit:
                requested_url, depth = queue.popleft()
                if requested_url in seen or _origin(requested_url) != first_origin:
                    continue
                seen.add(requested_url)
                if robots is not None and not robots.can_fetch(
                    self.settings.user_agent, requested_url
                ):
                    robots_blocked_count += 1
                    start_url_blocked = start_url_blocked or requested_url == first_url
                    continue
                try:
                    response = prefetched.pop(requested_url, None)
                    final_url = requested_url
                    if response is None:
                        response, final_url = await self._fetch(client, requested_url)
                    content_type = response.headers.get("content-type", "").split(";", 1)[0]
                    if "text/html" not in content_type.lower():
                        continue
                    page = extract_page(
                        audit_id=audit_id,
                        requested_url=requested_url,
                        final_url=final_url,
                        status_code=response.status_code,
                        content_type=content_type,
                        html=response.text,
                        depth=depth,
                        scope_origin=first_origin,
                    )
                    pages.append(page)
                    ordered_links = representative_url_order(
                        link.url for link in page.internal_links
                    )
                    for link_url in ordered_links:
                        if link_url not in seen and len(queue) + len(pages) < limit * 3:
                            queue.append((link_url, depth + 1))
                except (httpx.HTTPError, UnsafeTargetError) as exc:
                    pages.append(
                        PageRecord(
                            audit_id=audit_id,
                            requested_url=requested_url,
                            final_url=requested_url,
                            depth=depth,
                            fetch_error=str(exc),
                        )
                    )
                if self.settings.crawl_delay_seconds:
                    await asyncio.sleep(self.settings.crawl_delay_seconds)

        if robots_blocked_count:
            warnings.append(
                f"robots.txt disallowed {robots_blocked_count} discovered URL(s) for the audit user-agent."
            )
        if start_url_blocked:
            warnings.append(
                f"robots.txt disallowed the redirected start URL: {first_url}"
            )
        if len(pages) >= limit and queue:
            warnings.append(
                f"The crawl limit of {limit} pages was reached; findings describe a representative sample, not the entire site."
            )
        if not pages and not start_url_blocked:
            raise CrawlError("No crawlable HTML pages were found")
        return CrawlResult(
            pages=pages,
            origin=first_origin,
            warnings=list(dict.fromkeys(warnings)),
        )

    def request_headers(self) -> dict[str, str]:
        return {
            "User-Agent": self.settings.user_agent,
            # Avoid optional zstd decoder incompatibilities observed on some CDNs.
            "Accept-Encoding": "gzip, deflate",
        }

    async def _fetch(
        self, client: httpx.AsyncClient, url: str, max_redirects: int = 5
    ) -> tuple[httpx.Response, str]:
        current = url
        for _ in range(max_redirects + 1):
            validated = await validate_public_target(
                current, allow_private_networks=self.settings.allow_private_networks
            )
            response = await client.get(validated.url, follow_redirects=False)
            if response.status_code not in {301, 302, 303, 307, 308}:
                return response, validated.url
            location = response.headers.get("location")
            if not location:
                return response, validated.url
            current = urljoin(validated.url, location)
        raise CrawlError(f"Too many redirects while fetching {url}")

    async def _load_robots_and_sitemaps(
        self,
        client: httpx.AsyncClient,
        origin: str,
        warnings: list[str],
    ) -> tuple[RobotFileParser | None, list[str]]:
        robots_url = f"{origin}/robots.txt"
        parser: RobotFileParser | None = None
        declared_sitemaps: list[str] = []
        try:
            response, _ = await self._fetch(client, robots_url)
            if response.status_code == 200:
                parser = RobotFileParser()
                parser.set_url(robots_url)
                parser.parse(response.text.splitlines())
                for line in response.text.splitlines():
                    key, separator, value = line.partition(":")
                    if separator and key.strip().lower() == "sitemap":
                        declared_sitemaps.append(value.strip())
            elif response.status_code >= 400:
                warnings.append(f"robots.txt returned HTTP {response.status_code}")
        except (httpx.HTTPError, UnsafeTargetError, CrawlError) as exc:
            warnings.append(f"robots.txt could not be checked: {exc}")

        sitemap_candidates = declared_sitemaps or [f"{origin}/sitemap.xml"]
        discovered: list[str] = []
        for sitemap_url in sitemap_candidates[:3]:
            try:
                response, final_url = await self._fetch(client, sitemap_url)
                if response.status_code != 200:
                    continue
                discovered.extend(_parse_sitemap(response.text, final_url, origin))
            except (httpx.HTTPError, UnsafeTargetError, CrawlError, ET.ParseError):
                continue
        return parser, list(dict.fromkeys(discovered))


def _origin(url: str) -> str:
    parsed = urlsplit(url)
    return f"{parsed.scheme}://{parsed.netloc.lower()}"


def _parse_sitemap(xml: str, sitemap_url: str, origin: str) -> list[str]:
    root = ET.fromstring(xml)
    urls: list[str] = []
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1].lower() != "loc" or not element.text:
            continue
        candidate = canonicalize_discovered_url(sitemap_url, element.text)
        if candidate and _origin(candidate) == origin:
            urls.append(candidate)
    return urls[:100]
