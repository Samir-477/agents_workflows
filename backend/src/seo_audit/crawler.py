from __future__ import annotations

import asyncio
import xml.etree.ElementTree as ET
from collections import deque
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlsplit

import httpx

from seo_audit.config import Settings
from seo_audit.extractor import canonicalize_discovered_url, extract_page
from seo_audit.models import PageRecord
from seo_audit.page_types import representative_url_order
from seo_audit.robots import RobotsPolicy
from seo_audit.url_safety import UnsafeTargetError, validate_public_target


@dataclass(slots=True)
class CrawlResult:
    pages: list[PageRecord]
    origin: str
    warnings: list[str] = field(default_factory=list)
    discovered_urls: list[str] = field(default_factory=list)
    sitemap_urls: list[str] = field(default_factory=list)
    coverage_complete: bool = False
    robots_txt: str | None = None


class CrawlError(RuntimeError):
    pass


class SiteCrawler:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def crawl(self, audit_id: str, start_url: str, limit: int) -> CrawlResult:
        try:
            async with asyncio.timeout(self.settings.crawl_timeout_seconds):
                return await self._crawl_bounded(audit_id, start_url, limit)
        except TimeoutError as exc:
            raise CrawlError(
                f"The crawl exceeded its {self.settings.crawl_timeout_seconds:g}-second time budget. "
                "Retry with a lower page limit or when the site responds faster."
            ) from exc

    async def _crawl_bounded(self, audit_id: str, start_url: str, limit: int) -> CrawlResult:
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
            robots, sitemap_urls, robots_txt = await self._load_robots_and_sitemaps(
                client, first_origin, warnings
            )

            queue: deque[tuple[str, int]] = deque([(first_url, 0)])
            for sitemap_url in representative_url_order(sitemap_urls):
                if len(queue) >= limit:
                    break
                queue.append((sitemap_url, 1))

            seen: set[str] = set()
            crawled_final_urls: set[str] = set()
            pages: list[PageRecord] = []
            prefetched = {first_url: first_response}
            robots_blocked_count = 0
            start_url_blocked = False

            while queue and len(pages) < limit:
                requested_url, depth = queue.popleft()
                if requested_url in seen or _origin(requested_url) != first_origin:
                    continue
                seen.add(requested_url)
                if not robots.can_fetch(requested_url, self.settings.user_agent):
                    robots_blocked_count += 1
                    start_url_blocked = start_url_blocked or requested_url == first_url
                    continue
                try:
                    response = prefetched.pop(requested_url, None)
                    final_url = requested_url
                    if response is None:
                        response, final_url = await self._fetch(
                            client, requested_url, allowed_origin=first_origin
                        )
                    content_type = response.headers.get("content-type", "").split(";", 1)[0]
                    if "text/html" not in content_type.lower():
                        continue
                    # Two requested URLs can resolve to one page through redirects or a
                    # trailing slash. Recording both would make the page a duplicate of
                    # itself in every cross-page comparison, so keep the first only.
                    if final_url in crawled_final_urls:
                        seen.add(final_url)
                        continue
                    crawled_final_urls.add(final_url)
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
        limit_reached = len(pages) >= limit and bool(queue)
        if limit_reached:
            warnings.append(
                f"The crawl limit of {limit} pages was reached; findings describe a representative sample, not the entire site."
            )
        if not sitemap_urls:
            warnings.append(
                "No sitemap page inventory was available; site-wide orphan detection is limited to discovered pages."
            )
        if not pages and not start_url_blocked:
            raise CrawlError("No crawlable HTML pages were found")
        return CrawlResult(
            pages=pages,
            origin=first_origin,
            warnings=list(dict.fromkeys(warnings)),
            discovered_urls=list(dict.fromkeys([*seen, *(url for url, _ in queue)])),
            sitemap_urls=sitemap_urls,
            coverage_complete=(
                bool(sitemap_urls)
                and {canonicalize_discovered_url(first_url, url) for url in sitemap_urls}.issubset(seen)
                and not limit_reached
                and not robots_blocked_count
                and not any(page.fetch_error for page in pages)
            ),
            robots_txt=robots_txt,
        )

    def request_headers(self) -> dict[str, str]:
        return {
            "User-Agent": self.settings.user_agent,
            # Avoid optional zstd decoder incompatibilities observed on some CDNs.
            "Accept-Encoding": "gzip, deflate",
        }

    async def _fetch(
        self,
        client: httpx.AsyncClient,
        url: str,
        max_redirects: int = 5,
        allowed_origin: str | None = None,
    ) -> tuple[httpx.Response, str]:
        current = url
        force_identity = False
        for _ in range(max_redirects + 2):
            validated = await validate_public_target(
                current, allow_private_networks=self.settings.allow_private_networks
            )
            if allowed_origin and validated.origin != allowed_origin:
                raise CrawlError(f"A redirect left the settled audit origin: {validated.origin}")
            request = client.build_request(
                "GET",
                validated.url,
                headers={"Accept-Encoding": "identity"} if force_identity else None,
            )
            response = await client.send(request, follow_redirects=False, stream=True)
            if response.status_code not in {301, 302, 303, 307, 308}:
                declared_length = response.headers.get("content-length")
                if declared_length and declared_length.isdigit() and int(declared_length) > self.settings.maximum_response_bytes:
                    await response.aclose()
                    raise CrawlError(
                        f"Response exceeded the {self.settings.maximum_response_bytes}-byte limit: {validated.url}"
                    )
                content = bytearray()
                try:
                    async for chunk in response.aiter_bytes():
                        content.extend(chunk)
                        if len(content) > self.settings.maximum_response_bytes:
                            await response.aclose()
                            raise CrawlError(
                                f"Response exceeded the {self.settings.maximum_response_bytes}-byte limit: {validated.url}"
                            )
                except httpx.DecodingError as exc:
                    await response.aclose()
                    if force_identity:
                        raise CrawlError(
                            f"The server returned an unreadable compressed response: {validated.url}"
                        ) from exc
                    # Some CDNs label an uncompressed body as gzip/deflate. Retry
                    # once without compression rather than failing the whole crawl.
                    force_identity = True
                    continue
                status_code = response.status_code
                headers = httpx.Headers(response.headers)
                # `aiter_bytes()` has already decoded transfer content. Retaining
                # these headers on the reconstructed buffered response would make
                # `.text` attempt to decompress the body a second time.
                for header in ("content-encoding", "content-length", "transfer-encoding"):
                    if header in headers:
                        del headers[header]
                await response.aclose()
                return httpx.Response(
                    status_code, headers=headers, content=bytes(content), request=request
                ), validated.url
            location = response.headers.get("location")
            await response.aclose()
            if not location:
                return response, validated.url
            current = urljoin(validated.url, location)
        raise CrawlError(f"Too many redirects while fetching {url}")

    async def _load_robots_and_sitemaps(
        self,
        client: httpx.AsyncClient,
        origin: str,
        warnings: list[str],
    ) -> tuple[RobotsPolicy, list[str], str | None]:
        robots_url = f"{origin}/robots.txt"
        policy = RobotsPolicy.parse(None)
        robots_txt: str | None = None
        try:
            response, _ = await self._fetch(client, robots_url, allowed_origin=origin)
            if response.status_code == 200:
                robots_txt = response.text[:100_000]
                policy = RobotsPolicy.parse(response.text)
                if not policy.declared:
                    warnings.append(
                        "robots.txt was served but could not be parsed; the crawl proceeded "
                        "as if no rules were declared."
                    )
            elif response.status_code >= 400:
                warnings.append(f"robots.txt returned HTTP {response.status_code}")
        except (httpx.HTTPError, UnsafeTargetError, CrawlError) as exc:
            warnings.append(f"robots.txt could not be checked: {exc}")

        declared_sitemaps = [
            url for url in policy.sitemaps() if _origin(url) == origin
        ]
        sitemap_candidates = declared_sitemaps or [f"{origin}/sitemap.xml"]
        discovered: list[str] = []
        expanded_index = False
        # A declared sitemap is often a <sitemapindex> listing further sitemaps rather
        # than pages. Treating those child URLs as pages yields an empty inventory, so
        # follow one bounded level down to reach the real page list.
        for sitemap_url in sitemap_candidates[:3]:
            pages, children = await self._read_sitemap(client, sitemap_url, origin)
            discovered.extend(pages)
            for child_url in children[:20]:
                if len(discovered) >= 500:
                    break
                child_pages, _ = await self._read_sitemap(client, child_url, origin)
                if child_pages:
                    expanded_index = True
                discovered.extend(child_pages)
        if expanded_index and not discovered:
            warnings.append(
                "A sitemap index was found but none of its child sitemaps returned page URLs."
            )
        return policy, list(dict.fromkeys(discovered))[:500], robots_txt

    async def _read_sitemap(
        self, client: httpx.AsyncClient, sitemap_url: str, origin: str
    ) -> tuple[list[str], list[str]]:
        """Return (page URLs, child sitemap URLs) for one sitemap document."""
        try:
            response, final_url = await self._fetch(
                client, sitemap_url, allowed_origin=origin
            )
            if response.status_code != 200:
                return [], []
            return _parse_sitemap(response.text, final_url, origin)
        except (httpx.HTTPError, UnsafeTargetError, CrawlError, ET.ParseError):
            return [], []


def _origin(url: str) -> str:
    parsed = urlsplit(url)
    return f"{parsed.scheme}://{parsed.netloc.lower()}"


def _parse_sitemap(xml: str, sitemap_url: str, origin: str) -> tuple[list[str], list[str]]:
    """Split a sitemap document into page URLs and nested sitemap URLs.

    A `<sitemapindex>` lists other sitemaps, not pages. Both element types use `<loc>`,
    so the parent tag is what distinguishes them.
    """
    root = ET.fromstring(xml)
    is_index = root.tag.rsplit("}", 1)[-1].lower() == "sitemapindex"
    pages: list[str] = []
    children: list[str] = []
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1].lower() != "loc" or not element.text:
            continue
        candidate = canonicalize_discovered_url(sitemap_url, element.text)
        if not candidate or _origin(candidate) != origin:
            continue
        parent_is_sitemap = is_index or candidate.lower().endswith((".xml", ".xml.gz"))
        if parent_is_sitemap:
            if candidate != sitemap_url:
                children.append(candidate)
        else:
            pages.append(candidate)
    return pages[:500], list(dict.fromkeys(children))
